"""agents/llm_client.py — thin wrapper around google-generativeai with offline fallback."""
import json
import re
from typing import Optional

from config import GEMINI_API_KEY, GEMINI_TEXT_MODEL, LLM_MAX_RETRIES

_genai_client = None
if GEMINI_API_KEY:
    try:
        from google import genai 
        _genai_client = genai.Client(api_key=GEMINI_API_KEY)
        
    except Exception:
        _genai_client = None


class GeminiClient:
    """
    Minimal wrapper: one method, `generate`. If no API key is configured,
    `generate` raises GeminiUnavailable so callers can fall back to their
    own rule-based logic (see OrchestratorAgent._rule_based_fallback, etc.)
    rather than the whole pipeline crashing.
    """

    def __init__(self, model: str = GEMINI_TEXT_MODEL):
        self.model_name = model
        self._client = _genai_client

    def generate(self, prompt: str) -> str:
        if self._client is None:
            raise GeminiUnavailable("GEMINI_API_KEY not configured.")
        last_err: Optional[Exception] = None
        for attempt in range(LLM_MAX_RETRIES + 1):
            try:
                response = self._client.models.generate_content(
                    model = self.model_name,
                    contents= prompt
                )
                return response.text
            except Exception as e:
                last_err = e
        raise GeminiUnavailable(f"Gemini call failed after retries: {last_err}")

    @staticmethod
    def strip_json_fences(text: str) -> str:
        """Removes ```json ... ``` or ``` ... ``` fences if present."""
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        return match.group(1).strip() if match else text.strip()

    @classmethod
    def parse_json(cls, text: str) -> dict:
        cleaned = cls.strip_json_fences(text)
        return json.loads(cleaned)


class GeminiUnavailable(Exception):
    """Raised when no API key is configured or the Gemini call fails after retries."""
    pass

