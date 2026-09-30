"""
Crisis Command — LLM Fallback

Template-based explanation generator used when no LLM is available.
All explanations are derived from actual computed data — nothing is invented.
"""

from backend.llm.provider import LLMProvider


class FallbackProvider(LLMProvider):
    """Deterministic template-based fallback when no LLM key is present."""

    def is_available(self) -> bool:
        return True  # always available

    def generate_explanation(self, prompt: str) -> str:
        return prompt  # pass through — callers provide template text

    def parse_incident(self, text: str) -> dict:
        return {}  # cannot parse free text without LLM
