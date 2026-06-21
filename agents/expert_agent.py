"""agents/expert_agent.py — Generic ExpertAgent, parameterized by regulator."""
import json
from typing import List

from agents.base_agent import BaseAgent
from agents.llm_client import GeminiUnavailable
from core.prompt_loader import load_prompt
from rag.retriever import Retriever
from models.regulation import RegulationChunk
from models.verdict import Verdict, Issue
from config import TOP_K_CHUNKS


class ExpertAgent(BaseAgent):
    """
    One instance per regulator. Instantiate as: ExpertAgent(context, regulator="fssai")

    Reads: context.product_spec
    Writes: context.verdicts[self.regulator]
    """

    def __init__(self, context, regulator: str):
        super().__init__(context)
        self.regulator = regulator
        self.name = f"{regulator.upper()} Expert Agent"
        self.retriever = Retriever(collection=regulator)
        self.prompt_template = load_prompt(f"expert_{regulator}.txt")

    def run(self) -> None:
        self.log(f"Starting review for {self.regulator.upper()}...")
        chunks = self._retrieve_context()
        self.log(f"Retrieved {len(chunks)} regulation chunk(s) from ChromaDB.")

        prompt = self._build_prompt(chunks)
        try:
            raw = self.call_llm(prompt, expect_json=False)
            verdict = self._parse_verdict(raw, chunks)
            self.log(f"Verdict: {verdict.status} (confidence={verdict.confidence:.2f})")
        except GeminiUnavailable as e:
            self.log(f"Gemini unavailable ({e}); returning NEEDS_REVIEW fallback verdict.")
            verdict = self._fallback_verdict(chunks, reason=str(e))
        except (json.JSONDecodeError, ValueError) as e:
            self.log(f"Could not parse LLM response ({e}); returning NEEDS_REVIEW fallback verdict.")
            verdict = self._fallback_verdict(chunks, reason="Malformed LLM response.")

        self.context.set_verdict(self.regulator, verdict)

    def _retrieve_context(self) -> List[RegulationChunk]:
        """Build query from product spec attributes, retrieve top-k chunks from ChromaDB."""
        spec = self.context.product_spec
        query_parts = [
            spec.category,
            ", ".join(spec.ingredients),
            ", ".join(spec.claims),
            spec.target_demographic,
        ]
        query_text = " | ".join(p for p in query_parts if p)
        return self.retriever.query(query_text, n_results=TOP_K_CHUNKS, regulator=self.regulator)

    def _build_prompt(self, chunks: List[RegulationChunk]) -> str:
        """Inject retrieved chunks + product spec into the prompt template."""
        if chunks:
            context_text = "\n\n".join(
                f"[{c.document_title} — {c.section}]\n{c.text}" for c in chunks
            )
        else:
            context_text = "(No matching regulation chunks were found in the knowledge base.)"

        spec_json = json.dumps(self.context.product_spec.to_dict(), indent=2)
        return self.prompt_template.format(
            retrieved_context=context_text,
            product_spec_json=spec_json,
        )

    def _parse_verdict(self, llm_response: str, chunks: List[RegulationChunk]) -> Verdict:
        """Parse LLM JSON response into a Verdict dataclass. Handles malformed JSON."""
        data = self.llm.parse_json(llm_response)

        issues = [
            Issue(
                attribute=i.get("attribute", "unknown"),
                description=i.get("description", ""),
                severity=i.get("severity", "MEDIUM"),
                regulation_reference=i.get("regulation_reference", ""),
            )
            for i in data.get("issues", [])
        ]

        return Verdict(
            regulator=self.regulator,
            status=data.get("status", "NEEDS_REVIEW"),
            issues=issues,
            citations=[c.chunk_id for c in chunks],
            reasoning=data.get("reasoning", ""),
            confidence=float(data.get("confidence", 0.0)),
            agent_name=self.name,
        )

    def _fallback_verdict(self, chunks: List[RegulationChunk], reason: str) -> Verdict:
        """Used when the LLM call fails outright — keeps the pipeline alive for the demo."""
        return Verdict(
            regulator=self.regulator,
            status="NEEDS_REVIEW",
            issues=[
                Issue(
                    attribute="system",
                    description=f"Automated review could not complete: {reason}",
                    severity="MEDIUM",
                    regulation_reference="",
                )
            ],
            citations=[c.chunk_id for c in chunks],
            reasoning="Fallback verdict generated because the LLM call failed.",
            confidence=0.0,
            agent_name=self.name,
        )
