"""
Crisis Command — Plan Comparator

Calculates runtime metrics and a transparent combined score for each
candidate plan so the system can recommend one.

Combined decision score formula (documented here):

  score = (critical_covered  × 40)
        + (high_covered      × 25)
        + (medium_covered    × 15)
        + (low_covered       ×  5)
        − (uncovered_critical × 50)
        − (uncovered_high     × 30)
        − (uncovered_other    × 10)
        + (reserve_units     ×  8)
        + (resilience_score  ×  0.5)
        − (average_eta       ×  2)
        − (max_eta           ×  1)
"""

from typing import Optional
from backend.models import (
    ConfidenceFactor,
    DecisionConfidence,
    DecisionDebt,
    Plan,
    PlanMetrics,
    ResilienceResult,
    UnitType,
    UrgencyLevel,
)
from backend.state import CrisisState

# ---------------------------------------------------------------------------
# Scoring weights — single source of truth
# ---------------------------------------------------------------------------

W_CRITICAL_COVERED = 40.0
W_HIGH_COVERED = 25.0
W_MEDIUM_COVERED = 15.0
W_LOW_COVERED = 5.0
W_UNCOVERED_CRITICAL = -50.0
W_UNCOVERED_HIGH = -30.0
W_UNCOVERED_OTHER = -10.0
W_RESERVE = 8.0
W_RESILIENCE = 0.5
W_AVG_ETA = -2.0
W_MAX_ETA = -1.0


def calculate_metrics(plan: Plan, state: CrisisState) -> PlanMetrics:
    """Compute quantitative metrics for a plan."""
    covered_ids = {a.incident_id for a in plan.assignments}
    metrics = PlanMetrics(total_incidents=len(state.incidents))

    etas = [a.eta_minutes for a in plan.assignments]
    if etas:
        metrics.average_eta = round(sum(etas) / len(etas), 1)
        metrics.max_eta = round(max(etas), 1)

    for inc in state.incidents:
        if inc.id in covered_ids:
            metrics.total_covered += 1
            if inc.urgency == UrgencyLevel.CRITICAL:
                metrics.critical_covered += 1
            elif inc.urgency == UrgencyLevel.HIGH:
                metrics.high_covered += 1
            elif inc.urgency == UrgencyLevel.MEDIUM:
                metrics.medium_covered += 1
            else:
                metrics.low_covered += 1
        else:
            metrics.uncovered_incidents.append(inc.id)

    available_count = sum(1 for u in state.units if u.status.value == "AVAILABLE")
    metrics.reserve_units = available_count - len({a.unit_id for a in plan.assignments})

    # Resilience will be filled in later by the resilience engine
    plan.metrics = metrics
    return metrics


def score_plan(plan: Plan, state: CrisisState) -> float:
    """Calculate a combined decision score for a validated plan.

    Returns 0.0 for invalid plans.
    """
    if plan.validation and not plan.validation.valid:
        plan.score = 0.0
        return 0.0

    metrics = plan.metrics or calculate_metrics(plan, state)

    # Count uncovered by urgency
    uncovered_crit = 0
    uncovered_high = 0
    uncovered_other = 0
    for iid in metrics.uncovered_incidents:
        inc = state.get_incident(iid)
        if inc and inc.urgency == UrgencyLevel.CRITICAL:
            uncovered_crit += 1
        elif inc and inc.urgency == UrgencyLevel.HIGH:
            uncovered_high += 1
        else:
            uncovered_other += 1

    score = (
        metrics.critical_covered * W_CRITICAL_COVERED
        + metrics.high_covered * W_HIGH_COVERED
        + metrics.medium_covered * W_MEDIUM_COVERED
        + metrics.low_covered * W_LOW_COVERED
        + uncovered_crit * W_UNCOVERED_CRITICAL
        + uncovered_high * W_UNCOVERED_HIGH
        + uncovered_other * W_UNCOVERED_OTHER
        + metrics.reserve_units * W_RESERVE
        + metrics.resilience_score * W_RESILIENCE
        + metrics.average_eta * W_AVG_ETA
        + metrics.max_eta * W_MAX_ETA
    )

    plan.score = round(score, 1)
    return plan.score


