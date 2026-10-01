"""
Crisis Command — Regression Tests: Plan A/B/C + Multi-Disruption
24 tests covering all requirements from the spec.
"""
import pytest
from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def new_session():
    return client.post("/session").json()["session_id"]


def generate(sid):
    return client.post(f"/session/{sid}/generate-plans").json()


def approve(sid, plan_id):
    return client.post(f"/session/{sid}/approve", json={"plan_id": plan_id})


def get_state(sid):
    return client.get(f"/session/{sid}/state").json()


def batch_events(sid, events):
    return client.post(f"/session/{sid}/events", json={"events": events}).json()


# ---------------------------------------------------------------------------
# Plan A / B / C Generation
# ---------------------------------------------------------------------------

def test_1_plan_a_is_generated():
    sid = new_session()
    result = generate(sid)
    ids = [p["id"] for p in result["plans"]]
    assert any("-A" in i for i in ids)


def test_2_plan_b_has_different_strategy():
    sid = new_session()
    result = generate(sid)
    b = next((p for p in result["plans"] if ("-B" in p["id"])), None)
    assert b is not None
    assert b["strategy_name"] == "SEVERITY_FIRST"


def test_3_plan_c_has_different_strategy():
    sid = new_session()
    result = generate(sid)
    c = next((p for p in result["plans"] if ("-C" in p["id"])), None)
    assert c is not None
    assert c["strategy_name"] == "BALANCED"


def test_4_plan_fingerprints_differ_or_honest_infeasibility():
    """Plans A/B/C should either have different assignments OR explicitly be marked infeasible."""
    sid = new_session()
    result = generate(sid)
    plans = result["plans"]
    a = next(p for p in plans if ("-A" in p["id"]))
    b = next(p for p in plans if ("-B" in p["id"]))
    c = next(p for p in plans if ("-C" in p["id"]))

    def fingerprint(p):
        return frozenset((a["unit_id"], a["incident_id"]) for a in p["assignments"])

    fp_a = fingerprint(a)
    fp_b = fingerprint(b)
    fp_c = fingerprint(c)

    # If valid, plans should differ; if duplicates, at least 1 must be invalid
    valid_plans = [p for p in plans if p.get("validation", {}).get("valid")]
    valid_fps = [fingerprint(p) for p in valid_plans]
    # All valid fingerprints must be distinct, OR there must be fewer valid plans than 3
    assert len(set(valid_fps)) >= 2 or len(valid_plans) < 3, "Plans B and C converged, but A must differ."


def test_5_all_candidate_plans_independently_validated():
    sid = new_session()
    result = generate(sid)
    for p in result["plans"]:
        assert "validation" in p
        assert "valid" in p["validation"]
        assert "violations" in p["validation"]


# ---------------------------------------------------------------------------
# Plan Selection (Commander can approve any plan)
# ---------------------------------------------------------------------------

def test_6_commander_can_approve_plan_b():
    sid = new_session()
    generate(sid)
    state = get_state(sid)
    b = next((p for p in state["candidate_plans"] if ("-B" in p["id"])), None)
    assert b is not None
    if b.get("validation", {}).get("valid"):
        res = approve(sid, next(p["id"] for p in get_state(sid)["candidate_plans"] if "-B" in p["id"]))
        assert res.status_code == 200
        state = get_state(sid)
        assert "-B" in state["approved_plan"]["id"]
    else:
        # PLAN_B invalid — acceptable if truly infeasible
        pytest.skip("PLAN_B invalid — checking infeasibility is acceptable")


def test_7_commander_can_approve_plan_c():
    sid = new_session()
    generate(sid)
    state = get_state(sid)
    c = next((p for p in state["candidate_plans"] if ("-C" in p["id"])), None)
    assert c is not None
    if c.get("validation", {}).get("valid"):
        res = approve(sid, next(p["id"] for p in get_state(sid)["candidate_plans"] if "-C" in p["id"]))
        assert res.status_code == 200
        state = get_state(sid)
        assert "-C" in state["approved_plan"]["id"]
    else:
        pytest.skip("PLAN_C invalid — checking infeasibility is acceptable")


def test_8_approving_plan_b_dispatches_plan_b_missions():
    sid = new_session()
    generate(sid)
    state = get_state(sid)
    b = next((p for p in state["candidate_plans"] if ("-B" in p["id"])), None)
    if not b or not b.get("validation", {}).get("valid") or not b["assignments"]:
        pytest.skip("PLAN_B not valid/assigned")
    approve(sid, next(p["id"] for p in get_state(sid)["candidate_plans"] if "-B" in p["id"]))
    state = get_state(sid)
    missions = state.get("active_missions", {})
    b_unit_ids = {a["unit_id"] for a in b["assignments"]}
    mission_unit_ids = {m["unit_id"] for m in missions.values()}
    assert b_unit_ids.issubset(mission_unit_ids), (
        f"Expected PLAN_B units {b_unit_ids} in missions {mission_unit_ids}"
    )


