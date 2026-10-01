import pytest
from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)

def test_1_generate_plans_clears_approval():
    # TEST 1: Generate Plans clears previous approval
    res = client.post("/session")
    sid = res.json()["session_id"]
    
    # 1. Generate plans
    res = client.post(f"/session/{sid}/generate-plans")
    assert res.status_code == 200
    
    # 2. Approve plan
    plan_id = res.json()["recommended_plan"]["id"]
    client.post(f"/session/{sid}/approve", json={"plan_id": plan_id})
    state = client.get(f"/session/{sid}/state").json()
    assert state["approved_plan"] is not None
    
    # 3. Generate plans again
    client.post(f"/session/{sid}/generate-plans")
    state = client.get(f"/session/{sid}/state").json()
    assert state["approved_plan"] is None

def test_2_breakdown_clears_approval():
    # TEST 2: Breakdown clears approval
    res = client.post("/session")
    sid = res.json()["session_id"]
    client.post(f"/session/{sid}/generate-plans")
    state = client.get(f"/session/{sid}/state").json()
    client.post(f"/session/{sid}/approve", json={"plan_id": state["recommended_plan"]["id"]})
    
    client.post(f"/session/{sid}/events/breakdown", json={"unit_id": "AMB-01"})
    state = client.get(f"/session/{sid}/state").json()
    assert state["approved_plan"] is None

def test_3_roadblock_clears_approval_if_interrupted():
    # TEST 3: Roadblock clears approval if interrupted
    res = client.post("/session")
    sid = res.json()["session_id"]
    client.post(f"/session/{sid}/generate-plans")
    state = client.get(f"/session/{sid}/state").json()
    client.post(f"/session/{sid}/approve", json={"plan_id": state["recommended_plan"]["id"]})
    
    client.post(f"/session/{sid}/events", json={"events": [{"event_type": "road_block", "payload": {"road_id": "ROAD-001"}}]} )
    state = client.get(f"/session/{sid}/state").json()
    # It might or might not clear depending on if it caused an interruption
    # But analyze_global_impact sets replan_required=True for road_block, so it should clear it!
    assert state["approved_plan"] is None

def test_4_new_incident_clears_approval():
    # TEST 4: New incident clears approval
    res = client.post("/session")
    sid = res.json()["session_id"]
    client.post(f"/session/{sid}/generate-plans")
    state = client.get(f"/session/{sid}/state").json()
    client.post(f"/session/{sid}/approve", json={"plan_id": state["recommended_plan"]["id"]})
    
    new_inc = {
        "id": "INC-NEW", "type": "Fire", "location": "Test", 
        "latitude": 0, "longitude": 0, "required_units": {"AMBULANCE": 1}
    }
    client.post(f"/session/{sid}/events/new-incident", json=new_inc)
    state = client.get(f"/session/{sid}/state").json()
    assert state["approved_plan"] is None

def test_5_reject_clears_approval():
    # TEST 5: Reject clears approval
    res = client.post("/session")
    sid = res.json()["session_id"]
    client.post(f"/session/{sid}/generate-plans")
    state = client.get(f"/session/{sid}/state").json()
    client.post(f"/session/{sid}/approve", json={"plan_id": state["recommended_plan"]["id"]})
    
    client.post(f"/session/{sid}/reject")
    state = client.get(f"/session/{sid}/state").json()
    assert state["approved_plan"] is None

def test_6_simulate_step_clears_approval_on_disruption():
    # TEST 6: simulate_step clears approval on disruption
    res = client.post("/session")
    sid = res.json()["session_id"]
    client.post(f"/session/{sid}/generate-plans")
    state = client.get(f"/session/{sid}/state").json()
    client.post(f"/session/{sid}/approve", json={"plan_id": state["recommended_plan"]["id"]})
    
    # offset 15 (weather update) -> no replan needed
    # offset 22 (road block) -> replan needed
    client.post(f"/session/{sid}/simulate-step") # weather
    client.post(f"/session/{sid}/simulate-step") # road block
    state = client.get(f"/session/{sid}/state").json()
    assert state["approved_plan"] is None

def test_7_get_explanation_returns_deterministic_fallback():
    # TEST 7: AI Command Brief explanation format
    res = client.post("/session")
    sid = res.json()["session_id"]
    client.post(f"/session/{sid}/generate-plans")
    
    # Without gemini configured, it should return deterministic fallback
    expl = client.get(f"/session/{sid}/explanation").json()
    assert "explanation_source" in expl
    # In Golden Demo without Gemini, the fallback generator provides trade-offs
    assert "tradeoff" in expl

def test_8_simulate_step_advances_version():
    # TEST 8: State version increments
    res = client.post("/session")
    sid = res.json()["session_id"]
    
    state1 = client.get(f"/session/{sid}/state").json()
    client.post(f"/session/{sid}/simulate-step")
    state2 = client.get(f"/session/{sid}/state").json()
    
    assert state2["version"] > state1["version"]
