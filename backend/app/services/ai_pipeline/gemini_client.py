import json
import logging
from typing import Any
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


import asyncio
import time

_gemini_lock = None
_last_request_time = 0.0

class GeminiClient:
    """Google Gemini API client using the OpenAI-compatible endpoint"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 120,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or "gemini-2.5-flash-lite"
        self.timeout_seconds = timeout_seconds
        self.timeout = httpx.Timeout(self.timeout_seconds)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
        temperature: float | None = None,
        model: str | None = None,
    ) -> str:
        if not self.api_key:
            raise RuntimeError("Gemini API key is missing. Set GEMINI_API_KEY in config.")
        
        logger.info("Sending request to Gemini API...")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system:
            messages.append({"role": "system", "content": system})

        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else 0.2,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError):
                return ""

    def _extract_json(self, text: str) -> str | None:
        text = text.strip()
        # Some models return json enclosed in markdown backticks
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
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
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        extracted = self._extract_json(text)
        if extracted:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                pass

        fixed = self._fix_json(text)
        extracted_fixed = self._extract_json(fixed)
        if not extracted_fixed:
            return None
        try:
            return json.loads(extracted_fixed)
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
        raw = ""
        for attempt in range(max_retries + 1):
            try:
                raw = await self.generate(
                    prompt=prompt,
                    system=system,
                    json_mode=True,
                    temperature=temperature,
                    model=model,
                )
                parsed = self._parse_json_lenient(raw)
                import asyncio

                if isinstance(parsed, dict):
                    return parsed
                if isinstance(parsed, list):
                    if all(isinstance(i, dict) for i in parsed):
                        return {"items": parsed}
                logger.error(f"Failed to parse JSON. Raw output: {raw}")
                raise json.JSONDecodeError(
                    f"Could not extract valid JSON object from response", raw, 0
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning(
                        f"Rate limit exceeded (429). Waiting 60 seconds before retrying (attempt {attempt + 1}/{max_retries + 1})..."
                    )
                    import asyncio

                    await asyncio.sleep(60)
                else:
                    logger.warning(
                        f"HTTP error {e.response.status_code} (attempt {attempt + 1}/{max_retries + 1}): {e.response.text}"
                    )
                    if attempt == max_retries:
                        raise RuntimeError(
                            f"OpenRouter generation failed after {max_retries + 1} retries"
                        ) from e
            except httpx.RequestError as e:
                logger.warning(
                    f"Network error {type(e).__name__} (attempt {attempt + 1}/{max_retries + 1}): {str(e)}"
                )
                import asyncio

                await asyncio.sleep(5)
                if attempt == max_retries:
                    raise RuntimeError(
                        f"OpenRouter generation failed after {max_retries + 1} retries"
                    ) from e
            except json.JSONDecodeError as e:
                logger.warning(
                    f"JSON parse failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}"
                )
                if attempt == max_retries:
                    raise RuntimeError(
                        f"OpenRouter generation failed after {max_retries + 1} retries"
                    ) from e
        return {}
