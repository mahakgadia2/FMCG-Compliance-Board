"""core/pipeline.py — wires together all agents in order. Called by Streamlit."""
import asyncio

from core.context import AnalysisContext
from models.product_spec import ProductSpec
from agents.orchestrator import OrchestratorAgent
from agents.expert_agent import ExpertAgent
from agents.conflict_detector import ConflictDetectorAgent
from agents.report_synthesizer import ReportSynthesizerAgent


class AnalysisPipeline:
    """
    1. Create AnalysisContext
    2. Run OrchestratorAgent
    3. Run applicable ExpertAgents concurrently (asyncio.gather)
    4. Run ConflictDetectorAgent
    5. Run ReportSynthesizerAgent
    6. Return populated context (including final_report and log)
    """

    def run(self, product_spec: ProductSpec) -> AnalysisContext:
        context = AnalysisContext(product_spec=product_spec)
        context.status = "running"

        try:
            OrchestratorAgent(context).run()
            self._run_expert_agents_concurrently(context)
            ConflictDetectorAgent(context).run()
            ReportSynthesizerAgent(context).run()
            context.mark_complete()
        except Exception as e:
            context.mark_error(str(e))
            context.append_log("Pipeline", f"Fatal error: {e}")

        return context

    def _run_expert_agents_concurrently(self, context: AnalysisContext) -> None:
        """asyncio.gather over all applicable ExpertAgent.run() calls."""

        async def _run_all():
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(None, ExpertAgent(context, regulator).run)
                for regulator in context.applicable_regulators
            ]
            await asyncio.gather(*tasks)

        asyncio.run(_run_all())
