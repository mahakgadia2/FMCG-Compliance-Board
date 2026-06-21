"""rag/ingestion.py — end-to-end ingest: raw text -> chunks -> ChromaDB."""
import uuid
from datetime import datetime
from pathlib import Path

from rag.chunker import chunk_text
from rag.retriever import Retriever
from models.regulation import RegulationChunk


class Ingestion:
    def __init__(self):
        self.retriever = Retriever()

    def ingest_text(
        self,
        text: str,
        regulator: str,
        document_title: str,
        source_url: str = "",
        section: str = "",
    ) -> int:
        """Chunk a raw text blob and upsert into ChromaDB. Returns chunk count."""
        pieces = chunk_text(text)
        chunks = [
            RegulationChunk(
                chunk_id=str(uuid.uuid4()),
                regulator=regulator,
                source_url=source_url,
                document_title=document_title,
                section=section or f"chunk_{i}",
                text=piece,
                ingested_at=datetime.now().isoformat(),
            )
            for i, piece in enumerate(pieces)
        ]
        self.retriever.upsert(chunks)
        return len(chunks)

    def ingest_file(self, path: Path, regulator: str) -> int:
        """Read a .txt seed file and ingest it, using the filename as the title."""
        text = path.read_text(encoding="utf-8")
        title = path.stem.replace("_", " ").title()
        return self.ingest_text(
            text=text,
            regulator=regulator,
            document_title=title,
            source_url=f"seed://{regulator}/{path.name}",
        )
