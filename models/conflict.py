"""models/conflict.py — output of the Conflict Detector."""
from dataclasses import dataclass, asdict


@dataclass
class Conflict:
    conflict_id: str                 # Auto-generated: "conflict_001"
    attribute: str                   # The shared attribute both regulators disagree on
    regulator_a: str
    position_a: str                  # What regulator A says about this attribute
    regulator_b: str
    position_b: str                  # What regulator B says about this attribute
    severity: str = "MEDIUM"         # "HIGH" | "MEDIUM" | "LOW"
    description: str = ""            # Plain English explanation of the conflict
    suggested_resolution: str = ""   # Optional: what the manufacturer should do

    def to_dict(self) -> dict:
        return asdict(self)
