import pytest
from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)

def test_get_state_active_missions_regression():
    # 1. Create a session
    resp = client.post("/session")
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]
    
    # 2. Get state immediately after initialization
    resp = client.get(f"/session/{session_id}/state")
    assert resp.status_code == 200
    
    data = resp.json()
    assert "active_missions" in data
    assert isinstance(data["active_missions"], dict)
