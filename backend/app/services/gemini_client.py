import json
import logging
from typing import Any
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 120,
    ):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", None)
        self.model = "gemini-flash-lite-latest"
        self.timeout_seconds = timeout_seconds
        self.timeout = httpx.Timeout(self.timeout_seconds)
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        json_mode: bool = False,
        temperature: float | None = None,
        model: str | None = None,
    ) -> str:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not set in the environment")

        url = f"{self.base_url}?key={self.api_key}"

        # Gemini system instructions
        system_instruction = None
        if system:
            system_instruction = {"parts": [{"text": system}]}

        contents = [{"role": "user", "parts": [{"text": prompt}]}]

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature if temperature is not None else 0.2,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = system_instruction

        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                return ""

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
                            f"Gemini generation failed after {max_retries + 1} retries"
                        ) from e
            except httpx.RequestError as e:
                logger.warning(
                    f"Network error {type(e).__name__} (attempt {attempt + 1}/{max_retries + 1}): {str(e)}"
                )
                import asyncio

                await asyncio.sleep(5)
                if attempt == max_retries:
                    raise RuntimeError(
                        f"Gemini generation failed after {max_retries + 1} retries"
                    ) from e
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Gemini parse failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}"
                )
                if attempt == max_retries:
                    raise RuntimeError(
                        f"Gemini generation failed after {max_retries + 1} retries"
                    ) from e
        return {}
