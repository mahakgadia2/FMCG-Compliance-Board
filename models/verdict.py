"""models/verdict.py — output of each Expert Agent."""
from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class Issue:
    attribute: str                   # "ingredient" | "claim" | "labeling" | "packaging"
    description: str                 # Human-readable problem statement
    severity: str                    # "HIGH" | "MEDIUM" | "LOW"
    regulation_reference: str = ""   # e.g. "FSSAI Food Safety Act 2006, Section 3(1)"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Verdict:
    regulator: str                   # "fssai" | "ayush"
    status: str                      # "COMPLIANT" | "NON_COMPLIANT" | "NOT_APPLICABLE" | "NEEDS_REVIEW"
    issues: List[Issue] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)   # Chunk IDs from ChromaDB
    reasoning: str = ""               # The agent's free-text chain-of-thought
    confidence: float = 0.0           # 0.0-1.0, self-reported by the LLM
    agent_name: str = ""              # For display in the UI log

    def to_dict(self) -> dict:
        d = asdict(self)
        return d
