"""models/regulation.py — RegulationChunk (RAG storage) + RegulatoryChange (intel agent)."""
from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class RegulationChunk:
    chunk_id: str                    # UUID
    regulator: str                   # "fssai" | "ayush"
    source_url: str
    document_title: str
    section: str                     # e.g. "Section 2.4 - Health Claims"
    text: str                        # The actual chunk content
    ingested_at: str = ""             # ISO datetime

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RegulatoryChange:
    change_id: str
    regulator: str
    detected_at: str
    source_url: str
    document_title: str
    change_summary: str = ""          # Gemini-generated summary of what changed
    affected_product_categories: List[str] = field(default_factory=list)
    affected_ingredients: List[str] = field(default_factory=list)
    severity: str = "INFORMATIONAL"   # "MAJOR" | "MINOR" | "INFORMATIONAL"
    raw_text: str = ""
    is_acknowledged: bool = False

    def to_dict(self) -> dict:
        return asdict(self)