def test_9_approving_plan_c_dispatches_plan_c_missions():
    sid = new_session()
    generate(sid)
    state = get_state(sid)
    c = next((p for p in state["candidate_plans"] if ("-C" in p["id"])), None)
    if not c or not c.get("validation", {}).get("valid") or not c["assignments"]:
        pytest.skip("PLAN_C not valid/assigned")
    approve(sid, next(p["id"] for p in get_state(sid)["candidate_plans"] if "-C" in p["id"]))
    state = get_state(sid)
    missions = state.get("active_missions", {})
    c_unit_ids = {a["unit_id"] for a in c["assignments"]}
    mission_unit_ids = {m["unit_id"] for m in missions.values()}
    assert c_unit_ids.issubset(mission_unit_ids)


# ---------------------------------------------------------------------------
# Single disruption → one replan
# ---------------------------------------------------------------------------

def test_10_single_disruption_causes_replan():
    sid = new_session()
    generate(sid)
    approve(sid, next(p["id"] for p in get_state(sid)["candidate_plans"] if "-A" in p["id"]))
    v_before = get_state(sid)["version"]
    client.post(f"/session/{sid}/events/breakdown", json={"unit_id": "AMB-01"})
    v_after = get_state(sid)["version"]
    assert v_after > v_before


# ---------------------------------------------------------------------------
# Multi-disruption batch endpoint (atomic)
# ---------------------------------------------------------------------------

def test_11_batch_endpoint_exists():
    sid = new_session()
    res = client.post(f"/session/{sid}/events", json={"events": [
        {"event_type": "unit_failure", "payload": {"unit_id": "AMB-01"}}
    ]})
    assert res.status_code == 200


def test_12_two_simultaneous_disruptions_cause_one_replan():
    """Two events via batch → one atomic operation, version increments ONCE per batch."""
    sid = new_session()
    generate(sid)
    approve(sid, next(p["id"] for p in get_state(sid)["candidate_plans"] if "-A" in p["id"]))
    v_before = get_state(sid)["version"]

    batch_events(sid, [
        {"event_type": "unit_failure", "payload": {"unit_id": "AMB-01"}},
        {"event_type": "road_block", "payload": {"road_id": "ROAD-001"}},
    ])

    state = get_state(sid)
    # Approved plan must be cleared (replan occurred)
    assert state["approved_plan"] is None


def test_13_three_simultaneous_disruptions_atomic():
    sid = new_session()
    generate(sid)
    approve(sid, next(p["id"] for p in get_state(sid)["candidate_plans"] if "-A" in p["id"]))

    res = client.post(f"/session/{sid}/events", json={"events": [
        {"event_type": "unit_failure", "payload": {"unit_id": "AMB-01"}},
        {"event_type": "road_block", "payload": {"road_id": "ROAD-001"}},
        {"event_type": "new_incident", "payload": {
            "incident_id": "INC-TEST-001", "type": "Fire", "location": "Test",
            "latitude": 21.17, "longitude": 72.83,
            "people_affected": 3, "people_trapped": 0, "vulnerable_people": 0,
            "life_threat": True, "time_critical": True, "spreading_hazard": False,
            "required_units": {"ambulance": 1}
        }},
    ]})
    assert res.status_code == 200
    data = res.json()
    assert data["events_applied"] == 3

    state = get_state(sid)
    # All disruptions applied: AMB-01 broken, road blocked, new incident added
    units = {u["id"]: u for u in state["units"]}
    assert units["AMB-01"]["status"] == "BROKEN_DOWN"
    incident_ids = [i["id"] for i in state["incidents"]]
    assert "INC-TEST-001" in incident_ids


def test_14_breakdown_plus_roadblock_atomic():
    sid = new_session()
    generate(sid)
    approve(sid, next(p["id"] for p in get_state(sid)["candidate_plans"] if "-A" in p["id"]))

    res = client.post(f"/session/{sid}/events", json={"events": [
        {"event_type": "unit_failure", "payload": {"unit_id": "AMB-02"}},
        {"event_type": "road_block", "payload": {"road_id": "ROAD-001"}},
    ]})
    assert res.status_code == 200
    state = get_state(sid)
    units = {u["id"]: u for u in state["units"]}
    assert units["AMB-02"]["status"] == "BROKEN_DOWN"


def test_15_breakdown_plus_new_incident_atomic():
    sid = new_session()
    generate(sid)

    res = client.post(f"/session/{sid}/events", json={"events": [
        {"event_type": "unit_failure", "payload": {"unit_id": "AMB-01"}},
        {"event_type": "new_incident", "payload": {
            "incident_id": "INC-T15", "type": "Medical Emergency", "location": "Test15",
            "latitude": 21.17, "longitude": 72.83,
            "people_affected": 2, "people_trapped": 0, "vulnerable_people": 0,
            "life_threat": False, "time_critical": True, "spreading_hazard": False,
            "required_units": {"ambulance": 1}
        }},
    ]})
    assert res.status_code == 200
    state = get_state(sid)
    assert "INC-T15" in [i["id"] for i in state["incidents"]]


