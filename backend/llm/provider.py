"""
Crisis Command — LLM Provider Interface

Abstract interface for LLM providers.  The system works fully
without any LLM — all core logic is deterministic.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract LLM provider for explanation generation."""

    @abstractmethod
    def generate_explanation(self, prompt: str) -> str:
        """Generate a natural-language explanation."""
        ...

    @abstractmethod
    def parse_incident(self, text: str) -> dict:
        """Parse free-text incident report into structured data."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the LLM backend is reachable."""
        ...
