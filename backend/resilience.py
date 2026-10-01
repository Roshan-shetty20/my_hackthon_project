import backend.models
"""
Crisis Command — Counterfactual Resilience Engine

The primary differentiator of Crisis Command.

For every feasible candidate plan, this engine simulates controlled
failure scenarios and measures how each failure degrades the plan.

Failure types tested:
  1. Unit failure   — each assigned unit becomes BROKEN_DOWN
  2. Road blockage  — each unblocked road becomes blocked

Formulas:
  fragility_index  = (degrading_scenarios / total_scenarios) × 100
  resilience_score = 100 − fragility_index

A scenario is "degrading" if it causes:
  - a critical/high incident to become uncovered, OR
  - the plan to become invalid (constraint violation)

Single Point of Failure:
  A unit whose failure causes a CRITICAL incident to become uncovered
  with no alternative unit available for recovery.

All simulations operate on deep copies — the real CrisisState is
NEVER mutated during counterfactual analysis.
"""

from typing import List

from backend.models import (
    FailureImpact,
    FailureScenario,
    Plan,
    ResilienceResult,
    UnitStatus,
    UrgencyLevel,
)
from backend.constraints import validate_plan
from backend.route import calculate_eta
from backend.state import CrisisState


# ---------------------------------------------------------------------------
# Scenario generation
# ---------------------------------------------------------------------------

def generate_failure_scenarios(plan: Plan, state: CrisisState) -> List[FailureScenario]:
    """Generate all single-failure scenarios relevant to this plan."""
    scenarios: List[FailureScenario] = []

    # Unit failures — one scenario per assigned unit
    assigned_unit_ids = {a.unit_id for a in plan.assignments}
    for uid in assigned_unit_ids:
        unit = state.get_unit(uid)
        label = f"{uid} ({unit.type.value})" if unit else uid
        scenarios.append(
            FailureScenario(
                scenario_id=f"FAIL_{uid}",
                type="unit_failure",
                target_id=uid,
                description=f"{label} breaks down",
            )
        )

    # Road blockages — one scenario per currently unblocked road
    for road in state.road_conditions:
        if not road.blocked:
            scenarios.append(
                FailureScenario(
                    scenario_id=f"BLOCK_{road.id}",
                    type="road_block",
                    target_id=road.id,
                    description=f"{road.name} becomes blocked",
                )
            )

    
    # New incident simulation
    scenarios.append(
        FailureScenario(
            scenario_id="SIM_NEW_CRITICAL_INC",
            type="new_incident",
            target_id="INC-SIM-999",
            description="A new CRITICAL incident arrives",
        )
    )

    # Severity increase simulation
    for a in plan.assignments:
        inc = state.get_incident(a.incident_id)
        if inc and not inc.status == "RESOLVED":
            scenarios.append(
                FailureScenario(
                    scenario_id=f"SIM_ESCALATE_{a.incident_id}",
                    type="severity_increase",
                    target_id=a.incident_id,
                    description=f"{a.incident_id} severity increases",
                )
            )

    return scenarios


# ---------------------------------------------------------------------------
# Failure simulation
# ---------------------------------------------------------------------------

