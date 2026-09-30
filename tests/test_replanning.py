"""Tests for replanning after situation changes."""

from backend.models import Incident, Unit, UnitStatus, UnitType, RoadCondition
from backend.severity import assess_incident
from backend.state import CrisisState, StateHistory
from backend.planner import generate_candidate_plans
from backend.comparator import compare_and_select
from backend.replanner import apply_unit_breakdown, apply_road_block, apply_new_incident


def _init_state():
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
    state = CrisisState(incidents=incs, units=units, road_conditions=roads)
    state = generate_candidate_plans(state)
    state = compare_and_select(state)
    return state


def test_breakdown_replanning():
    state = _init_state()
    history = StateHistory()
    v_before = state.version
    state = apply_unit_breakdown(state, history, "AMB-01")

    assert state.get_unit("AMB-01").status == UnitStatus.BROKEN_DOWN
    assert state.version > v_before
    assert len(state.system_events) > 0


def test_road_block_replanning():
    state = _init_state()
    history = StateHistory()
    v_before = state.version
    state = apply_road_block(state, history, "R1")

    road = next(r for r in state.road_conditions if r.id == "R1")
    assert road.blocked is True
    assert state.version > v_before


def test_new_incident_replanning():
    state = _init_state()
    history = StateHistory()
    new_inc = Incident(
        id="I3", type="Gas Leak", location="C", latitude=21.148, longitude=72.810,
        people_affected=15, people_trapped=3, vulnerable_people=5,
        life_threat=True, time_critical=True, spreading_hazard=True,
        required_units={UnitType.RESCUE_TEAM: 1, UnitType.AMBULANCE: 1},
    )
    v_before = state.version
    state = apply_new_incident(state, history, new_inc)

    assert len(state.incidents) == 3
    assert state.get_incident("I3") is not None
    assert state.version > v_before


def test_history_preserved():
    state = _init_state()
    history = StateHistory()
    history.save(state)
    v1 = state.version

    state = apply_unit_breakdown(state, history, "AMB-01")

    old = history.get_version(v1)
    assert old is not None
    assert old.get_unit("AMB-01").status == UnitStatus.AVAILABLE
