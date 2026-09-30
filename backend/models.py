"""
Crisis Command — Data Models
All Pydantic models for the deterministic MVP.
SIMULATION DATA — No real emergency data is used.
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class IncidentStatus(str, Enum):
    """Status of an emergency incident."""
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class UnitStatus(str, Enum):
    """Operational status of a response unit."""
    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    UNAVAILABLE = "UNAVAILABLE"
    BROKEN_DOWN = "BROKEN_DOWN"


class UnitType(str, Enum):
    """Type of response unit."""
    AMBULANCE = "ambulance"
    RESCUE_TEAM = "rescue_team"


class UrgencyLevel(str, Enum):
    """Urgency classification derived from severity score."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Core domain models
# ---------------------------------------------------------------------------

class Incident(BaseModel):
    """An emergency incident requiring response."""
    id: str
    type: str
    location: str
    latitude: float
    longitude: float
    people_affected: int = 0
    people_trapped: int = 0
    vulnerable_people: int = 0
    life_threat: bool = False
    time_critical: bool = False
    spreading_hazard: bool = False
    required_units: Dict[UnitType, int] = Field(default_factory=dict)
    status: IncidentStatus = IncidentStatus.NEW
    severity: Optional[int] = None
    urgency: Optional[UrgencyLevel] = None
    timestamp: Optional[str] = None


class Unit(BaseModel):
    """A response unit (ambulance, rescue team, etc.)."""
    id: str
    type: UnitType
    status: UnitStatus = UnitStatus.AVAILABLE
    capacity: int = 1
    latitude: float = 0.0
    longitude: float = 0.0
    current_incident: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    available_at: Optional[str] = None


class RoadCondition(BaseModel):
    """Road segment condition for route planning."""
    id: str
    name: str
    from_node: str = ""
    to_node: str = ""
    from_lat: float
    from_lon: float
    to_lat: float
    to_lon: float
    distance_km: float = 0.0
    speed_kmh: float = 40.0
    blocked: bool = False
    delay_minutes: float = 0.0
    reason: Optional[str] = None


class RouteOption(BaseModel):
    """A feasible or blocked path on the road graph."""
    route_id: str
    name: str = "Route"
    waypoints: List[List[float]] = Field(default_factory=list) # [[lat, lon], ...]
    road_segments: List[str] = Field(default_factory=list)
    distance_km: float = 0.0
    eta_minutes: float = 0.0
    status: str = "FEASIBLE" # FEASIBLE, BLOCKED, NO_FEASIBLE_ROUTE
    blocked: bool = False
    reason: str = ""


class DispatchMission(BaseModel):
    """An active unit dispatch containing live state tracking."""
    mission_id: str
    unit_id: str
    incident_id: str
    route_id: str
    status: str = "EN_ROUTE" # EN_ROUTE, ARRIVED, INTERRUPTED
    progress_percent: float = 0.0
    current_latitude: float = 0.0
    current_longitude: float = 0.0
    destination_latitude: float = 0.0
    destination_longitude: float = 0.0
    eta_minutes: float = 0.0
    distance_remaining_km: float = 0.0

# ---------------------------------------------------------------------------
# Plan-related models
# ---------------------------------------------------------------------------

class Assignment(BaseModel):
    """Assignment of a unit to an incident."""
    incident_id: str
    unit_id: str
    eta_minutes: float = 0.0


class Violation(BaseModel):
    """A constraint violation in a plan."""
    type: str
    unit: Optional[str] = None
    incident: Optional[str] = None
    message: str


class ValidationResult(BaseModel):
    """Result of constraint validation on a plan."""
    valid: bool
    violations: List[Violation] = Field(default_factory=list)


class PlanMetrics(BaseModel):
    """Quantitative metrics for evaluating a plan."""
    critical_covered: int = 0
    high_covered: int = 0
    medium_covered: int = 0
    low_covered: int = 0
    total_covered: int = 0
    total_incidents: int = 0
    uncovered_incidents: List[str] = Field(default_factory=list)
    average_eta: float = 0.0
    max_eta: float = 0.0
    reserve_units: int = 0
    units_reassigned: int = 0
    resilience_score: float = 0.0
    fragility_index: float = 0.0
    human_attention_required: bool = False
    attention_reasons: List[str] = Field(default_factory=list)


