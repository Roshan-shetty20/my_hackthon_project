"""
Crisis Command — FastAPI REST API

All endpoints use the same backend service layer as the Streamlit dashboard.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from backend.models import Incident, UnitType
from backend.severity import assess_incident
from backend.planner import generate_candidate_plans
from backend.comparator import compare_and_select
from backend.resilience import evaluate_plan_resilience
from backend.replanner import apply_unit_breakdown, apply_road_block, apply_new_incident
from backend.state import CrisisState, StateHistory
from backend.db import init_db, save_state

# ---------------------------------------------------------------------------
# App state (in-memory for MVP; persisted to SQLite on key events)
# ---------------------------------------------------------------------------

app = FastAPI(title="Crisis Command API", version="1.0.0")
_state: Optional[CrisisState] = None
_history = StateHistory()


def _get_state() -> CrisisState:
    global _state
    if _state is None:
        raise HTTPException(status_code=400, detail="Crisis not initialised. POST /initialize first.")
    return _state


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_json(filename: str):
    path = Path(__file__).parent.parent / "data" / filename
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ApproveRequest(BaseModel):
    plan_id: str


class BreakdownRequest(BaseModel):
    unit_id: str


class RoadBlockRequest(BaseModel):
    road_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/initialize")
def initialize():
    global _state, _history
    _history = StateHistory()

    incidents_raw = _load_json("incidents.json")
    units_raw = _load_json("units.json")
    roads_raw = _load_json("roads.json")

    from backend.models import Unit, RoadCondition
    incidents = [Incident(**{k: v for k, v in d.items() if k != "_comment"}) for d in incidents_raw]
    units = [Unit(**{k: v for k, v in d.items() if k != "_comment"}) for d in units_raw]
    roads = [RoadCondition(**{k: v for k, v in d.items() if k != "_comment"}) for d in roads_raw]

    for inc in incidents:
        assess_incident(inc)

    _state = CrisisState(incidents=incidents, units=units, road_conditions=roads)
    _state.log_action("System", "Crisis initialised", f"{len(incidents)} incidents, {len(units)} units")
    _history.save(_state)
    return {"status": "initialised", "version": _state.version}


@app.get("/state")
def get_state():
    return _get_state().model_dump()


@app.get("/incidents")
def get_incidents():
    return [inc.model_dump() for inc in _get_state().incidents]


@app.get("/units")
def get_units():
    return [u.model_dump() for u in _get_state().units]


@app.post("/plan")
def plan():
    global _state
    state = _get_state()
    state = generate_candidate_plans(state)
    state = compare_and_select(state)
    # Resilience
    for p in state.candidate_plans:
        if p.validation and p.validation.valid and len(p.assignments) > 0:
            res = evaluate_plan_resilience(p, state)
            state.resilience_results[p.id] = res
            if p.metrics:
                p.metrics.resilience_score = res.resilience_score
                p.metrics.fragility_index = res.fragility_index
    _state = state
    _history.save(state)
    return {
        "version": state.version,
        "plans": [p.model_dump() for p in state.candidate_plans],
        "recommended": state.recommended_plan.model_dump() if state.recommended_plan else None,
    }


@app.get("/plans")
def get_plans():
    return [p.model_dump() for p in _get_state().candidate_plans]


@app.get("/plans/{plan_id}")
def get_plan(plan_id: str):
    for p in _get_state().candidate_plans:
        if p.id == plan_id:
            return p.model_dump()
    raise HTTPException(404, f"Plan {plan_id} not found")


@app.get("/resilience/{plan_id}")
def get_resilience(plan_id: str):
    state = _get_state()
    if plan_id in state.resilience_results:
        return state.resilience_results[plan_id].model_dump()
    raise HTTPException(404, f"Resilience result for {plan_id} not found")


@app.get("/action-log")
def get_action_log():
    return [e.model_dump() for e in _get_state().action_log]


@app.post("/approve")
def approve(req: ApproveRequest):
    global _state
    state = _get_state()
    for p in state.candidate_plans:
        if p.id == req.plan_id:
            if p.validation and not p.validation.valid:
                raise HTTPException(400, f"Plan {req.plan_id} is invalid and cannot be approved.")
            state.approved_plan = p
            state.log_action("Dispatcher", f"Approved plan {req.plan_id}")
            state.increment_version()
            _history.save(state)
            return {"status": "approved", "plan_id": req.plan_id, "version": state.version}
    raise HTTPException(404, f"Plan {req.plan_id} not found")


@app.post("/reject")
def reject():
    global _state
    state = _get_state()
    state.approved_plan = None
    state.log_action("Dispatcher", "Rejected recommended plan")
    state.increment_version()
    _history.save(state)
    return {"status": "rejected", "version": state.version}


@app.post("/events/breakdown")
def event_breakdown(req: BreakdownRequest):
    global _state
    state = _get_state()
    _state = apply_unit_breakdown(state, _history, req.unit_id)
    return {"status": "breakdown_applied", "unit_id": req.unit_id, "version": _state.version}


@app.post("/events/road-block")
def event_road_block(req: RoadBlockRequest):
    global _state
    state = _get_state()
    _state = apply_road_block(state, _history, req.road_id)
    return {"status": "road_blocked", "road_id": req.road_id, "version": _state.version}


@app.post("/events/new-incident")
def event_new_incident(incident: Incident):
    global _state
    state = _get_state()
    _state = apply_new_incident(state, _history, incident)
    return {"status": "incident_added", "incident_id": incident.id, "version": _state.version}


@app.post("/replan")
def replan():
    global _state
    state = _get_state()
    prev = state.approved_plan or state.recommended_plan
    state.approved_plan = None
    state.recommended_plan = None
    state = generate_candidate_plans(state)
    state = compare_and_select(state)
    for p in state.candidate_plans:
        if p.validation and p.validation.valid and len(p.assignments) > 0:
            res = evaluate_plan_resilience(p, state)
            state.resilience_results[p.id] = res
            if p.metrics:
                p.metrics.resilience_score = res.resilience_score
                p.metrics.fragility_index = res.fragility_index
    if prev and state.recommended_plan:
        from backend.diff import compute_plan_diff
        diff = compute_plan_diff(prev, state.recommended_plan, state, "Manual replan")
        state.plan_diffs.append(diff)
    _state = state
    _history.save(state)
    return {
        "version": state.version,
        "recommended": state.recommended_plan.model_dump() if state.recommended_plan else None,
    }
