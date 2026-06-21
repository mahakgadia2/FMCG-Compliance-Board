"""agents/base_agent.py — Abstract BaseAgent class. All agents inherit from this."""
from abc import ABC, abstractmethod

from agents.llm_client import GeminiClient
from core.context import AnalysisContext


class BaseAgent(ABC):
    """
    Gives every agent: a Gemini client, a logger, and access to the shared context.
    """

    def __init__(self, context: AnalysisContext):
        self.context = context
        self.name: str = self.__class__.__name__  # Subclasses should override.
        self.llm = GeminiClient()

    @abstractmethod
    def run(self) -> None:
        """
        Execute this agent's responsibility.
        Reads from and writes to self.context.
        Never returns a value — all output goes into context.
        """
        ...

    def log(self, message: str) -> None:
        """Convenience: delegates to context.append_log with self.name."""
        self.context.append_log(self.name, message)

    def call_llm(self, prompt: str, expect_json: bool = False):
        """
        Wraps the Gemini API call.
        If expect_json=True, strips markdown fences and parses+returns JSON (dict).
        Otherwise returns the raw text.
        Raises GeminiUnavailable / json.JSONDecodeError on failure — callers
        are expected to catch and fall back to rule-based logic.
        """
        raw = self.llm.generate(prompt)
        if expect_json:
            return self.llm.parse_json(raw)
        return raw
