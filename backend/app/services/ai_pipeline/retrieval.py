import logging
import os
from typing import Any

import chromadb
from chromadb.config import Settings

from app.core.config import settings
from app.services.ai_pipeline.client_factory import get_ai_client

logger = logging.getLogger(__name__)


def _collection_name(school_id: int) -> str:
    return f"school_{school_id}_curriculum"


class ChromaDBClient:
    def __init__(self, path: str = "./database/chroma", ollama=None):
        self.path = path
        os.makedirs(self.path, exist_ok=True)
        # Initialize embedded ChromaDB PersistentClient
        self.client = chromadb.PersistentClient(path=self.path, settings=Settings(anonymized_telemetry=False))
        self.ollama = ollama or get_ai_client()

    def _ensure_collection(self, school_id: int):
        name = _collection_name(school_id)
        # get_or_create_collection handles existence natively
        return self.client.get_or_create_collection(name=name, metadata={"school_id": school_id})

    async def embed_and_store(
        self,
        chunks: list[dict[str, Any]],
        school_id: int,
    ) -> int:
        collection = self._ensure_collection(school_id)

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
            
            # Clean metadatas (Chroma requires str, int, float, or bool)
            meta = {
                "book_id": str(chunk.get("book_id", "")),
                "grade": str(chunk.get("grade", "")),
                "school_id": str(school_id),
                "chunk_index": int(chunk.get("chunk_index", 0)),
            }
            if chunk.get("chapter_id"):
                meta["chapter_id"] = str(chunk.get("chapter_id"))
            if chunk.get("topic_id"):
                meta["topic_id"] = str(chunk.get("topic_id"))
                
            metadatas.append(meta)

        if not embeddings:
            return 0

        try:
            # PersistentClient operates synchronously
            collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents,
            )
            return len(ids)
        except Exception as e:
            logger.error("ChromaDB add failed: %s", e)
            return 0

    async def retrieve(
        self,
        school_id: int,
        query: str,
        where: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        name = _collection_name(school_id)
        try:
            collection = self.client.get_collection(name=name)
        except Exception:
            return []

        try:
            query_emb = await self.ollama.generate_embedding(query)
        except Exception as e:
            logger.warning("Failed to embed query: %s", e)
            return []

        try:
            results = collection.query(
                query_embeddings=[query_emb],
                n_results=top_k,
                where=where or {},
            )
            
            formatted_results = []
            if results and results.get("ids") and len(results["ids"]) > 0:
                for i in range(len(results["ids"][0])):
                    formatted_results.append({
                        "id": results["ids"][0][i],
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if results.get("distances") else 0.0,
                    })
            return formatted_results
        except Exception as e:
            logger.error("ChromaDB query failed: %s", e)
            return []

    async def delete_for_book(self, school_id: int, book_id: int) -> bool:
        name = _collection_name(school_id)
        try:
            collection = self.client.get_collection(name=name)
            collection.delete(where={"book_id": str(book_id)})
            return True
        except Exception as e:
            logger.error("ChromaDB delete failed: %s", e)
            return False