class Plan(BaseModel):
    """A candidate response plan."""
    id: str
    strategy_name: str
    assignments: List[Assignment] = Field(default_factory=list)
    validation: Optional[ValidationResult] = None
    metrics: Optional[PlanMetrics] = None
    score: Optional[float] = None
    explanation: str = ""
    ai_explanation: Optional[Dict] = None


# ---------------------------------------------------------------------------
# Resilience models
# ---------------------------------------------------------------------------

class FailureScenario(BaseModel):
    """A hypothetical failure scenario for resilience testing."""
    scenario_id: str
    type: str  # "unit_failure", "road_block", "new_incident"
    target_id: str
    description: str


class FailureImpact(BaseModel):
    """Impact assessment of a failure scenario on a plan."""
    scenario: FailureScenario
    plan_still_valid: bool
    affected_incidents: List[str] = Field(default_factory=list)
    uncovered_incidents: List[str] = Field(default_factory=list)
    eta_increase_minutes: float = 0.0
    reserve_remaining: int = 0
    recovery_possible: bool = True
    severity_impact: str = "NONE"  # NONE, LOW, MEDIUM, HIGH, CRITICAL


class ResilienceResult(BaseModel):
    """Resilience analysis result for a plan."""
    plan_id: str
    resilience_score: float = 0.0
    fragility_index: float = 0.0
    worst_case_unit: Optional[str] = None
    worst_case_impact: Optional[FailureImpact] = None
    single_points_of_failure: List[str] = Field(default_factory=list)
    scenarios_tested: int = 0
    scenario_results: List[FailureImpact] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Diff / Log / Event models
# ---------------------------------------------------------------------------

class PlanDiff(BaseModel):
    """Difference between two plans showing what changed and why."""
    before_plan_id: str
    after_plan_id: str
    added_assignments: List[Assignment] = Field(default_factory=list)
    removed_assignments: List[Assignment] = Field(default_factory=list)
    changed_units: List[Dict] = Field(default_factory=list)
    newly_uncovered: List[str] = Field(default_factory=list)
    newly_covered: List[str] = Field(default_factory=list)
    eta_changes: Dict[str, float] = Field(default_factory=dict)
    explanation: str = ""
    trigger: str = ""
    reallocation_reasons: List[Dict] = Field(default_factory=list)


class ActionLogEntry(BaseModel):
    """An entry in the action log."""
    timestamp: str
    version: int
    agent: str
    action: str
    details: str = ""


class SystemEvent(BaseModel):
    """A system event (breakdown, road block, new incident, etc.)."""
    id: str
    type: str  # "breakdown", "road_block", "new_incident"
    target_id: str
    description: str
    timestamp: str


# ---------------------------------------------------------------------------
# Decision confidence + debt models
# ---------------------------------------------------------------------------

class ConfidenceFactor(BaseModel):
    """A single factor contributing to decision confidence."""
    label: str
    passed: bool
    detail: str = ""


class DecisionConfidence(BaseModel):
    """Deterministic decision confidence derived from runtime state.

    Level: HIGH | MEDIUM | LOW
    Calculated from: incident data completeness, unit availability,
    route availability, plan validity, resilience completion.
    Never claims a percentage unless calculated.
    """
    level: str = "LOW"   # HIGH | MEDIUM | LOW
    factors: List[ConfidenceFactor] = Field(default_factory=list)
    passed_count: int = 0
    total_count: int = 0


class DecisionDebt(BaseModel):
    """A decision dependency or vulnerability introduced by the current plan.

    Only populated when actual runtime data supports it.
    Never fabricated.
    """
    unit_id: str
    dependent_incident_ids: List[str] = Field(default_factory=list)
    is_spof: bool = False
    description: str = ""
    failure_impact: str = ""


# ---------------------------------------------------------------------------
# Event Model (Phase 1)
# ---------------------------------------------------------------------------

class NormalizedEvent(BaseModel):
    """A normalized event from any input source (simulation, operator, external)."""
    event_id: str
    timestamp: str
    source: str
    source_type: str  # "simulation", "operator", "external"
    event_type: str   # "weather_update", "new_incident", "road_block", "unit_failure", "system_replan"
    location: str
    payload: dict = Field(default_factory=dict)

