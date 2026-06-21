"""agents/orchestrator.py — Step 1 of the pipeline: classify applicable regulators."""
import json
from typing import List

from agents.base_agent import BaseAgent
from agents.llm_client import GeminiUnavailable
from core.prompt_loader import load_prompt
from config import SUPPORTED_REGULATORS


class OrchestratorAgent(BaseAgent):
    """
    Reads: context.product_spec
    Writes: context.applicable_regulators
    """

    SUPPORTED_REGULATORS = SUPPORTED_REGULATORS

    def __init__(self, context):
        super().__init__(context)
        self.name = "Orchestrator"
        self.prompt_template = load_prompt("classifier.txt")

    def run(self) -> None:
        self.log("Classifying applicable regulators...")
        try:
            regulators = self._classify_regulators()
            self.log(f"Gemini classification: {regulators}")
        except (GeminiUnavailable, json.JSONDecodeError, KeyError) as e:
            self.log(f"LLM classification failed ({e}); using rule-based fallback.")
            regulators = self._rule_based_fallback()
            self.log(f"Rule-based classification: {regulators}")

        # Always sanitize against the supported list, never trust the LLM blindly.
        regulators = [r for r in regulators if r in self.SUPPORTED_REGULATORS]
        if not regulators:
            regulators = self._rule_based_fallback()

        self.context.applicable_regulators = regulators
        self.log(f"Final applicable regulators: {regulators}")

    def _classify_regulators(self) -> List[str]:
        """Calls Gemini with the product spec. Returns a subset of SUPPORTED_REGULATORS."""
        spec_json = json.dumps(self.context.product_spec.to_dict(), indent=2)
        prompt = self.prompt_template.format(product_spec_json=spec_json)
        result = self.call_llm(prompt, expect_json=True)
        return result.get("applicable_regulators", [])

    def _rule_based_fallback(self) -> List[str]:
        """
        Simple heuristic: if has_herbal_ingredients -> include ayush,
        always include fssai. Ensures demo reliability even if Gemini is slow/down.
        """
        spec = self.context.product_spec
        regulators = ["fssai"]  # FSSAI applies to virtually all packaged food/supplements
        if spec.has_herbal_ingredients:
            regulators.append("ayush")
        return regulators
