import asyncio
import json
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout_seconds = timeout_seconds or settings.OLLAMA_TIMEOUT
        self.timeout = httpx.Timeout(self.timeout_seconds)
        self.num_thread = settings.OLLAMA_NUM_THREAD
        self.temperature = settings.OLLAMA_TEMPERATURE

    def _build_options(self, temperature: float | None = None) -> dict[str, Any]:
        return {
            "temperature": temperature if temperature is not None else self.temperature,
            "num_thread": self.num_thread,
        }

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
        temperature: float | None = None,
        model: str | None = None,
    ) -> str:
        url = f"{self.base_url}/api/generate"
        payload: dict[str, Any] = {
            "model": model or self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": self._build_options(temperature),
        }
        if json_mode:
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()["response"]

    def _extract_json(self, text: str) -> str | None:
        text = text.strip()
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = text.find(start_char)
            if start >= 0:
                depth = 0
                for i in range(start, len(text)):
                    if text[i] == start_char:
                        depth += 1
                    elif text[i] == end_char:
                        depth -= 1
                        if depth == 0:
                            return text[start : i + 1]
                return text[start:]
        return None

    def _fix_json(self, text: str) -> str:
        import re
        text = re.sub(r"\{\{", "{", text)
        text = re.sub(r"\}\}", "}", text)
        text = re.sub(r"(\s)(\w+)(\s*:)", r'\1"\2"\3', text)
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*\]", "]", text)
        return text

    def _parse_json_lenient(self, text: str) -> dict | list | None:
        fixed = self._fix_json(text)
        extracted = self._extract_json(fixed)
        if not extracted:
            return None
        try:
            return json.loads(extracted)
        except json.JSONDecodeError:
            return None

    async def generate_structured(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float | None = None,
        max_retries: int = 2,
        model: str | None = None,
    ) -> dict[str, Any]:
        last_error: str | None = None
        raw = ""
        for attempt in range(max_retries + 1):
            try:
                raw = await self.generate(
                    prompt=prompt,
                    system=system,
                    json_mode=False,
                    temperature=temperature,
                    model=model,
                )
                parsed = self._parse_json_lenient(raw)
                if isinstance(parsed, dict):
                    return parsed
                if isinstance(parsed, list):
                    if all(isinstance(i, dict) for i in parsed):
                        return {"items": parsed}
                raise json.JSONDecodeError(f"Could not extract valid JSON object from response", raw, 0)
            except (json.JSONDecodeError, httpx.HTTPStatusError) as e:
                last_error = f"{type(e).__name__}: {e}"
                logger.warning(
                    "Ollama parse failed (attempt %d/%d, last_error=%s): %s...",
                    attempt + 1, max_retries + 1, last_error, raw[:200] if raw else "empty",
                )
                if attempt < max_retries:
                    await asyncio.sleep(1 * (attempt + 1))
            except httpx.TimeoutException as e:
                last_error = f"Timeout: {e}"
                logger.warning("Ollama timeout (attempt %d/%d): %s", attempt + 1, max_retries + 1, last_error)
                if attempt < max_retries:
                    await asyncio.sleep(1 * (attempt + 1))
            except Exception as e:
                last_error = f"Unhandled: {type(e).__name__}: {e}"
                logger.error("_gen_struct unhandled exception: %s", last_error)
                raise
        raise RuntimeError(f"Ollama generation failed after {max_retries + 1} retries: {last_error}")

    async def generate_structured_array(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float | None = None,
        max_retries: int = 2,
        model: str | None = None,
    ) -> list[dict[str, Any]]:
        last_error: str | None = None
        raw = ""
        for attempt in range(max_retries + 1):
            try:
                raw = await self.generate(
                    prompt=prompt,
                    system=system,
                    json_mode=False,
                    temperature=temperature,
                    model=model,
                )
                parsed = self._parse_json_lenient(raw)
                if isinstance(parsed, list):
                    return parsed
                if isinstance(parsed, dict):
                    for key in ("questions", "mcqs", "items", "results", "question", "mcq"):
                        if key in parsed and isinstance(parsed[key], list):
                            return parsed[key]
                    return [parsed]
                return []
            except httpx.TimeoutException as e:
                last_error = f"Timeout: {e}"
                logger.warning("Ollama timeout (attempt %d/%d): %s", attempt + 1, max_retries + 1, last_error)
                if attempt < max_retries:
                    await asyncio.sleep(1 * (attempt + 1))
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}: {e}"
                logger.warning("Ollama HTTP error (attempt %d/%d): %s", attempt + 1, max_retries + 1, last_error)
                if attempt < max_retries:
                    await asyncio.sleep(1 * (attempt + 1))
            except (json.JSONDecodeError, ValueError) as e:
                last_error = str(e)
                logger.warning(
                    "Ollama array JSON parse failed (attempt %d/%d): %s...",
                    attempt + 1, max_retries + 1, raw[:300],
                )
                if attempt < max_retries:
                    continue
        logger.error("Ollama array generation failed after %d retries: %s", max_retries + 1, last_error)
        return []

    async def generate_embedding(self, text: str, model: str = "nomic-embed-text") -> list[float]:
        url = f"{self.base_url}/api/embeddings"
        payload = {"model": model, "prompt": text}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()["embedding"]

    async def is_available(self) -> bool:
        try:
            url = f"{self.base_url}/api/tags"
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(url)
                return response.status_code == 200
        except Exception:
            return False
