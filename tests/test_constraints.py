"""Tests for constraint checker."""

from backend.models import (
    Assignment, Incident, Plan, Unit, UnitStatus, UnitType, UrgencyLevel,
)
from backend.state import CrisisState
from backend.constraints import validate_plan


def _inc(id="I1", utype=UnitType.AMBULANCE, count=1):
    return Incident(
        id=id, type="T", location="A", latitude=0, longitude=0,
        people_affected=1, required_units={utype: count},
    )


def _unit(id="U1", utype=UnitType.AMBULANCE, status=UnitStatus.AVAILABLE):
    return Unit(id=id, type=utype, status=status, capacity=1, latitude=0, longitude=0)


def test_valid_plan():
    state = CrisisState(incidents=[_inc()], units=[_unit("U1"), _unit("U2")])
    plan = Plan(id="P", strategy_name="T", assignments=[
        Assignment(incident_id="I1", unit_id="U1"),
    ])
    result = validate_plan(plan, state)
    assert result.valid


def test_nonexistent_unit():
    state = CrisisState(incidents=[_inc()], units=[_unit("U1")])
    plan = Plan(id="P", strategy_name="T", assignments=[
        Assignment(incident_id="I1", unit_id="GHOST"),
    ])
    result = validate_plan(plan, state)
    assert not result.valid
    assert any(v.type == "NONEXISTENT_UNIT" for v in result.violations)


def test_unavailable_unit():
    state = CrisisState(incidents=[_inc()], units=[_unit("U1", status=UnitStatus.BROKEN_DOWN)])
    plan = Plan(id="P", strategy_name="T", assignments=[
        Assignment(incident_id="I1", unit_id="U1"),
    ])
    result = validate_plan(plan, state)
    assert not result.valid
    assert any(v.type == "UNAVAILABLE_UNIT" for v in result.violations)


def test_duplicate_assignment():
    state = CrisisState(
        incidents=[_inc("I1"), _inc("I2")],
        units=[_unit("U1")],
    )
    plan = Plan(id="P", strategy_name="T", assignments=[
        Assignment(incident_id="I1", unit_id="U1"),
        Assignment(incident_id="I2", unit_id="U1"),
    ])
    result = validate_plan(plan, state)
    assert not result.valid
    assert any(v.type == "DUPLICATE_ASSIGNMENT" for v in result.violations)


def test_wrong_unit_type():
    state = CrisisState(
        incidents=[_inc(utype=UnitType.RESCUE_TEAM)],
        units=[_unit("U1", utype=UnitType.AMBULANCE), _unit("U2")],
    )
    plan = Plan(id="P", strategy_name="T", assignments=[
        Assignment(incident_id="I1", unit_id="U1"),
    ])
    result = validate_plan(plan, state)
    assert not result.valid
    assert any(v.type == "WRONG_UNIT_TYPE" for v in result.violations)


def test_insufficient_resources():
    state = CrisisState(
        incidents=[_inc(count=2)],
        units=[_unit("U1"), _unit("U2"), _unit("U3")],
    )
    plan = Plan(id="P", strategy_name="T", assignments=[
        Assignment(incident_id="I1", unit_id="U1"),  # only 1 of 2 needed
    ])
    result = validate_plan(plan, state)
    assert not result.valid
    assert any(v.type == "INSUFFICIENT_RESOURCES" for v in result.violations)


def test_reserve_violation():
    state = CrisisState(
        incidents=[_inc("I1"), _inc("I2")],
        units=[_unit("U1"), _unit("U2")],  # 2 available, both assigned = 0 reserve
    )
    plan = Plan(id="P", strategy_name="T", assignments=[
        Assignment(incident_id="I1", unit_id="U1"),
        Assignment(incident_id="I2", unit_id="U2"),
    ])
    result = validate_plan(plan, state)
    assert not result.valid
    assert any(v.type == "RESERVE_VIOLATION" for v in result.violations)


def test_invalid_incident():
    state = CrisisState(incidents=[_inc()], units=[_unit("U1")])
    plan = Plan(id="P", strategy_name="T", assignments=[
        Assignment(incident_id="GHOST", unit_id="U1"),
    ])
    result = validate_plan(plan, state)
    assert not result.valid
    assert any(v.type == "INVALID_INCIDENT" for v in result.violations)


def test_eta_exceeded():
    state = CrisisState(incidents=[_inc()], units=[_unit("U1"), _unit("U2")])
    plan = Plan(id="P", strategy_name="T", assignments=[
        Assignment(incident_id="I1", unit_id="U1", eta_minutes=35.0),
    ])
    result = validate_plan(plan, state)
    assert not result.valid
    assert any(v.type == "ETA_EXCEEDED" for v in result.violations)