def simulate_failure(
    scenario: FailureScenario,
    plan: Plan,
    state: CrisisState,
) -> FailureImpact:
    """Simulate a single failure scenario on a *copy* of the state.

    Returns the measured impact WITHOUT modifying the real state.
    """
    sim_state = state.snapshot()  # deep copy

    if scenario.type == "unit_failure":
        unit = sim_state.get_unit(scenario.target_id)
        if unit:
            unit.status = UnitStatus.BROKEN_DOWN

    
    elif scenario.type == "new_incident":
        from backend.models import Incident, UnitType
        from backend.severity import assess_incident
        new_inc = Incident(
            id=scenario.target_id, type="MEDICAL", location="Simulation",
            latitude=0.0, longitude=0.0,
            people_affected=25, life_threat=True
        )
        assess_incident(new_inc)
        sim_state.incidents.append(new_inc)

    elif scenario.type == "severity_increase":
        inc = sim_state.get_incident(scenario.target_id)
        if inc:
            inc.severity = min(10, (inc.severity or 1) + 2)
            if inc.severity >= 9:
                
                inc.urgency = backend.models.UrgencyLevel.CRITICAL

    elif scenario.type == "road_block":
        for road in sim_state.road_conditions:
            if road.id == scenario.target_id:
                road.blocked = True
                road.delay_minutes = 5.0
                road.reason = "Simulated blockage"
                break

    # Re-validate the plan against the degraded state
    sim_plan = plan.model_copy(deep=True)
    validation = validate_plan(sim_plan, sim_state)

    # Determine affected incidents
    assigned_units_map = {}  # unit_id -> incident_id
    for a in plan.assignments:
        assigned_units_map[a.unit_id] = a.incident_id

    affected: List[str] = []
    uncovered: List[str] = []

    if scenario.type == "unit_failure":
        # The incident that lost this unit
        affected_iid = assigned_units_map.get(scenario.target_id)
        if affected_iid:
            affected.append(affected_iid)
            # Can any other available unit of the same type fill in?
            failed_unit = state.get_unit(scenario.target_id)
            if failed_unit:
                assigned_ids = {a.unit_id for a in plan.assignments}
                alternatives = [
                    u for u in sim_state.units
                    if u.status == UnitStatus.AVAILABLE
                    and u.type == failed_unit.type
                    and u.id not in assigned_ids
                ]
                if not alternatives:
                    uncovered.append(affected_iid)

    # ETA increase for road blocks
    eta_increase = 0.0
    if scenario.type == "road_block":
        for a in plan.assignments:
            unit = sim_state.get_unit(a.unit_id)
            inc = sim_state.get_incident(a.incident_id)
            if unit and inc:
                new_eta = calculate_eta(
                    unit.latitude, unit.longitude,
                    inc.latitude, inc.longitude,
                    sim_state.road_conditions,
                )
                eta_increase += max(0, new_eta - a.eta_minutes)

    # Reserve remaining
    available_after = sum(
        1 for u in sim_state.units if u.status == UnitStatus.AVAILABLE
    )
    assigned_count = len({a.unit_id for a in plan.assignments})
    if scenario.type == "unit_failure":
        assigned_count -= 1  # broken unit is no longer assigned
    reserve = available_after - assigned_count

    # Determine severity of impact
    severity_impact = "NONE"
    for iid in uncovered:
        inc = state.get_incident(iid)
        if inc:
            if inc.urgency in (backend.models.UrgencyLevel.CRITICAL, backend.models.UrgencyLevel.HIGH):
                severity_impact = "CRITICAL"
                break
            elif inc.urgency == backend.models.UrgencyLevel.MEDIUM:
                severity_impact = "MEDIUM"

    if not validation.valid and severity_impact == "NONE":
        severity_impact = "LOW"

    return FailureImpact(
        scenario=scenario,
        plan_still_valid=validation.valid and len(uncovered) == 0,
        affected_incidents=affected,
        uncovered_incidents=uncovered,
        eta_increase_minutes=round(eta_increase, 1),
        reserve_remaining=max(0, reserve),
        recovery_possible=len(uncovered) == 0,
        severity_impact=severity_impact,
    )


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def evaluate_plan_resilience(plan: Plan, state: CrisisState) -> ResilienceResult:
    """Run all failure scenarios and compute resilience metrics."""
    scenarios = generate_failure_scenarios(plan, state)
    if not scenarios:
        return ResilienceResult(
            plan_id=plan.id,
            resilience_score=100.0,
            fragility_index=0.0,
            scenarios_tested=0,
        )

    impacts: List[FailureImpact] = []
    degrading_count = 0
    worst_impact: FailureImpact | None = None
    worst_severity_rank = -1
    spof: List[str] = []

    severity_rank = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

    for scenario in scenarios:
        impact = simulate_failure(scenario, plan, state)
        impacts.append(impact)

        # Is this scenario degrading?
        if not impact.plan_still_valid or impact.severity_impact in ("MEDIUM", "HIGH", "CRITICAL"):
            degrading_count += 1

        # Track worst case
        rank = severity_rank.get(impact.severity_impact, 0)
        if rank > worst_severity_rank or (
            rank == worst_severity_rank
            and worst_impact
            and impact.eta_increase_minutes > worst_impact.eta_increase_minutes
        ):
            worst_severity_rank = rank
            worst_impact = impact

        # Single point of failure detection
        if scenario.type == "unit_failure" and impact.severity_impact == "CRITICAL":
            spof.append(scenario.target_id)

    fragility = round((degrading_count / len(scenarios)) * 100, 1)
    resilience = round(100 - fragility, 1)

    return ResilienceResult(
        plan_id=plan.id,
        resilience_score=resilience,
        fragility_index=fragility,
        worst_case_unit=worst_impact.scenario.target_id if worst_impact else None,
        worst_case_impact=worst_impact,
        single_points_of_failure=spof,
        scenarios_tested=len(scenarios),
        scenario_results=impacts,
    )


def generate_resilience_summary(result: ResilienceResult) -> str:
    """Generate a human-readable resilience summary."""
    lines = [
        f"Resilience Score: {result.resilience_score}/100",
        f"Fragility Index: {result.fragility_index}%",
        f"Scenarios Tested: {result.scenarios_tested}",
    ]
    if result.single_points_of_failure:
        lines.append(f"Single Points of Failure: {', '.join(result.single_points_of_failure)}")
    if result.worst_case_impact:
        wc = result.worst_case_impact
        lines.append(f"Worst Case: {wc.scenario.description}")
        if wc.uncovered_incidents:
            lines.append(f"  → Uncovered: {', '.join(wc.uncovered_incidents)}")
        if wc.eta_increase_minutes > 0:
            lines.append(f"  → ETA increase: +{wc.eta_increase_minutes} min")
    return "\n".join(lines)
