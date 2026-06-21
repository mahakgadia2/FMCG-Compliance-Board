"""rag/embedder.py — thin wrapper around Gemini embeddings, with a local fallback."""
from typing import List
import hashlib

from config import GEMINI_API_KEY, GEMINI_EMBED_MODEL

_genai_client = None
if GEMINI_API_KEY:
    try:
        from google import genai
        _genai_client = genai.Client(api_key=GEMINI_API_KEY)
        
    except Exception:
       _genai_client = None


class Embedder:
    """
    Wraps Gemini's embedding endpoint. If no API key is configured (e.g. running
    offline for the hackathon demo), falls back to a deterministic hash-based
    pseudo-embedding so the rest of the pipeline (chunking → ChromaDB → retrieval)
    still works end-to-end without network access.
    """

    DIM = 768

    def __init__(self, model: str = GEMINI_EMBED_MODEL):
        self.model_name = model
        self._client = _genai_client

    def embed(self, text: str) -> List[float]:
        if self._client is not None:
            try:
                result = self._client.models.embed_content(model=self.model_name, content=text)
                return result["embedding"]
            except Exception:
                pass  # fall through to offline fallback
        return self._fallback_embed(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]

    def _fallback_embed(self, text: str) -> List[float]:
        """Deterministic pseudo-embedding from hashed n-grams. Not semantically
        meaningful, but stable and good enough for offline demo continuity —
        ChromaDB still returns nearest neighbours rather than crashing."""
        vec = [0.0] * self.DIM
        words = text.lower().split()
        for w in words:
            h = int(hashlib.md5(w.encode()).hexdigest(), 16)
            idx = h % self.DIM
            vec[idx] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]
