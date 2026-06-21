"""core/context.py — AnalysisContext, the shared state object passed between agents."""
import uuid
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from models.product_spec import ProductSpec
from models.verdict import Verdict
from models.conflict import Conflict
from models.report import FinalReport


@dataclass
class AnalysisContext:
    # Input
    product_spec: ProductSpec

    # Set by Orchestrator
    applicable_regulators: List[str] = field(default_factory=list)
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Set by Expert Agents (keyed by regulator name)
    verdicts: Dict[str, Verdict] = field(default_factory=dict)

    # Set by Conflict Detector
    conflicts: List[Conflict] = field(default_factory=list)

    # Set by Report Synthesizer
    final_report: Optional[FinalReport] = None

    # Shared event log — all agents append here
    log: List[str] = field(default_factory=list)

    # Status tracking
    status: str = "pending"          # "pending" | "running" | "complete" | "error"
    error: Optional[str] = None

    # internal lock for thread/async-safe writes from concurrent expert agents
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def append_log(self, agent_name: str, message: str) -> None:
        """Timestamped log entry. All agents call this."""
        ts = datetime.now().strftime("%H:%M:%S")
        with self._lock:
            self.log.append(f"[{ts}] {agent_name}: {message}")

    def set_verdict(self, regulator: str, verdict: Verdict) -> None:
        """Thread-safe verdict registration."""
        with self._lock:
            self.verdicts[regulator] = verdict

    def mark_complete(self) -> None:
        self.status = "complete"

    def mark_error(self, error: str) -> None:
        self.status = "error"
        self.error = error
