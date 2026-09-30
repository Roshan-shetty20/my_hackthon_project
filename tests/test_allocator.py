"""Tests for resource allocator."""

from backend.models import Incident, Unit, UnitStatus, UnitType
from backend.severity import assess_incident
from backend.state import CrisisState
from backend.allocator import (
    generate_plan_a_nearest,
    generate_plan_b_severity,
    generate_plan_c_balanced,
)


def _scenario():
    """Standard 3-incident, 5-unit scenario."""
    incs = [
        Incident(id="I1", type="Flood", location="A", latitude=21.195, longitude=72.819,
                 people_affected=25, people_trapped=8, vulnerable_people=3,
                 life_threat=True, time_critical=True, spreading_hazard=True,
                 required_units={UnitType.RESCUE_TEAM: 2, UnitType.AMBULANCE: 1}),
        Incident(id="I2", type="Medical", location="B", latitude=21.175, longitude=72.831,
                 people_affected=4, vulnerable_people=2, life_threat=True, time_critical=True,
                 required_units={UnitType.AMBULANCE: 1}),
        Incident(id="I3", type="Accident", location="C", latitude=21.158, longitude=72.847,
                 people_affected=5, people_trapped=1, time_critical=True,
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


def test_plan_a_generates_assignments():
    state = _scenario()
    plan = generate_plan_a_nearest(state)
    assert len(plan.assignments) > 0


def test_plan_b_prioritises_severity():
    state = _scenario()
    plan = generate_plan_b_severity(state)
    # I1 is highest severity; its assignments should appear first
    if plan.assignments:
        first_inc = plan.assignments[0].incident_id
        assert first_inc == "I1", f"Expected I1 first, got {first_inc}"


def test_plan_c_maintains_reserve():
    """Balanced plan should keep at least 1 reserve unit."""
    state = _scenario()
    plan = generate_plan_c_balanced(state)
    assigned = {a.unit_id for a in plan.assignments}
    available = sum(1 for u in state.units if u.status == UnitStatus.AVAILABLE)
    reserve = available - len(assigned)
    assert reserve >= 1, f"Expected reserve >= 1, got {reserve}"


def test_no_assignment_for_busy_units():
    """No plan should assign a BUSY unit."""
    state = _scenario()
    for u in state.units:
        u.status = UnitStatus.UNAVAILABLE
    plan = generate_plan_a_nearest(state)
    assert len(plan.assignments) == 0
