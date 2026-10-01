import pytest
from unittest.mock import patch, MagicMock
from backend.models import Incident, Unit, UnitType, RoadCondition, NormalizedEvent
from backend.state import CrisisState, StateHistory
from backend.replanner import apply_events_batch
from backend.llm.gemini_provider import GeminiProvider

def _create_state():
    return CrisisState(
        incidents=[],
        units=[
            Unit(id="A1", type=UnitType.AMBULANCE),
            Unit(id="A2", type=UnitType.AMBULANCE),
            Unit(id="R1", type=UnitType.RESCUE_TEAM),
        ],
        road_conditions=[RoadCondition(id="R-1", name="Main Road", from_node="A", to_node="B", from_lat=0, from_lon=0, to_lat=0, to_lon=0)]
    )

def _ev_new(inc_id, sev=None, inc_type="MEDICAL", trapped=0, people=0):
    return NormalizedEvent(
        event_id=f"EV-{inc_id}", timestamp="12:00", source="test", source_type="test",
        event_type="new_incident", location="Test Loc",
        payload={
            "incident_id": inc_id, "type": inc_type, "latitude": 0.0, "longitude": 0.0,
            "people_trapped": trapped, "people_affected": people
        }
    )

def test_two_simultaneous_incidents():
    st = _create_state()
    h = StateHistory()
    evs = [_ev_new("INC-01"), _ev_new("INC-02")]
    st = apply_events_batch(st, h, evs)
    assert len(st.incidents) == 2
    assert st.latest_impact_analysis is not None
    assert len(st.candidate_plans) == 3

def test_three_simultaneous_incidents():
    st = _create_state()
    h = StateHistory()
    evs = [_ev_new("INC-01"), _ev_new("INC-02"), _ev_new("INC-03")]
    st = apply_events_batch(st, h, evs)
    assert len(st.incidents) == 3

def test_two_critical_competing_for_one_ambulance():
    st = CrisisState(
        incidents=[], units=[Unit(id="A1", type=UnitType.AMBULANCE)], road_conditions=[]
    )
    h = StateHistory()
    evs = [_ev_new("INC-01", inc_type="MEDICAL", people=20), _ev_new("INC-02", inc_type="MEDICAL", people=20)]
    st = apply_events_batch(st, h, evs)
    imp = st.latest_impact_analysis
    assert "ambulance" in imp["resource_shortfalls"]
    assert imp["resource_shortfalls"]["ambulance"] >= 1

def test_equal_severity_incidents():
    st = _create_state()
    h = StateHistory()
    ev1 = _ev_new("INC-01", inc_type="MEDICAL")
    ev2 = _ev_new("INC-02", inc_type="MEDICAL", trapped=1) # Tie breaker: trapped
    st = apply_events_batch(st, h, [ev1, ev2])
    plan = st.candidate_plans[0]
    assigned_incidents = [a.incident_id for a in plan.assignments]
    assert "INC-02" in assigned_incidents

def test_incident_and_ambulance_breakdown():
    st = _create_state()
    h = StateHistory()
    ev1 = _ev_new("INC-01")
    ev2 = NormalizedEvent(event_id="E2", timestamp="12", source="test", source_type="test", event_type="unit_failure", location="", payload={"unit_id": "A1"})
    st = apply_events_batch(st, h, [ev1, ev2])
    assert st.get_unit("A1").status.value == "BROKEN_DOWN"
    assert len(st.incidents) == 1

def test_incident_and_road_block():
    st = _create_state()
    h = StateHistory()
    ev1 = _ev_new("INC-01")
    ev2 = NormalizedEvent(event_id="E2", timestamp="12", source="test", source_type="test", event_type="road_block", location="", payload={"road_id": "R-1"})
    st = apply_events_batch(st, h, [ev1, ev2])
    assert st.road_conditions[0].blocked == True
    assert len(st.incidents) == 1

def test_simultaneous_incidents_and_breakdown():
    st = _create_state()
    h = StateHistory()
    evs = [_ev_new("INC-01"), _ev_new("INC-02"), NormalizedEvent(event_id="E2", timestamp="12", source="test", source_type="test", event_type="unit_failure", location="", payload={"unit_id": "A1"})]
    st = apply_events_batch(st, h, evs)
    assert st.get_unit("A1").status.value == "BROKEN_DOWN"
    assert len(st.incidents) == 2

def test_simultaneous_incidents_and_road_block():
    st = _create_state()
    h = StateHistory()
    evs = [_ev_new("INC-01"), _ev_new("INC-02"), NormalizedEvent(event_id="E2", timestamp="12", source="test", source_type="test", event_type="road_block", location="", payload={"road_id": "R-1"})]
    st = apply_events_batch(st, h, evs)
    assert st.road_conditions[0].blocked == True
    assert len(st.incidents) == 2

def test_gas_leak_with_15_affected():
    st = _create_state()
    h = StateHistory()
    ev1 = _ev_new("INC-01", inc_type="GAS LEAK", people=15)
    st = apply_events_batch(st, h, [ev1])
    inc = st.incidents[0]
    assert inc.severity > 1
    assert inc.required_units[UnitType.RESCUE_TEAM] >= 1

def test_missing_hazard_information():
    st = _create_state()
    h = StateHistory()
    ev1 = _ev_new("INC-01", inc_type="HAZMAT")
    st = apply_events_batch(st, h, [ev1])
    inc = st.incidents[0]
    assert "hazard_radius" in inc.assessment.missing_information
    assert inc.assessment.confidence == "DETERMINISTIC_LOW"

def test_gemini_unavailable():
    gp = GeminiProvider()
    with patch.dict('os.environ', clear=True):
        assert gp.is_available() == False

def test_gemini_connected():
    gp = GeminiProvider()
    with patch.dict('os.environ', {'GEMINI_API_KEY': 'mock'}):
        assert gp.is_available() == True

def test_atomic_update_no_duplicate_replans():
    st = _create_state()
    h = StateHistory()
    evs = [_ev_new("INC-01"), _ev_new("INC-02")]
    st = apply_events_batch(st, h, evs)
    count_replans = sum(1 for e in st.action_log if e.action == "Replanning complete")
    assert count_replans == 1

def test_session_isolation():
    from backend.server import _get_session
    from backend.server import create_session; s1 = create_session().get("session_id"); s1 = _get_session(s1)
    s2 = create_session().get("session_id"); s2 = _get_session(s2)
    assert s1 is not s2
    assert "state" in s1
    assert "state" in s2
    s1["state"].version = 999
    assert s2["state"].version == 1

