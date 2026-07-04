import logging
from typing import Any

import httpx

from app.core.config import settings
from app.services.ai_pipeline.gemini_client import GeminiClient as OllamaClient

logger = logging.getLogger(__name__)


def _collection_name(school_id: int) -> str:
    return f"school_{school_id}_curriculum"


class ChromaDBClient:
    def __init__(self, base_url: str | None = None, ollama: OllamaClient | None = None):
        self.base_url = (base_url or settings.CHROMA_BASE_URL).rstrip("/")
        self.ollama = ollama or OllamaClient()

    async def _ensure_collection(self, school_id: int) -> str | None:
        name = _collection_name(school_id)
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            response = await client.get(f"{self.base_url}/api/v1/collections?name={name}")
            if response.status_code == 200:
                collections = response.json()
                if collections:
                    return collections[0].get("id") or collections[0].get("name") or name

            create_resp = await client.post(
                f"{self.base_url}/api/v1/collections",
                json={"name": name, "metadata": {"school_id": school_id}},
            )
            if create_resp.status_code in (200, 201):
                data = create_resp.json()
                return data.get("id") or data.get("name") or name

            logger.warning("Failed to create ChromaDB collection: %s", create_resp.text)
            return None

    async def embed_and_store(
        self,
        chunks: list[dict[str, Any]],
        school_id: int,
    ) -> int:
        collection_id = await self._ensure_collection(school_id)
        if not collection_id:
            logger.error("Cannot store chunks: ChromaDB collection unavailable")
            return 0

        ids: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, Any]] = []
        documents: list[str] = []

        for chunk in chunks:
            chunk_id = str(chunk.get("id", ""))
            if not chunk_id:
                chunk_id = f"chunk_{school_id}_{chunk.get('chunk_index', 0)}"
            ids.append(chunk_id)

            try:
                emb = await self.ollama.generate_embedding(chunk.get("text", ""))
                embeddings.append(emb)
            except Exception as e:
                logger.warning("Embedding failed for chunk %s: %s", chunk_id, e)
                continue

            documents.append(chunk.get("text", ""))
            metadatas.append({
                "book_id": str(chunk.get("book_id", "")),
                "chapter_id": str(chunk.get("chapter_id", "")) if chunk.get("chapter_id") else None,
                "topic_id": str(chunk.get("topic_id", "")) if chunk.get("topic_id") else None,
                "grade": str(chunk.get("grade", "")),
                "school_id": str(school_id),
                "chunk_index": str(chunk.get("chunk_index", 0)),
            })

        if not embeddings:
            return 0

        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/collections/{collection_id}/add",
                json={
                    "ids": ids,
                    "embeddings": embeddings,
                    "metadatas": metadatas,
                    "documents": documents,
                },
            )
            if response.status_code not in (200, 201):
                logger.error("ChromaDB add failed: %s", response.text)
                return 0

        return len(ids)

    async def retrieve(
        self,
        school_id: int,
        query: str,
        where: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        name = _collection_name(school_id)
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.get(f"{self.base_url}/api/v1/collections?name={name}")
            if resp.status_code != 200 or not resp.json():
                return []
            collection = resp.json()[0]
            collection_id = collection.get("id") or collection.get("name") or name

        try:
            query_emb = await self.ollama.generate_embedding(query)
        except Exception as e:
            logger.warning("Failed to embed query: %s", e)
            return []

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/collections/{collection_id}/query",
                json={
                    "query_embeddings": [query_emb],
                    "n_results": top_k,
                    "where": where or {},
                },
            )
            if response.status_code != 200:
                logger.warning("ChromaDB query failed: %s", response.text)
                return []

            data = response.json()
            results: list[dict[str, Any]] = []
            metadatas_list = data.get("metadatas", [[]])[0]
            documents_list = data.get("documents", [[]])[0]
            distances_list = data.get("distances", [[]])[0]
            ids_list = data.get("ids", [[]])[0]

            for i in range(len(ids_list)):
                results.append({
                    "id": ids_list[i] if i < len(ids_list) else "",
                    "text": documents_list[i] if i < len(documents_list) else "",
                    "metadata": metadatas_list[i] if i < len(metadatas_list) else {},
                    "score": 1.0 - (distances_list[i] if i < len(distances_list) else 0),
                })

            return results

    async def delete_book_vectors(self, school_id: int, book_id: int) -> bool:
        name = _collection_name(school_id)
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.get(f"{self.base_url}/api/v1/collections?name={name}")
            if resp.status_code != 200 or not resp.json():
                return True
            collection = resp.json()[0]
            collection_id = collection.get("id") or collection.get("name") or name

            del_resp = await client.post(
                f"{self.base_url}/api/v1/collections/{collection_id}/delete",
                json={"where": {"book_id": str(book_id)}},
            )
            return del_resp.status_code in (200, 201)

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(f"{self.base_url}/api/v1/heartbeat")
                return response.status_code == 200
        except Exception:
            return False