def compare_and_select(state: CrisisState) -> CrisisState:
    """Score all candidate plans and select the best valid one."""
    best_plan = None
    best_score = -9999.0

    for plan in state.candidate_plans:
        calculate_metrics(plan, state)
        s = score_plan(plan, state)
        if plan.validation and plan.validation.valid:
            if len(plan.assignments) == 0 and len(state.incidents) > 0:
                continue  # empty plan cannot be recommended
            if s > best_score:
                best_score = s
                best_plan = plan

    state.recommended_plan = best_plan
    if best_plan:
        state.log_action(
            "Comparator",
            f"Recommended {best_plan.strategy_name}",
            f"Score {best_score}",
        )
    else:
        state.log_action("Comparator", "No feasible plan found", "All plans invalid or empty")

    state.increment_version()
    return state


# ---------------------------------------------------------------------------
# Why This Plan? — deterministic explanation from runtime metrics
# ---------------------------------------------------------------------------

_STRATEGY_LABELS = {
    "NEAREST_FIRST": "Fastest Response",
    "SEVERITY_FIRST": "Critical-First",
    "BALANCED": "Resilient Balance",
}


def generate_why_explanation(state: CrisisState) -> dict:
    """Generate 'Why This Plan?', Trade-Off, and 'Why Not X?' from runtime data.

    Returns a dict with keys: why, tradeoff, why_not (per plan id).
    All text derived from actual computed metrics.
    Returns empty strings when no recommendation exists.
    """
    rec = state.recommended_plan
    if not rec or not rec.metrics:
        return {"why": "", "tradeoff": "", "why_not": {}}

    rec_m = rec.metrics
    rec_res = state.resilience_results.get(rec.id)

    # --- WHY THIS PLAN? ---
    why_parts = []
    if rec_m.critical_covered > 0:
        why_parts.append(f"Covers {rec_m.critical_covered} critical incident(s)")
    if rec_m.high_covered > 0:
        why_parts.append(f"Covers {rec_m.high_covered} high-priority incident(s)")
    if rec_m.reserve_units > 0:
        why_parts.append(f"Maintains {rec_m.reserve_units} reserve unit(s)")
    if rec_res and rec_res.resilience_score > 0:
        why_parts.append(f"Resilience score {rec_res.resilience_score}/100")
    if rec_m.average_eta > 0:
        why_parts.append(f"Average ETA {rec_m.average_eta} min")

    # Compare to alternatives
    for plan in state.candidate_plans:
        if plan.id == rec.id or not plan.metrics or not (plan.validation and plan.validation.valid):
            continue
        other_m = plan.metrics
        other_res = state.resilience_results.get(plan.id)
        if other_res and rec_res and rec_res.resilience_score > other_res.resilience_score:
            diff = round(rec_res.resilience_score - other_res.resilience_score, 1)
            label = _STRATEGY_LABELS.get(plan.strategy_name, plan.strategy_name)
            why_parts.append(f"More resilient than {label} by {diff} points")

    why = " | ".join(why_parts) if why_parts else "Selected as highest-scoring valid plan."

    # --- TRADE-OFF ---
    tradeoff_parts = []
    
    # Absolute risks (Decision Debt / Resilience)
    if rec_res and rec_res.resilience_score < 50.0:
        tradeoff_parts.append(f"HIGH DEPENDENCY RISK (Resilience only {rec_res.resilience_score}/100)")
    
    if rec_res and rec_res.fragility_index > 1.5:
        tradeoff_parts.append(f"FRAGILE (Index: {rec_res.fragility_index})")
        
    spof_count = sum(1 for d in state.decision_debts if d.is_spof) if state.decision_debts else 0
    if spof_count > 0:
        tradeoff_parts.append(f"Accepts {spof_count} Single Point(s) of Failure")

    # Relative trade-offs vs other valid plans
    for plan in state.candidate_plans:
        if plan.id == rec.id or not plan.metrics or not (plan.validation and plan.validation.valid):
            continue
        other_m = plan.metrics
        other_res = state.resilience_results.get(plan.id)
        label = _STRATEGY_LABELS.get(plan.strategy_name, plan.strategy_name)

        if other_m.average_eta < rec_m.average_eta:
            delta = round(rec_m.average_eta - other_m.average_eta, 1)
            tradeoff_parts.append(f"Slower by {delta} min vs {label}")
        if other_m.reserve_units > rec_m.reserve_units:
            delta = other_m.reserve_units - rec_m.reserve_units
            tradeoff_parts.append(f"Uses {delta} more reserve unit(s) vs {label}")
        if other_res and rec_res and other_res.resilience_score > rec_res.resilience_score:
            delta = round(other_res.resilience_score - rec_res.resilience_score, 1)
            tradeoff_parts.append(f"Sacrifices {delta} resilience points vs {label} (Safest Plan)")
        if other_m.critical_covered > rec_m.critical_covered:
            delta = other_m.critical_covered - rec_m.critical_covered
            tradeoff_parts.append(f"Leaves {delta} more critical incident(s) uncovered vs {label}")

    if not tradeoff_parts:
        tradeoff_parts.append("Minimal measurable trade-offs against valid alternatives")

    tradeoff = " | ".join(tradeoff_parts)

    # --- WHY NOT OTHER PLANS? ---
    why_not = {}
    for plan in state.candidate_plans:
        if plan.id == rec.id:
            continue
        label = _STRATEGY_LABELS.get(plan.strategy_name, plan.strategy_name)
        if plan.validation and not plan.validation.valid:
            v = plan.validation.violations[0] if plan.validation.violations else None
            reason = v.message if v else "Constraint violation"
            why_not[plan.id] = f"INVALID: {reason}"
        elif not plan.metrics:
            why_not[plan.id] = "No metrics computed"
        else:
            m = plan.metrics
            res = state.resilience_results.get(plan.id)
            parts = []
            if plan.score is not None and rec.score is not None and rec.score > plan.score:
                parts.append(f"Lower score ({plan.score} vs {rec.score})")
            if res and rec_res and res.resilience_score < rec_res.resilience_score:
                parts.append(f"Less resilient ({res.resilience_score}/100)")
            if m.average_eta > rec_m.average_eta:
                delta = round(m.average_eta - rec_m.average_eta, 1)
                parts.append(f"Slower avg ETA (+{delta} min)")
            why_not[plan.id] = " | ".join(parts) if parts else "Lower composite score"

    return {"why": why, "tradeoff": tradeoff, "why_not": why_not}


