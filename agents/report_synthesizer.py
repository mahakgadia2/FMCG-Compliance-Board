"""agents/report_synthesizer.py — Step 4 (final): builds the FinalReport."""
import json
import uuid
from datetime import datetime

from agents.base_agent import BaseAgent
from agents.llm_client import GeminiUnavailable
from core.prompt_loader import load_prompt
from models.report import FinalReport


class ReportSynthesizerAgent(BaseAgent):
    """
    Reads: context.verdicts, context.conflicts, context.product_spec
    Writes: context.final_report
    """

    def __init__(self, context):
        super().__init__(context)
        self.name = "Report Synthesizer"
        self.prompt_template = load_prompt("report_synthesizer.txt")

    def run(self) -> None:
        self.log("Synthesizing final report...")
        overall_status = self._determine_overall_status()
        action_items = self._compile_action_items()
        summary = self._generate_summary(overall_status)

        report = FinalReport(
            report_id=str(uuid.uuid4()),
            product_name=self.context.product_spec.product_name,
            overall_status=overall_status,
            applicable_regulators=self.context.applicable_regulators,
            verdicts=list(self.context.verdicts.values()),
            conflicts=self.context.conflicts,
            action_items=action_items,
            summary=summary,
            generated_at=datetime.now().isoformat(),
            pipeline_log=list(self.context.log),
        )
        self.context.final_report = report
        self.log(f"Final report ready. Overall status: {overall_status}")

    def _determine_overall_status(self) -> str:
        """
        Rule-based (no LLM needed):
        - Any NON_COMPLIANT verdict -> overall NON_COMPLIANT
        - Any HIGH severity conflict -> NEEDS_REVIEW
        - All COMPLIANT (or NOT_APPLICABLE) -> COMPLIANT
        - Otherwise -> NEEDS_REVIEW
        """
        statuses = [v.status for v in self.context.verdicts.values()]

        if "NON_COMPLIANT" in statuses:
            return "NON_COMPLIANT"
        if any(c.severity == "HIGH" for c in self.context.conflicts):
            return "NEEDS_REVIEW"
        if all(s in ("COMPLIANT", "NOT_APPLICABLE") for s in statuses):
            return "COMPLIANT"
        return "NEEDS_REVIEW"

    def _compile_action_items(self):
        """Flatten all issues from all verdicts into a deduplicated action list."""
        items = []
        seen = set()
        for verdict in self.context.verdicts.values():
            for issue in verdict.issues:
                text = f"[{verdict.regulator.upper()} / {issue.severity}] {issue.description}"
                if text not in seen:
                    seen.add(text)
                    items.append(text)
        for conflict in self.context.conflicts:
            text = f"[CONFLICT / {conflict.severity}] {conflict.description} — {conflict.suggested_resolution}"
            if text not in seen:
                seen.add(text)
                items.append(text)
        return items

    def _generate_summary(self, overall_status: str) -> str:
        """Single Gemini call to write a 2-3 sentence executive summary."""
        verdicts_json = json.dumps(
            [v.to_dict() for v in self.context.verdicts.values()], indent=2
        )
        conflicts_json = json.dumps(
            [c.to_dict() for c in self.context.conflicts], indent=2
        )
        prompt = self.prompt_template.format(
            product_name=self.context.product_spec.product_name,
            overall_status=overall_status,
            verdicts_json=verdicts_json,
            conflicts_json=conflicts_json,
        )
        try:
            return self.call_llm(prompt, expect_json=False).strip()
        except GeminiUnavailable:
            return self._fallback_summary(overall_status)

    def _fallback_summary(self, overall_status: str) -> str:
        n_issues = sum(len(v.issues) for v in self.context.verdicts.values())
        n_conflicts = len(self.context.conflicts)
        return (
            f"{self.context.product_spec.product_name} was reviewed against "
            f"{len(self.context.applicable_regulators)} regulator(s) and received an "
            f"overall status of {overall_status}, with {n_issues} issue(s) and "
            f"{n_conflicts} cross-regulator conflict(s) identified. "
            f"(Generated via rule-based fallback; Gemini was unavailable.)"
        )