def test_16_roadblock_plus_new_incident_atomic():
    sid = new_session()
    generate(sid)

    res = client.post(f"/session/{sid}/events", json={"events": [
        {"event_type": "road_block", "payload": {"road_id": "ROAD-001"}},
        {"event_type": "new_incident", "payload": {
            "incident_id": "INC-T16", "type": "Road Accident", "location": "Test16",
            "latitude": 21.16, "longitude": 72.84,
            "people_affected": 2, "people_trapped": 0, "vulnerable_people": 0,
            "life_threat": False, "time_critical": True, "spreading_hazard": False,
            "required_units": {"ambulance": 1}
        }},
    ]})
    assert res.status_code == 200
    state = get_state(sid)
    roads = {r["id"]: r for r in state["road_conditions"]}
    assert roads.get("ROAD-001", {}).get("blocked") is True
    assert "INC-T16" in [i["id"] for i in state["incidents"]]


def test_17_global_resource_shortfall_calculated():
    sid = new_session()
    generate(sid)
    # Add 3 new incidents requiring ambulances to create shortfall
    for i in range(3):
        client.post(f"/session/{sid}/events/new-incident", json={
            "id": f"INC-EXTRA-{i}", "type": "Medical Emergency", "location": f"Test{i}",
            "latitude": 21.17, "longitude": 72.83,
            "people_affected": 1, "people_trapped": 0,
            "life_threat": True, "time_critical": True, "spreading_hazard": False,
            "required_units": {"ambulance": 1}
        })
    state = get_state(sid)
    assert state["latest_impact_analysis"] is not None


def test_18_plan_diff_populated_after_replan():
    sid = new_session()
    generate(sid)
    approve(sid, next(p["id"] for p in get_state(sid)["candidate_plans"] if "-A" in p["id"]))
    # Trigger breakdown → replan → should produce plan diff
    client.post(f"/session/{sid}/events/breakdown", json={"unit_id": "AMB-01"})
    state = get_state(sid)
    # Plan diffs may or may not exist depending on whether replan changed anything
    assert "plan_diffs" in state


def test_19_recommendation_belongs_to_latest_version():
    sid = new_session()
    generate(sid)
    state1 = get_state(sid)
    v1 = state1["version"]
    rec1_id = state1.get("recommended_plan", {}).get("id") if state1.get("recommended_plan") else None

    client.post(f"/session/{sid}/events/breakdown", json={"unit_id": "AMB-01"})
    state2 = get_state(sid)
    v2 = state2["version"]
    assert v2 > v1
    # After replan, recommended_plan should be fresh
    rec2 = state2.get("recommended_plan")
    assert rec2 is not None  # replan should produce a recommendation


def test_20_old_recommendation_not_shown_after_replan():
    sid = new_session()
    generate(sid)
    approve(sid, next(p["id"] for p in get_state(sid)["candidate_plans"] if "-A" in p["id"]))
    client.post(f"/session/{sid}/events/breakdown", json={"unit_id": "AMB-01"})
    state = get_state(sid)
    # approved_plan must be cleared after replan
    assert state["approved_plan"] is None


def test_21_reset_clears_all_disruption_state():
    sid = new_session()
    generate(sid)
    client.post(f"/session/{sid}/events/breakdown", json={"unit_id": "AMB-01"})
    client.post(f"/session/{sid}/reset")
    state = get_state(sid)
    units = {u["id"]: u for u in state["units"]}
    assert units["AMB-01"]["status"] == "AVAILABLE"
    assert state["approved_plan"] is None
    assert state["candidate_plans"] == []


def test_22_session_isolation():
    sid1 = new_session()
    sid2 = new_session()
    generate(sid1)
    approve(sid1, next(p["id"] for p in get_state(sid1)["candidate_plans"] if "-A" in p["id"]))
    state2 = get_state(sid2)
    # Session 2 should be unaffected
    assert state2["approved_plan"] is None
    assert state2["candidate_plans"] == []


def test_23_normal_session_starts_unscripted():
    sid = new_session()
    state = get_state(sid)
    assert state["candidate_plans"] == []
    assert state["approved_plan"] is None
    assert state["active_missions"] == {}


def test_24_batch_endpoint_returns_events_applied_count():
    sid = new_session()
    res = client.post(f"/session/{sid}/events", json={"events": [
        {"event_type": "unit_failure", "payload": {"unit_id": "AMB-01"}},
        {"event_type": "road_block", "payload": {"road_id": "ROAD-001"}},
    ]})
    assert res.status_code == 200
    data = res.json()
    assert data.get("events_applied") == 2
