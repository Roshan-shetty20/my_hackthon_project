"""
Crisis Command — Replanner

Handles dynamic replanning when the situation changes (unit breakdown,
road blockage, new incident).  Preserves state history and generates
plan diffs.
"""

from datetime import datetime

from backend.models import Incident, SystemEvent, UnitStatus
from backend.planner import generate_candidate_plans
from backend.comparator import compare_and_select
from backend.resilience import evaluate_plan_resilience
from backend.diff import compute_plan_diff
from backend.severity import assess_incident
from backend.state import CrisisState, StateHistory


def apply_unit_breakdown(
    state: CrisisState,
    history: StateHistory,
    unit_id: str,
) -> CrisisState:
    """Mark a unit as BROKEN_DOWN and trigger replanning."""
    from backend.impact import analyze_impact
    impact = analyze_impact(state, trigger="Unit Breakdown", event_type="unit_failure", payload={"unit_id": unit_id})
    state.latest_impact_analysis = impact.model_dump()
    history.save(state)

    unit = state.get_unit(unit_id)
    if not unit:
        state.log_action("System", f"Breakdown failed: unit {unit_id} not found")
        return state

    old_status = unit.status.value
    unit.status = UnitStatus.BROKEN_DOWN
    unit.current_incident = None

    state.system_events.append(
        SystemEvent(
            id=f"EVT-BRK-{unit_id}",
            type="breakdown",
            target_id=unit_id,
            description=f"{unit_id} changed from {old_status} to BROKEN_DOWN",
            timestamp=datetime.now().isoformat(timespec="seconds"),
        )
    )
    state.log_action("System", f"Unit {unit_id} breakdown", f"{old_status} → BROKEN_DOWN")
    state.increment_version()

    # Invalidate current plans
    previous_plan = state.approved_plan or state.recommended_plan
    state.approved_plan = None
    state.recommended_plan = None

    # Replan
    state = _replan(state, history, previous_plan, trigger=f"{unit_id} breakdown")
    return state


def apply_road_block(
    state: CrisisState,
    history: StateHistory,
    road_id: str,
) -> CrisisState:
    """Block a road and trigger replanning."""
    from backend.impact import analyze_impact
    impact = analyze_impact(state, trigger="Road Block", event_type="road_block", payload={"road_id": road_id})
    state.latest_impact_analysis = impact.model_dump()
    history.save(state)

    road = None
    for r in state.road_conditions:
        if r.id == road_id:
            road = r
            break

    if not road:
        state.log_action("System", f"Road block failed: road {road_id} not found")
        return state

    road.blocked = True
    road.delay_minutes = 5.0
    road.reason = "Blocked by debris"

    state.system_events.append(
        SystemEvent(
            id=f"EVT-RB-{road_id}",
            type="road_block",
            target_id=road_id,
            description=f"{road.name} blocked",
            timestamp=datetime.now().isoformat(timespec="seconds"),
        )
    )
    state.log_action("System", f"Road {road.name} blocked", road_id)
    
    # Check if this road block interrupts any active missions
    state.handle_road_block(road_id)
    
    state.increment_version()

    previous_plan = state.approved_plan or state.recommended_plan
    state.approved_plan = None
    state.recommended_plan = None

    state = _replan(state, history, previous_plan, trigger=f"{road.name} road block")
    return state


def apply_new_incident(
    state: CrisisState,
    history: StateHistory,
    incident: Incident,
) -> CrisisState:
    """Add a new incident and trigger replanning."""
    from backend.impact import analyze_impact
    payload = {
        "incident_id": incident.id,
        "required_units": incident.required_units
    }
    impact = analyze_impact(state, trigger="New Incident", event_type="new_incident", payload=payload)
    state.latest_impact_analysis = impact.model_dump()
    history.save(state)

    assess_incident(incident)
    state.incidents.append(incident)

    state.system_events.append(
        SystemEvent(
            id=f"EVT-NEW-{incident.id}",
            type="new_incident",
            target_id=incident.id,
            description=f"New {incident.type} at {incident.location}",
            timestamp=datetime.now().isoformat(timespec="seconds"),
        )
    )
    state.log_action("System", f"New incident {incident.id}", incident.type)
    state.increment_version()

    previous_plan = state.approved_plan or state.recommended_plan
    state.approved_plan = None
    state.recommended_plan = None

    state = _replan(state, history, previous_plan, trigger=f"New incident {incident.id}")
    return state


def _replan(
    state: CrisisState,
    history: StateHistory,
    previous_plan,
    trigger: str,
) -> CrisisState:
    """Internal: generate new plans, validate, compare, compute resilience + diff."""
    state = generate_candidate_plans(state)
    state = compare_and_select(state)

    # Resilience analysis on valid plans
    for plan in state.candidate_plans:
        if plan.validation and plan.validation.valid:
            result = evaluate_plan_resilience(plan, state)
            state.resilience_results[plan.id] = result
            if plan.metrics:
                plan.metrics.resilience_score = result.resilience_score
                plan.metrics.fragility_index = result.fragility_index
            from backend.comparator import evaluate_human_attention
            evaluate_human_attention(plan, state, result)

    # Plan diff
    if previous_plan and state.recommended_plan:
        diff = compute_plan_diff(previous_plan, state.recommended_plan, state, trigger)
        state.plan_diffs.append(diff)

    state.log_action("Replanner", f"Replanning complete", trigger)
    return state
