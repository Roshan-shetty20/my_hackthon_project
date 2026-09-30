"""
Crisis Command — Central Crisis State

Versioned state container.  Every meaningful mutation increments `version`.
Historical snapshots are maintained by StateHistory so previous states
are never modified.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field

from backend.models import (
    ActionLogEntry,
    DecisionConfidence,
    DecisionDebt,
    Incident,
    Plan,
    PlanDiff,
    ResilienceResult,
    RoadCondition,
    SystemEvent,
    Unit,
    UnitStatus,
    DispatchMission,
    RouteOption
)


class CrisisState(BaseModel):
    """Central crisis state with version tracking."""

    version: int = 1
    incidents: List[Incident] = Field(default_factory=list)
    units: List[Unit] = Field(default_factory=list)
    road_conditions: List[RoadCondition] = Field(default_factory=list)
    candidate_plans: List[Plan] = Field(default_factory=list)
    recommended_plan: Optional[Plan] = None
    approved_plan: Optional[Plan] = None
    resilience_results: Dict[str, ResilienceResult] = Field(default_factory=dict)
    action_log: List[ActionLogEntry] = Field(default_factory=list)
    system_events: List[SystemEvent] = Field(default_factory=list)
    plan_diffs: List[PlanDiff] = Field(default_factory=list)
    decision_confidence: Optional[DecisionConfidence] = None
    decision_debts: List[DecisionDebt] = Field(default_factory=list)
    active_missions: Dict[str, DispatchMission] = Field(default_factory=dict)
    latest_impact_analysis: Optional[Any] = None


    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def log_action(self, agent: str, action: str, details: str = "") -> None:
        """Append a structured entry to the action log."""
        self.action_log.append(
            ActionLogEntry(
                timestamp=datetime.now().isoformat(timespec="seconds"),
                version=self.version,
                agent=agent,
                action=action,
                details=details,
            )
        )

    def increment_version(self) -> None:
        self.version += 1

    def get_available_units(self) -> List[Unit]:
        return [u for u in self.units if u.status == UnitStatus.AVAILABLE]

    def get_unit(self, unit_id: str) -> Optional[Unit]:
        for u in self.units:
            if u.id == unit_id:
                return u
        return None

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        for inc in self.incidents:
            if inc.id == incident_id:
                return inc
        return None

    def snapshot(self) -> "CrisisState":
        """Return a deep copy of the current state."""
        return self.model_copy(deep=True)

    def dispatch_unit(self, unit_id: str, incident_id: str, route: RouteOption) -> None:
        """Create a DispatchMission and transition unit to EN_ROUTE."""
        import uuid
        unit = self.get_unit(unit_id)
        if not unit or unit.status not in (UnitStatus.AVAILABLE, UnitStatus.ASSIGNED):
            self.log_action("Commander", "Dispatch Rejected", f"Unit {unit_id} is {unit.status if unit else 'missing'}")
            return
            
        unit.status = UnitStatus.EN_ROUTE
        unit.current_incident = incident_id
        
        mission_id = f"MSN-{str(uuid.uuid4())[:8].upper()}"
        mission = DispatchMission(
            mission_id=mission_id,
            unit_id=unit_id,
            incident_id=incident_id,
            route_id=route.route_id,
            status="EN_ROUTE",
            progress_percent=0.0,
            current_latitude=unit.latitude,
            current_longitude=unit.longitude,
            destination_latitude=route.waypoints[-1][0] if route.waypoints else unit.latitude,
            destination_longitude=route.waypoints[-1][1] if route.waypoints else unit.longitude,
            eta_minutes=route.eta_minutes,
            distance_remaining_km=route.distance_km
        )
        # Store full route dynamically as an extra attribute (we can use a shadow dict to store objects without breaking pydantic)
        self.active_missions[mission_id] = mission
        if not hasattr(self, '_mission_routes'):
            self._mission_routes = {}
        self._mission_routes[mission_id] = route
        
        self.log_action(
            "Commander",
            "DISPATCHED",
            f"{unit_id} -> {incident_id} | Route: {route.name} | ETA: {route.eta_minutes} min"
        )
        self.increment_version()

    def get_mission_route(self, mission_id: str) -> Optional[RouteOption]:
        if hasattr(self, '_mission_routes'):
            return self._mission_routes.get(mission_id)
        return None

    def advance_missions(self, step_percent: float = 15.0) -> None:
        """Advance all EN_ROUTE missions by a fixed percentage."""
        from backend.models import UnitStatus
        advanced = False
        for m_id, mission in self.active_missions.items():
            if mission.status == "EN_ROUTE":
                mission.progress_percent = min(100.0, mission.progress_percent + step_percent)
                route = self.get_mission_route(m_id)
                
                if route and route.waypoints:
                    # Interpolate position (simple linear for demo)
                    idx = int((mission.progress_percent / 100.0) * (len(route.waypoints) - 1))
                    mission.current_latitude = route.waypoints[idx][0]
                    mission.current_longitude = route.waypoints[idx][1]
                    
                mission.eta_minutes = max(0.0, round(mission.eta_minutes - (mission.eta_minutes * (step_percent/100.0)), 1))
                mission.distance_remaining_km = max(0.0, round(mission.distance_remaining_km - (mission.distance_remaining_km * (step_percent/100.0)), 1))
                
                if mission.progress_percent >= 100.0:
                    mission.status = "ON_SCENE"
                    unit = self.get_unit(mission.unit_id)
                    if unit: unit.status = UnitStatus.ON_SCENE
                    self.log_action("Simulator", "UNIT ARRIVED", f"{mission.unit_id} arrived at {mission.incident_id}")
                advanced = True
        
        if advanced:
            self.increment_version()

    def handle_road_block(self, road_id: str) -> None:
        """Triggered when a road block event occurs. Checks active missions and interrupts them."""
        from backend.route import calculate_routes
        interrupted = False
        for m_id, mission in self.active_missions.items():
            if mission.status == "EN_ROUTE":
                route = self.get_mission_route(m_id)
                if route and road_id in route.road_segments:
                    mission.status = "INTERRUPTED"
                    # Try to recalculate
                    new_routes = calculate_routes(
                        mission.current_latitude, mission.current_longitude,
                        mission.destination_latitude, mission.destination_longitude,
                        self.road_conditions
                    )
                    
                    if new_routes and new_routes[0].status == "FEASIBLE":
                        # Rescued!
                        new_r = new_routes[0]
                        impact = round(new_r.eta_minutes - mission.eta_minutes, 1)
                        self.log_action(
                            "Simulator", 
                            "ROUTE RECALCULATED", 
                            f"{mission.unit_id} rerouted around {road_id}. ETA Impact: +{impact} min"
                        )
                        mission.route_id = new_r.route_id
                        mission.status = "EN_ROUTE"
                        mission.eta_minutes = new_r.eta_minutes
                        mission.distance_remaining_km = new_r.distance_km
                        if hasattr(self, '_mission_routes'):
                            self._mission_routes[m_id] = new_r
                    else:
                        self.log_action(
                            "Simulator",
                            "NO FEASIBLE ROUTE",
                            f"{mission.unit_id} is trapped by {road_id} block."
                        )
                    interrupted = True
        
        if interrupted:
            self.increment_version()


class StateHistory:
    """Immutable history of crisis-state snapshots."""

    def __init__(self) -> None:
        self.snapshots: List[CrisisState] = []

    def save(self, state: CrisisState) -> None:
        self.snapshots.append(state.snapshot())

    def get_version(self, version: int) -> Optional[CrisisState]:
        for s in self.snapshots:
            if s.version == version:
                return s
        return None

    def latest(self) -> Optional[CrisisState]:
        return self.snapshots[-1] if self.snapshots else None
