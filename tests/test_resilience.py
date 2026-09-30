"""Tests for counterfactual resilience engine."""

from backend.models import Incident, Unit, UnitStatus, UnitType, RoadCondition
from backend.severity import assess_incident
from backend.state import CrisisState
from backend.planner import generate_candidate_plans
from backend.comparator import compare_and_select
from backend.resilience import (
    generate_failure_scenarios,
    simulate_failure,
    evaluate_plan_resilience,
)


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
    roads = [
        RoadCondition(id="R1", name="Test Road", from_lat=21.195, from_lon=72.819,
                      to_lat=21.185, to_lon=72.825),
    ]
    return CrisisState(incidents=incs, units=units, road_conditions=roads)


def test_scenarios_generated():
    state = _scenario()
    state = generate_candidate_plans(state)
    state = compare_and_select(state)
    plan = state.recommended_plan
    assert plan is not None
    scenarios = generate_failure_scenarios(plan, state)
    assert len(scenarios) > 0


def test_simulation_does_not_mutate_state():
    state = _scenario()
    state = generate_candidate_plans(state)
    state = compare_and_select(state)
    plan = state.recommended_plan
    assert plan is not None

    original_statuses = {u.id: u.status for u in state.units}
    scenarios = generate_failure_scenarios(plan, state)
    for s in scenarios:
        simulate_failure(s, plan, state)

    for u in state.units:
        assert u.status == original_statuses[u.id], f"State mutated for {u.id}"


def test_resilience_scores_in_range():
    state = _scenario()
    state = generate_candidate_plans(state)
    state = compare_and_select(state)
    plan = state.recommended_plan
    assert plan is not None
    result = evaluate_plan_resilience(plan, state)
    assert 0 <= result.resilience_score <= 100
    assert 0 <= result.fragility_index <= 100
    assert result.resilience_score + result.fragility_index == 100


def test_unit_failure_impact():
    state = _scenario()
    state = generate_candidate_plans(state)
    state = compare_and_select(state)
    plan = state.recommended_plan
    assert plan is not None
    result = evaluate_plan_resilience(plan, state)
    assert result.scenarios_tested > 0
    for impact in result.scenario_results:
        assert impact.scenario is not None
        assert impact.severity_impact in ("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL")
