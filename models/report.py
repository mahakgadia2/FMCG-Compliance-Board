"""models/report.py — final output of the pipeline."""
from dataclasses import dataclass, field, asdict
from typing import List
from models.verdict import Verdict
from models.conflict import Conflict


@dataclass
class FinalReport:
    report_id: str                   # UUID
    product_name: str
    overall_status: str              # "COMPLIANT" | "NON_COMPLIANT" | "NEEDS_REVIEW"
    applicable_regulators: List[str] = field(default_factory=list)
    verdicts: List[Verdict] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    summary: str = ""
    generated_at: str = ""            # ISO datetime string
    pipeline_log: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "product_name": self.product_name,
            "overall_status": self.overall_status,
            "applicable_regulators": self.applicable_regulators,
            "verdicts": [v.to_dict() for v in self.verdicts],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "action_items": self.action_items,
            "summary": self.summary,
            "generated_at": self.generated_at,
            "pipeline_log": self.pipeline_log,
        }
