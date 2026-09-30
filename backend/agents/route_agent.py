"""
Crisis Command — Route / Logistics Agent

Interface for future LLM + OSM integration.  Currently uses
deterministic Haversine ETA calculations.
"""

from backend.route import calculate_eta
from backend.state import CrisisState


class RouteLogisticsAgent:
    """Calculate routes and ETAs.

    MVP: Haversine distance ÷ average speed.
    Phase 2: OpenStreetMap real road-network routing.
    """

    def calculate_all_etas(self, state: CrisisState) -> CrisisState:
        for plan in state.candidate_plans:
            for asgn in plan.assignments:
                unit = state.get_unit(asgn.unit_id)
                inc = state.get_incident(asgn.incident_id)
                if unit and inc:
                    asgn.eta_minutes = calculate_eta(
                        unit.latitude, unit.longitude,
                        inc.latitude, inc.longitude,
                        state.road_conditions,
                    )
        state.log_action("RouteLogisticsAgent", "Calculated ETAs for all assignments")
        return state
