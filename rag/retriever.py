"""rag/retriever.py — thin wrapper around ChromaDB. No agent touches ChromaDB directly."""
from typing import Dict, List, Optional
from datetime import datetime

import chromadb

from config import CHROMA_DIR
from rag.embedder import Embedder
from models.regulation import RegulationChunk

_client = chromadb.PersistentClient(path=str(CHROMA_DIR))


def _collection_name(regulator: str) -> str:
    return f"regulai_{regulator}"


class Retriever:
    """
    If `collection` is specified, all queries/upserts are scoped to that
    regulator namespace. If None, operates across all known collections
    (used by the Regulatory Intelligence Agent for stats / cross-cutting work).
    """

    def __init__(self, collection: Optional[str] = None):
        self.regulator = collection
        self.embedder = Embedder()
        self._collections: Dict[str, "chromadb.Collection"] = {}

    def _get_collection(self, regulator: str):
        if regulator not in self._collections:
            self._collections[regulator] = _client.get_or_create_collection(
                name=_collection_name(regulator)
            )
        return self._collections[regulator]

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        regulator: Optional[str] = None,
    ) -> List[RegulationChunk]:
        """Embed query_text, search ChromaDB, return top-n RegulationChunks."""
        reg = regulator or self.regulator
        if reg is None:
            raise ValueError("Retriever.query requires a regulator (set at init or per-call).")

        col = self._get_collection(reg)
        if col.count() == 0:
            return []

        query_embedding = self.embedder.embed(query_text)
        n = min(n_results, col.count())
        results = col.query(query_embeddings=[query_embedding], n_results=n)

        chunks: List[RegulationChunk] = []
        ids = results.get("ids", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        for cid, doc, meta in zip(ids, docs, metas):
            chunks.append(
                RegulationChunk(
                    chunk_id=cid,
                    regulator=meta.get("regulator", reg),
                    source_url=meta.get("source_url", ""),
                    document_title=meta.get("document_title", ""),
                    section=meta.get("section", ""),
                    text=doc,
                    ingested_at=meta.get("ingested_at", ""),
                )
            )
        return chunks

    def upsert(self, chunks: List[RegulationChunk]) -> None:
        """Add or update chunks. Uses chunk_id as the stable identifier."""
        by_regulator: Dict[str, List[RegulationChunk]] = {}
        for c in chunks:
            by_regulator.setdefault(c.regulator, []).append(c)

        for regulator, group in by_regulator.items():
            col = self._get_collection(regulator)
            embeddings = self.embedder.embed_batch([c.text for c in group])
            col.upsert(
                ids=[c.chunk_id for c in group],
                documents=[c.text for c in group],
                embeddings=embeddings,
                metadatas=[
                    {
                        "regulator": c.regulator,
                        "source_url": c.source_url,
                        "document_title": c.document_title,
                        "section": c.section,
                        "ingested_at": c.ingested_at or datetime.now().isoformat(),
                    }
                    for c in group
                ],
            )

    def get_collection_stats(self) -> Dict[str, int]:
        """Returns: {"fssai": 142, "ayush": 87} — used by Intel Agent status UI."""
        from config import SUPPORTED_REGULATORS
        stats = {}
        for reg in SUPPORTED_REGULATORS:
            col = self._get_collection(reg)
            stats[reg] = col.count()
        return stats

    def get_last_ingested(self, regulator: str) -> Optional[str]:
        """Returns ISO datetime of most recently ingested chunk for this regulator."""
        col = self._get_collection(regulator)
        if col.count() == 0:
            return None
        all_meta = col.get()["metadatas"]
        timestamps = [m.get("ingested_at") for m in all_meta if m.get("ingested_at")]
        return max(timestamps) if timestamps else None
