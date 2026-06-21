"""agents/conflict_detector.py — Step 3: compares verdicts pairwise, flags contradictions."""
import json
from itertools import combinations
from typing import Dict, List, Optional, Tuple

from agents.base_agent import BaseAgent
from agents.llm_client import GeminiUnavailable
from core.prompt_loader import load_prompt
from models.conflict import Conflict
from models.verdict import Issue


class ConflictDetectorAgent(BaseAgent):
    """
    Reads: context.verdicts (all expert agent outputs)
    Writes: context.conflicts
    """

    def __init__(self, context):
        super().__init__(context)
        self.name = "Conflict Detector"
        self.prompt_template = load_prompt("conflict_detector.txt")

    def run(self) -> None:
        self.log("Scanning verdicts for cross-regulator conflicts...")
        overlaps = self._find_attribute_overlaps()

        if not overlaps:
            self.log("No shared attributes across regulators; no conflicts possible.")
            self.context.conflicts = []
            return

        conflicts: List[Conflict] = []
        counter = 1
        for attribute, issue_pairs in overlaps.items():
            for (reg_a, issue_a), (reg_b, issue_b) in combinations(issue_pairs, 2):
                conflict = self._detect_contradiction(attribute, [(reg_a, issue_a), (reg_b, issue_b)])
                if conflict:
                    conflict.conflict_id = f"conflict_{counter:03d}"
                    counter += 1
                    conflicts.append(conflict)

        self.context.conflicts = conflicts
        if conflicts:
            self.log(f"Detected {len(conflicts)} conflict(s).")
        else:
            self.log("No conflicts detected.")

    def _find_attribute_overlaps(self) -> Dict[str, List[Tuple[str, Issue]]]:
        """
        Groups issues by attribute across all verdicts.
        Returns: { "ingredient:ashwagandha": [("fssai", Issue), ("ayush", Issue)] }
        """
        groups: Dict[str, List[Tuple[str, Issue]]] = {}
        for regulator, verdict in self.context.verdicts.items():
            for issue in verdict.issues:
                key = issue.attribute
                groups.setdefault(key, []).append((regulator, issue))

        # Only attributes flagged by 2+ distinct regulators are candidates.
        return {
            attr: pairs
            for attr, pairs in groups.items()
            if len({reg for reg, _ in pairs}) >= 2
        }

    def _detect_contradiction(
        self,
        attribute: str,
        issues: List[Tuple[str, Issue]],
    ) -> Optional[Conflict]:
        """For a shared attribute, calls Gemini to determine if positions contradict."""
        (reg_a, issue_a), (reg_b, issue_b) = issues
        prompt = self.prompt_template.format(
            attribute=attribute,
            regulator_a=reg_a,
            position_a=issue_a.description,
            regulator_b=reg_b,
            position_b=issue_b.description,
        )

        try:
            data = self.call_llm(prompt, expect_json=True)
        except (GeminiUnavailable, json.JSONDecodeError):
            # Fallback heuristic: if severities differ meaningfully, flag as a
            # low-confidence conflict so the manufacturer still sees the overlap.
            if issue_a.severity != issue_b.severity:
                return Conflict(
                    conflict_id="",
                    attribute=attribute,
                    regulator_a=reg_a,
                    position_a=issue_a.description,
                    regulator_b=reg_b,
                    position_b=issue_b.description,
                    severity="LOW",
                    description=(
                        "Both regulators flagged this attribute with different "
                        "severities; manual review recommended (LLM unavailable "
                        "for deeper contradiction analysis)."
                    ),
                    suggested_resolution="Manually compare both regulator positions.",
                )
            return None

        if not data.get("is_conflict", False):
            return None

        return Conflict(
            conflict_id="",
            attribute=attribute,
            regulator_a=reg_a,
            position_a=issue_a.description,
            regulator_b=reg_b,
            position_b=issue_b.description,
            severity=data.get("severity", "MEDIUM"),
            description=data.get("description", ""),
            suggested_resolution=data.get("suggested_resolution", ""),
        )
