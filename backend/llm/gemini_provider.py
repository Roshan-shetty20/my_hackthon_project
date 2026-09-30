"""
Crisis Command — Gemini Provider (Stub)

Placeholder for Google Gemini integration.
Requires GEMINI_API_KEY environment variable.
Falls back to deterministic templates when unavailable.
"""

import os
from backend.llm.provider import LLMProvider


class GeminiProvider(LLMProvider):
    """Gemini API integration — currently a stub for Phase 2."""

    def __init__(self) -> None:
        self.api_key = os.environ.get("GEMINI_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate_explanation(self, prompt: str) -> str:
        if not self.is_available():
            return ""
        
        try:
            from google import genai
            from google.genai import types
            import json
            
            client = genai.Client(api_key=self.api_key)
            
            system_instruction = (
                "You are the explanation layer of Crisis Command. "
                "You do not make operational decisions. "
                "All resource availability, route feasibility, ETA, constraint validation, "
                "resilience results and plan scores supplied to you are authoritative. "
                "Explain only what the verified evidence supports. "
                "Never invent missing information. "
                "If information is missing, explicitly state that it is unknown. "
                "Do not claim that a plan is feasible unless the deterministic constraint "
                "checker says it is feasible. "
                "Use concise commander-friendly language. "
                "You must return ONLY a JSON object with keys: summary, why_this_plan, why_not_alternatives, trade_off, risk, what_changed."
            )
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            return response.text
        except Exception as e:
            print(f"LLM Error: {e}")
            return ""

    def parse_incident(self, text: str) -> dict:
        if not self.is_available():
            return {}
        # Phase 2: call Gemini API here
        return {}
