"""
Crisis Command — Incident Assessment Agent

Interface for future LLM integration.  Currently uses deterministic
severity scoring.  When Gemini is connected, this agent will parse
free-text incident reports into structured Incident objects.
"""

from backend.models import Incident
from backend.severity import assess_incident
from backend.state import CrisisState


class IncidentAssessmentAgent:
    """Assess incidents and compute severity.

    MVP: deterministic scoring only.
    Phase 2: LLM parses free-text descriptions → structured Incident.
    """

    def assess_all(self, state: CrisisState) -> CrisisState:
        for inc in state.incidents:
            assess_incident(inc)
        state.log_action("IncidentAssessmentAgent", "Assessed all incident severities")
        return state

    def assess_one(self, incident: Incident) -> Incident:
        return assess_incident(incident)