# ---------------------------------------------------------------------------
# Decision Confidence — deterministic from runtime state
# ---------------------------------------------------------------------------

def calculate_decision_confidence(state: CrisisState) -> DecisionConfidence:
    """Determine decision confidence level from runtime state.

    Checks 6 concrete conditions. Never claims a probability.
    """
    factors = []

    # 1. Incident data completeness
    all_have_severity = all(inc.severity is not None for inc in state.incidents)
    factors.append(ConfidenceFactor(
        label="Incident data complete",
        passed=all_have_severity and len(state.incidents) > 0,
        detail=f"{len(state.incidents)} incident(s) assessed" if all_have_severity
               else "Some incidents not assessed",
    ))

    # 2. Units available
    avail = sum(1 for u in state.units if u.status.value == "AVAILABLE")
    factors.append(ConfidenceFactor(
        label="Response units available",
        passed=avail > 0,
        detail=f"{avail} of {len(state.units)} units available",
    ))

    # 3. Routes available (no fully blocked network)
    open_roads = sum(1 for r in state.road_conditions if not r.blocked)
    total_roads = len(state.road_conditions)
    routes_ok = open_roads >= max(1, total_roads // 2) if total_roads > 0 else True
    factors.append(ConfidenceFactor(
        label="Routes available",
        passed=routes_ok,
        detail=f"{open_roads}/{total_roads} road segments open",
    ))

    # 4. At least one valid plan
    has_valid = any(
        p.validation and p.validation.valid and len(p.assignments) > 0
        for p in state.candidate_plans
    )
    factors.append(ConfidenceFactor(
        label="Valid plan exists",
        passed=has_valid,
        detail="At least one feasible plan" if has_valid else "No valid plans generated",
    ))

    # 5. Resilience analysis complete
    rec = state.recommended_plan
    res_done = rec is not None and rec.id in state.resilience_results
    factors.append(ConfidenceFactor(
        label="Resilience analysis complete",
        passed=res_done,
        detail="Counterfactual stress-testing done" if res_done else "Not yet performed",
    ))

    # 6. No active single points of failure on recommended plan
    no_spof = True
    spof_detail = "No critical SPOFs detected"
    if rec and rec.id in state.resilience_results:
        spof_list = state.resilience_results[rec.id].single_points_of_failure
        if spof_list:
            no_spof = False
            spof_detail = f"SPOFs detected: {', '.join(spof_list)}"
    factors.append(ConfidenceFactor(
        label="No critical single points of failure",
        passed=no_spof,
        detail=spof_detail,
    ))

    passed = sum(1 for f in factors if f.passed)
    total = len(factors)

    if passed == total:
        level = "HIGH"
    elif passed >= total - 2:
        level = "MEDIUM"
    else:
        level = "LOW"

    return DecisionConfidence(
        level=level,
        factors=factors,
        passed_count=passed,
        total_count=total,
    )


# ---------------------------------------------------------------------------
# Decision Debt — derived from resilience data only
# ---------------------------------------------------------------------------

def calculate_decision_debts(state: CrisisState) -> list:
    """Identify decision dependencies introduced by the recommended plan.

    Only returns entries backed by actual resilience data.
    Never fabricates dependencies.
    """
    rec = state.recommended_plan
    if not rec or rec.id not in state.resilience_results:
        return []

    res = state.resilience_results[rec.id]
    debts = []

    # Count how many incidents each unit is responsible for
    unit_incident_map: dict = {}
    for a in rec.assignments:
        unit_incident_map.setdefault(a.unit_id, []).append(a.incident_id)

    for impact in res.scenario_results:
        if impact.scenario.type != "unit_failure":
            continue
        if impact.severity_impact not in ("CRITICAL", "HIGH"):
            continue

        uid = impact.scenario.target_id
        dep_incidents = unit_incident_map.get(uid, [])
        if not dep_incidents:
            continue

        is_spof = uid in res.single_points_of_failure

        # Describe the dependency from actual data
        inc_labels = []
        for iid in dep_incidents:
            inc = state.get_incident(iid)
            if inc:
                inc_labels.append(f"{inc.type} ({iid})")

        failure_parts = []
        if impact.uncovered_incidents:
            unc_labels = []
            for iid in impact.uncovered_incidents:
                inc = state.get_incident(iid)
                if inc:
                    unc_labels.append(f"{inc.type} ({iid})")
            failure_parts.append(f"Coverage lost: {', '.join(unc_labels)}")
        if impact.eta_increase_minutes > 0:
            failure_parts.append(f"ETA +{impact.eta_increase_minutes} min")

        debts.append(DecisionDebt(
            unit_id=uid,
            dependent_incident_ids=dep_incidents,
            is_spof=is_spof,
            description=f"Plan depends on {uid} for: {', '.join(inc_labels)}",
            failure_impact=" | ".join(failure_parts) if failure_parts else "Coverage degraded",
        ))

    return debts

# ---------------------------------------------------------------------------
# Human Attention — deterministic from runtime state
# ---------------------------------------------------------------------------

def evaluate_human_attention(plan: Plan, state: CrisisState, res_result: Optional[ResilienceResult] = None):
    """Deterministically check if a plan requires human attention."""
    if not plan.metrics:
        return

    reasons = []
    
    # 1. Uncovered critical incidents
    uncovered_crit = [iid for iid in plan.metrics.uncovered_incidents if state.get_incident(iid) and state.get_incident(iid).urgency == UrgencyLevel.CRITICAL]
    if uncovered_crit:
        reasons.append(f"{len(uncovered_crit)} CRITICAL incident(s) left uncovered.")
        
    # 2. Critical incidents without sufficient resources (not strictly implemented, but we can check if reserve is 0 and there are active incidents)
    if plan.metrics.reserve_units == 0 and any(inc.urgency == UrgencyLevel.CRITICAL for inc in state.incidents):
        reasons.append("Reserve units depleted while critical incidents exist.")

    # 3. No feasible plans at all (checked before this function)
    if len(plan.assignments) == 0 and len(state.incidents) > 0:
        reasons.append("No feasible assignments generated.")

    # 4. Resilience Risk (SPOF)
    if res_result and res_result.single_points_of_failure:
        reasons.append(f"Plan has {len(res_result.single_points_of_failure)} Single Point(s) of Failure.")
        
    if res_result and res_result.resilience_score < 40.0:
        reasons.append(f"Dangerously low resilience score ({res_result.resilience_score}/100).")

    if reasons:
        plan.metrics.human_attention_required = True
        plan.metrics.attention_reasons = reasons
    else:
        plan.metrics.human_attention_required = False
        plan.metrics.attention_reasons = []
