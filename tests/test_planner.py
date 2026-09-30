"""Tests for planner and comparator."""

from backend.models import Incident, Unit, UnitStatus, UnitType
from backend.severity import assess_incident
from backend.state import CrisisState
from backend.planner import generate_candidate_plans
from backend.comparator import compare_and_select, score_plan, calculate_metrics


def _scenario():
    incs = [
        Incident(id="I1", type="Flood", location="A", latitude=21.195, longitude=72.819,
                 people_affected=25, people_trapped=8, vulnerable_people=3,
                 life_threat=True, time_critical=True, spreading_hazard=True,
                 required_units={UnitType.RESCUE_TEAM: 2, UnitType.AMBULANCE: 1}),
        Incident(id="I2", type="Medical", location="B", latitude=21.175, longitude=72.831,
                 people_affected=4, vulnerable_people=2, life_threat=True, time_critical=True,
                 required_units={UnitType.AMBULANCE: 1}),
    ]
    for i in incs:
        assess_incident(i)

    units = [
        Unit(id="AMB-01", type=UnitType.AMBULANCE, status=UnitStatus.AVAILABLE, latitude=21.185, longitude=72.825),
        Unit(id="AMB-02", type=UnitType.AMBULANCE, status=UnitStatus.AVAILABLE, latitude=21.170, longitude=72.840),
        Unit(id="AMB-03", type=UnitType.AMBULANCE, status=UnitStatus.AVAILABLE, latitude=21.155, longitude=72.835),
        Unit(id="RES-01", type=UnitType.RESCUE_TEAM, status=UnitStatus.AVAILABLE, latitude=21.190, longitude=72.815),
        Unit(id="RES-02", type=UnitType.RESCUE_TEAM, status=UnitStatus.AVAILABLE, latitude=21.165, longitude=72.820),
    ]
    return CrisisState(incidents=incs, units=units)


def test_generates_three_plans():
    state = _scenario()
    state = generate_candidate_plans(state)
    assert len(state.candidate_plans) == 3


def test_plans_are_validated():
    state = _scenario()
    state = generate_candidate_plans(state)
    for plan in state.candidate_plans:
        assert plan.validation is not None


def test_compare_selects_a_plan():
    state = _scenario()
    state = generate_candidate_plans(state)
    state = compare_and_select(state)
    assert state.recommended_plan is not None


def test_invalid_plan_scores_zero():
    state = _scenario()
    state = generate_candidate_plans(state)
    for plan in state.candidate_plans:
        if plan.validation and not plan.validation.valid:
            s = score_plan(plan, state)
            assert s == 0.0


def test_no_feasible_plan():
    """All units busy → no feasible plan."""
    state = _scenario()
    for u in state.units:
        u.status = UnitStatus.UNAVAILABLE
    state = generate_candidate_plans(state)
    state = compare_and_select(state)
    assert state.recommended_plan is None


def test_version_increments():
    state = _scenario()
    v0 = state.version
    state = generate_candidate_plans(state)
    assert state.version > v0
    v1 = state.version
    state = compare_and_select(state)
    assert state.version > v1
