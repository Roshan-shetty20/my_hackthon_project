"""
Crisis Command — Session-Isolated FastAPI Server

Each browser session gets its own CrisisState.
Multiple judges/users cannot share state.

Session ID is a UUID generated on POST /session.
All operations are scoped to /session/{session_id}/...

The existing deterministic engine is unchanged.
This module only adds the HTTP transport layer.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.models import Incident, Unit, RoadCondition
from backend.state import CrisisState, StateHistory
from backend.severity import assess_incident
from backend.planner import generate_candidate_plans
from backend.comparator import (
    compare_and_select,
    generate_why_explanation,
    calculate_decision_confidence,
    calculate_decision_debts,
)
from backend.resilience import evaluate_plan_resilience
from backend.replanner import apply_unit_breakdown, apply_road_block, apply_new_incident
from backend.diff import compute_plan_diff
from backend.agents.command_agent import CommandPlanningAgent

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Crisis Command API",
    version="2.0.0",
    description="Session-isolated Crisis Command REST API for judge-facing demo.",
)

ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001,https://crisis-command.vercel.app"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Tighten for production if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory session store  {session_id -> {"state": CrisisState, "history": StateHistory}}
# Sessions expire only on server restart (fine for hackathon).
# ---------------------------------------------------------------------------

_sessions: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _data_path(filename: str) -> Path:
    return Path(__file__).parent.parent / "data" / filename


def _load_json(filename: str):
    with open(_data_path(filename), encoding="utf-8") as f:
        return json.load(f)


def _strip_comment(d: dict) -> dict:
    return {k: v for k, v in d.items() if k != "_comment"}


def _init_state() -> CrisisState:
    """Load initial data and build a fresh CrisisState."""
    incidents = [Incident(**_strip_comment(d)) for d in _load_json("incidents.json")]
    units = [Unit(**_strip_comment(d)) for d in _load_json("units.json")]
    roads = [RoadCondition(**_strip_comment(d)) for d in _load_json("roads.json")]
    for inc in incidents:
        assess_incident(inc)
    state = CrisisState(incidents=incidents, units=units, road_conditions=roads)
    state.log_action("System", "Crisis initialised", f"{len(incidents)} incidents, {len(units)} units loaded")
    return state


def _get_session(session_id: str) -> Dict[str, Any]:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found. POST /session first.")
    return _sessions[session_id]


def _run_plans(state: CrisisState) -> CrisisState:
    state.approved_plan = None
    """Generate → validate → compare → resilience → confidence → debt."""
    state = generate_candidate_plans(state)
    state = compare_and_select(state)
    for p in state.candidate_plans:
        if p.validation and p.validation.valid and len(p.assignments) > 0:
            res = evaluate_plan_resilience(p, state)
            state.resilience_results[p.id] = res
            if p.metrics:
                p.metrics.resilience_score = res.resilience_score
                p.metrics.fragility_index = res.fragility_index
            from backend.comparator import evaluate_human_attention
            evaluate_human_attention(p, state, res)
    compare_and_select(state)
    state.decision_confidence = calculate_decision_confidence(state)
    state.decision_debts = calculate_decision_debts(state)
    return state


def _get_explanation(state: CrisisState) -> dict:
    plan = state.recommended_plan
    if plan and plan.ai_explanation:
        ai = plan.ai_explanation
        return {
            "source": "gemini",
            "why": ai.get("why_this_plan", ""),
            "tradeoff": ai.get("trade_off", ""),
            "risk": ai.get("risk", ""),
            "what_changed": ai.get("what_changed", ""),
            "summary": ai.get("summary", ""),
        }
    det = generate_why_explanation(state)
    return {
        "source": "deterministic_fallback",
        "why": det.get("why", ""),
        "tradeoff": det.get("tradeoff", ""),
        "risk": "",
        "what_changed": "",
        "summary": "",
        "why_not": det.get("why_not", {}),
    }


def _derive_stage(state: CrisisState) -> str:
    """Return the current pipeline stage name based on actual state."""
    if not state.candidate_plans:
        return "RECEIVE"  # Incidents loaded, plans not generated
    has_resilience = bool(state.resilience_results)
    if not has_resilience:
        return "ALLOCATE"
    if not state.recommended_plan:
        return "COMPARE"
    if state.plan_diffs and not state.approved_plan:
        return "REPLAN_REVIEW"
    if not state.approved_plan:
        return "RECOMMEND"
    if state.plan_diffs:
        return "POST_DISRUPTION"
    return "ACTIVE"


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class ApproveBody(BaseModel):
    plan_id: str


class BreakdownBody(BaseModel):
    unit_id: str


class RoadBlockBody(BaseModel):
    road_id: str


class NewIncidentBody(BaseModel):
    id: str
    type: str
    location: str
    latitude: float
    longitude: float
    people_affected: int = 0
    people_trapped: int = 0
    vulnerable_people: int = 0
    life_threat: bool = False
    time_critical: bool = False
    spreading_hazard: bool = False
    required_units: Dict[str, int] = {}


class BatchDisruptionEvent(BaseModel):
    event_type: str
    payload: dict

class BatchDisruptionsBody(BaseModel):
    events: list[BatchDisruptionEvent]



# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    gemini_connected = bool(os.environ.get("GEMINI_API_KEY"))
    ors_connected = bool(os.environ.get("ORS_API_KEY"))
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "sessions_active": len(_sessions),
        "integrations": {
            "gemini": "connected" if gemini_connected else "degraded",
            "openrouteservice": "connected" if ors_connected else "degraded",
            "open_meteo": "available",
            "dijkstra": "active",
        },
    }


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

@app.post("/session")
def create_session():
    """Create a new isolated session. Returns session_id."""
    session_id = str(uuid.uuid4())
    state = _init_state()
    history = StateHistory()
    history.save(state)
    _sessions[session_id] = {"state": state, "history": history}
    return {
        "session_id": session_id,
        "version": state.version,
        "stage": _derive_stage(state),
        "message": "Fresh crisis scenario loaded. STATE v1.",
    }


@app.post("/session/{session_id}/reset")
def reset_session(session_id: str):
    """Reset session to initial state (v1)."""
    sess = _get_session(session_id)
    state = _init_state()
    history = StateHistory()
    history.save(state)
    sess["state"] = state
    sess["history"] = history
    return {
        "session_id": session_id,
        "version": state.version,
        "stage": _derive_stage(state),
        "message": "Reset to STATE v1.",
    }


# ---------------------------------------------------------------------------
# State read
# ---------------------------------------------------------------------------


def _build_missions(state):
    missions = {}
    for m_id, m in state.active_missions.items():
        m_dict = m.model_dump()
        r = state.get_mission_route(m_id)
        if r:
            m_dict["route"] = r.model_dump()
        missions[m_id] = m_dict
    return missions

@app.get("/session/{session_id}/state")
def get_state(session_id: str):
    sess = _get_session(session_id)
    state: CrisisState = sess["state"]
    rec = state.recommended_plan
    return {
        "version": state.version,
        "stage": _derive_stage(state),
        "incidents": [i.model_dump() for i in state.incidents],
        "units": [u.model_dump() for u in state.units],
        "road_conditions": [r.model_dump() for r in state.road_conditions],
        "candidate_plans": [p.model_dump() for p in state.candidate_plans],
        "recommended_plan": rec.model_dump() if rec else None,
        "approved_plan": state.approved_plan.model_dump() if state.approved_plan else None,
        "resilience_results": {k: v.model_dump() for k, v in state.resilience_results.items()},
        "plan_diffs": [d.model_dump() for d in state.plan_diffs],
        "action_log": [e.model_dump() for e in state.action_log],
        "system_events": [e.model_dump() for e in state.system_events],
        "decision_confidence": state.decision_confidence.model_dump() if state.decision_confidence else None,
        "decision_debts": [d.model_dump() for d in state.decision_debts],
        "latest_impact_analysis": state.latest_impact_analysis,
                "active_missions": _build_missions(state),
    }


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

@app.post("/session/{session_id}/assess")
def assess(session_id: str):
    """Re-run incident assessment (idempotent)."""
    sess = _get_session(session_id)
    state: CrisisState = sess["state"]
    for inc in state.incidents:
        assess_incident(inc)
    state.log_action("IncidentAssessment", "Assessed all incidents", f"{len(state.incidents)} incidents")
    state.increment_version()
    return {"version": state.version, "stage": _derive_stage(state), "incidents_assessed": len(state.incidents)}


@app.post("/session/{session_id}/replan")
def replan(session_id: str):
    """Commander manually triggers a replan based on current state."""
    sess = _get_session(session_id)
    state: CrisisState = sess["state"]
    history: StateHistory = sess["history"]
    previous_plan = state.approved_plan or state.recommended_plan
    
    # Store old metrics for diff comparison
    old_version = state.version
    
    # Clear active plans and trigger internal replan
    state.approved_plan = None
    state.recommended_plan = None
    
    from backend.replanner import _replan
    state = _replan(state, history, previous_plan, trigger="Commander triggered manual replan")
    state.decision_confidence = calculate_decision_confidence(state)
    state.decision_debts = calculate_decision_debts(state)
    
    sess["state"] = state
    history.save(state)
    
    # Refresh AI brief if needed
    try:
        agent = CommandPlanningAgent()
        state = agent.select_plan(state)
        sess["state"] = state
    except Exception:
        pass
        
    return {
        "status": "replanned",
        "version": state.version,
        "stage": _derive_stage(state),
        "plans": [p.model_dump() for p in state.candidate_plans],
        "recommended_plan": state.recommended_plan.model_dump() if state.recommended_plan else None,
        "plan_diffs": [d.model_dump() for d in state.plan_diffs],
        "changed": old_version != state.version
    }


@app.post("/session/{session_id}/generate-plans")
def generate_plans(session_id: str):
    """Generate + validate + resilience + compare all plans."""
    sess = _get_session(session_id)
    state: CrisisState = sess["state"]
    state = _run_plans(state)
    sess["state"] = state
    sess["history"].save(state)

    # Try Gemini explanation
    try:
        agent = CommandPlanningAgent()
        state = agent.select_plan(state)
        sess["state"] = state
    except Exception:
        pass  # Gemini failure is non-fatal

    return {
        "version": state.version,
        "stage": _derive_stage(state),
        "plans": [p.model_dump() for p in state.candidate_plans],
        "recommended_plan": state.recommended_plan.model_dump() if state.recommended_plan else None,
        "resilience_results": {k: v.model_dump() for k, v in state.resilience_results.items()},
        "decision_confidence": state.decision_confidence.model_dump() if state.decision_confidence else None,
    }


@app.get("/session/{session_id}/explanation")
def get_explanation(session_id: str):
    """Return Gemini or deterministic-fallback explanation for current recommendation."""
    sess = _get_session(session_id)
    state: CrisisState = sess["state"]
    if not state.recommended_plan:
        raise HTTPException(400, "No recommended plan yet. Run generate-plans first.")
    gemini_available = bool(os.environ.get("GEMINI_API_KEY"))
    expl = _get_explanation(state)
    return {
        "gemini_status": "connected" if (gemini_available and expl["source"] == "gemini") else "degraded",
        "explanation_source": expl["source"],
        **expl,
        "boundary_note": (
            "Gemini interprets verified system evidence. "
            "It does not allocate resources or make operational decisions."
        ),
    }


@app.post("/session/{session_id}/approve")
def approve_plan(session_id: str, body: ApproveBody):
    """Human commander approves the specified plan."""
    sess = _get_session(session_id)
    state: CrisisState = sess["state"]
    target = None
    for p in state.candidate_plans:
        if p.id == body.plan_id:
            target = p
            break
    if not target:
        raise HTTPException(404, f"Plan {body.plan_id} not found.")
    if target.validation and not target.validation.valid:
        raise HTTPException(400, f"Plan {body.plan_id} is invalid and cannot be approved.")

    state.approved_plan = target
    from backend.route import calculate_routes
    for a in target.assignments:
        u = state.get_unit(a.unit_id)
        inc = state.get_incident(a.incident_id)
        if u and inc:
            r = calculate_routes(u.latitude, u.longitude, inc.latitude, inc.longitude, state.road_conditions)
            if r:
                state.dispatch_unit(u.id, inc.id, r[0])
    state.log_action("Commander", f"Approved {target.strategy_name}", f"Plan ID: {body.plan_id}")
    state.increment_version()
    sess["history"].save(state)
    return {
        "status": "approved",
        "plan_id": body.plan_id,
        "strategy": target.strategy_name,
        "version": state.version,
    }


@app.post("/session/{session_id}/reject")
def reject_plan(session_id: str):
    """Commander rejects the current approved plan."""
    sess = _get_session(session_id)
    state: CrisisState = sess["state"]
    if state.approved_plan:
        name = state.approved_plan.strategy_name
        state.approved_plan = None
        state.log_action("Commander", f"Rejected {name}")
        state.increment_version()
    return {"status": "rejected", "version": state.version}


# ---------------------------------------------------------------------------
# Disruption events
# ---------------------------------------------------------------------------

@app.post("/session/{session_id}/events/breakdown")
def event_breakdown(session_id: str, body: BreakdownBody):
    sess = _get_session(session_id)
    state: CrisisState = sess["state"]
    history: StateHistory = sess["history"]
    state = apply_unit_breakdown(state, history, body.unit_id)
    state.decision_confidence = calculate_decision_confidence(state)
    state.decision_debts = calculate_decision_debts(state)
    sess["state"] = state
    return {
        "status": "breakdown_applied",
        "unit_id": body.unit_id,
        "version": state.version,
        "stage": _derive_stage(state),
        "impact": state.latest_impact_analysis,
    }


@app.post("/session/{session_id}/events/road-block")
def event_road_block(session_id: str, body: RoadBlockBody):
    sess = _get_session(session_id)
    state: CrisisState = sess["state"]
    history: StateHistory = sess["history"]
    state = apply_road_block(state, history, body.road_id)
    state.decision_confidence = calculate_decision_confidence(state)
    state.decision_debts = calculate_decision_debts(state)
    sess["state"] = state
    return {
        "status": "road_blocked",
        "road_id": body.road_id,
        "version": state.version,
        "stage": _derive_stage(state),
        "impact": state.latest_impact_analysis,
    }


@app.post("/session/{session_id}/events/new-incident")
def event_new_incident(session_id: str, body: NewIncidentBody):
    sess = _get_session(session_id)
    state: CrisisState = sess["state"]
    history: StateHistory = sess["history"]

    from backend.models import UnitType
    required_units = {}
    for k, v in body.required_units.items():
        try:
            required_units[UnitType(k)] = v
        except ValueError:
            pass

    inc = Incident(
        id=body.id,
        type=body.type,
        location=body.location,
        latitude=body.latitude,
        longitude=body.longitude,
        people_affected=body.people_affected,
        people_trapped=body.people_trapped,
        vulnerable_people=body.vulnerable_people,
        life_threat=body.life_threat,
        time_critical=body.time_critical,
        spreading_hazard=body.spreading_hazard,
        required_units=required_units,
    )
    state = apply_new_incident(state, history, inc)
    state.decision_confidence = calculate_decision_confidence(state)
    state.decision_debts = calculate_decision_debts(state)
    sess["state"] = state
    return {
        "status": "incident_added",
        "incident_id": inc.id,
        "version": state.version,
        "stage": _derive_stage(state),
        "impact": state.latest_impact_analysis,
    }


# ---------------------------------------------------------------------------
# Golden scenario — step through surat_monsoon.json
# ---------------------------------------------------------------------------



@app.post("/session/{session_id}/tick")
def tick_time(session_id: str):
    """Advances time, moving ambulances along their routes."""
    sess = _get_session(session_id)
    state: CrisisState = sess["state"]
    
    state.advance_missions(step_percent=20.0)
    
    return get_state(session_id)

@app.post("/session/{session_id}/simulate-step")
def simulate_step(session_id: str):
    """Advance the deterministic Surat Monsoon simulation by one event batch."""
    sess = _get_session(session_id)
    if "simulator" not in sess:
        from backend.simulator import DeterministicSimulator
        sess["simulator"] = DeterministicSimulator()
    sim = sess["simulator"]
    if not sim.has_next():
        return {"status": "complete", "message": "All simulation events exhausted."}

    batch = sim.next_event_batch()
    state: CrisisState = sess["state"]
    history: StateHistory = sess["history"]

    from backend.replanner import apply_events_batch
    state = apply_events_batch(state, history, batch)

    state.decision_confidence = calculate_decision_confidence(state)
    state.decision_debts = calculate_decision_debts(state)
    sess["state"] = state

    return {
        "events": [e.model_dump() for e in batch],
        "version": state.version,
        "stage": _derive_stage(state),
        "events_remaining": sim.events_remaining(),
        "impact": state.latest_impact_analysis,
    }

# ---------------------------------------------------------------------------
@app.get("/session/{session_id}/timeline")
def get_timeline(session_id: str):
    sess = _get_session(session_id)
    state: CrisisState = sess["state"]
    return {
        "action_log": [e.model_dump() for e in state.action_log],
        "system_events": [e.model_dump() for e in state.system_events],
        "version": state.version,
    }


@app.get("/session/{session_id}/plan-diff")
def get_plan_diff(session_id: str):
    sess = _get_session(session_id)
    state: CrisisState = sess["state"]
    return {
        "plan_diffs": [d.model_dump() for d in state.plan_diffs],
        "count": len(state.plan_diffs),
    }


@app.get("/session/{session_id}/resilience/{plan_id}")
def get_resilience(session_id: str, plan_id: str):
    sess = _get_session(session_id)
    state: CrisisState = sess["state"]
    if plan_id not in state.resilience_results:
        raise HTTPException(404, f"No resilience result for plan {plan_id}.")
    return state.resilience_results[plan_id].model_dump()


@app.get("/session/{session_id}/impact")
def get_impact(session_id: str):
    sess = _get_session(session_id)
    state: CrisisState = sess["state"]
    return {"impact": state.latest_impact_analysis, "version": state.version}


@app.post("/session/{session_id}/events")
def apply_batch_disruptions(session_id: str, body: BatchDisruptionsBody):
    """Apply multiple disruption events atomically — ONE global impact analysis + ONE replan."""
    sess = _get_session(session_id)
    state: CrisisState = sess["state"]
    history: StateHistory = sess["history"]
    
    if not body.events:
        raise HTTPException(400, "events list must not be empty")
    
    from backend.replanner import apply_events_batch
    
    # Pass BatchDisruptionEvent objects directly - they have .event_type and .payload
    state = apply_events_batch(state, history, body.events)
    state.decision_confidence = calculate_decision_confidence(state)
    state.decision_debts = calculate_decision_debts(state)
    sess["state"] = state
    
    return {
        "status": "events_applied",
        "events_applied": len(body.events),
        "version": state.version,
        "stage": _derive_stage(state),
        "impact": state.latest_impact_analysis,
    }


# ---------------------------------------------------------------------------
# Legacy single-instance endpoints (kept for backward compat with tests)
# ---------------------------------------------------------------------------

_legacy_state: Optional[CrisisState] = None
_legacy_history = StateHistory()


@app.get("/health/legacy")
def health_legacy():
    return {"status": "ok"}


@app.post("/initialize")
def legacy_initialize():
    global _legacy_state, _legacy_history
    _legacy_history = StateHistory()
    _legacy_state = _init_state()
    _legacy_history.save(_legacy_state)
    return {"status": "initialised", "version": _legacy_state.version}


@app.get("/state")
def legacy_state():
    if not _legacy_state:
        raise HTTPException(400, "Not initialised.")
    return _legacy_state.model_dump()


@app.post("/plan")
def legacy_plan():
    global _legacy_state
    if not _legacy_state:
        raise HTTPException(400, "Not initialised.")
    _legacy_state = _run_plans(_legacy_state)
    _legacy_history.save(_legacy_state)
    return {
        "version": _legacy_state.version,
        "plans": [p.model_dump() for p in _legacy_state.candidate_plans],
        "recommended": _legacy_state.recommended_plan.model_dump() if _legacy_state.recommended_plan else None,
    }


@app.get("/incidents")
def legacy_incidents():
    if not _legacy_state:
        raise HTTPException(400, "Not initialised.")
    return [i.model_dump() for i in _legacy_state.incidents]


@app.get("/units")
def legacy_units():
    if not _legacy_state:
        raise HTTPException(400, "Not initialised.")
    return [u.model_dump() for u in _legacy_state.units]


@app.get("/plans")
def legacy_plans():
    if not _legacy_state:
        raise HTTPException(400, "Not initialised.")
    return [p.model_dump() for p in _legacy_state.candidate_plans]


@app.get("/action-log")
def legacy_action_log():
    if not _legacy_state:
        raise HTTPException(400, "Not initialised.")
    return [e.model_dump() for e in _legacy_state.action_log]


class _LegacyApprove(BaseModel):
    plan_id: str

class _LegacyBreakdown(BaseModel):
    unit_id: str

class _LegacyRoadBlock(BaseModel):
    road_id: str


@app.post("/approve")
def legacy_approve(req: _LegacyApprove):
    global _legacy_state
    if not _legacy_state:
        raise HTTPException(400, "Not initialised.")
    for p in _legacy_state.candidate_plans:
        if p.id == req.plan_id:
            _legacy_state.approved_plan = p
            _legacy_state.log_action("Commander", f"Approved {p.strategy_name}")
            _legacy_state.increment_version()
            return {"status": "approved", "version": _legacy_state.version}
    raise HTTPException(404, f"Plan {req.plan_id} not found.")


@app.post("/events/breakdown")
def legacy_breakdown(req: _LegacyBreakdown):
    global _legacy_state
    if not _legacy_state:
        raise HTTPException(400, "Not initialised.")
    _legacy_state = apply_unit_breakdown(_legacy_state, _legacy_history, req.unit_id)
    return {"status": "breakdown_applied", "version": _legacy_state.version}


@app.post("/events/road-block")
def legacy_road_block(req: _LegacyRoadBlock):
    global _legacy_state
    if not _legacy_state:
        raise HTTPException(400, "Not initialised.")
    _legacy_state = apply_road_block(_legacy_state, _legacy_history, req.road_id)
    return {"status": "road_blocked", "version": _legacy_state.version}


@app.post("/events/new-incident")
def legacy_new_incident(incident: Incident):
    global _legacy_state
    if not _legacy_state:
        raise HTTPException(400, "Not initialised.")
    _legacy_state = apply_new_incident(_legacy_state, _legacy_history, incident)
    return {"status": "incident_added", "version": _legacy_state.version}
