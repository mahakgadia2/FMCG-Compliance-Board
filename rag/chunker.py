"""rag/chunker.py — splits raw regulation text into overlapping token-bounded chunks."""
from typing import List

try:
    import tiktoken
    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:
    _ENC = None

from config import CHUNK_SIZE_TOKENS, CHUNK_OVERLAP_TOKENS


def _token_len(text: str) -> int:
    if _ENC is not None:
        return len(_ENC.encode(text))
    # fallback: rough estimate, ~4 chars/token
    return max(1, len(text) // 4)


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE_TOKENS,
    overlap: int = CHUNK_OVERLAP_TOKENS,
) -> List[str]:
    """
    Splits text into chunks of roughly `chunk_size` tokens with `overlap` tokens
    shared between consecutive chunks. Splits on paragraph/sentence boundaries
    where possible so chunks stay semantically coherent.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]

    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = _token_len(para)

        if current_len + para_len > chunk_size and current:
            chunks.append("\n\n".join(current))
            # carry overlap forward: keep last paragraph(s) up to `overlap` tokens
            overlap_paras = []
            overlap_len = 0
            for p in reversed(current):
                p_len = _token_len(p)
                if overlap_len + p_len > overlap:
                    break
                overlap_paras.insert(0, p)
                overlap_len += p_len
            current = overlap_paras
            current_len = overlap_len

        current.append(para)
        current_len += para_len

    if current:
        chunks.append("\n\n".join(current))

    # Safety net: if a single paragraph itself exceeds chunk_size, hard-split it.
    final_chunks: List[str] = []
    for c in chunks:
        if _token_len(c) <= chunk_size * 1.5:
            final_chunks.append(c)
        else:
            words = c.split()
            step = max(1, int(len(words) * chunk_size / max(1, _token_len(c))))
            for i in range(0, len(words), step):
                final_chunks.append(" ".join(words[i:i + step]))

    return final_chunks
