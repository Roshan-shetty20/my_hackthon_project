"""
Crisis Command — Plan Diff

Computes a structured diff between two plans showing exactly what
changed and why.  Every explanation corresponds to an actual state
change — nothing is invented.
"""

from typing import Dict

from backend.models import Assignment, Plan, PlanDiff
from backend.state import CrisisState


def compute_plan_diff(
    before: Plan,
    after: Plan,
    state: CrisisState,
    trigger: str = "",
) -> PlanDiff:
    """Compare two plans and produce a structured diff."""
    before_map: Dict[str, Assignment] = {a.incident_id: a for a in before.assignments}
    after_map: Dict[str, Assignment] = {a.incident_id: a for a in after.assignments}

    all_incidents = set(before_map.keys()) | set(after_map.keys())

    added = []
    removed = []
    changed = []
    newly_uncovered = []
    newly_covered = []
    eta_changes: Dict[str, float] = {}

    for iid in all_incidents:
        b = before_map.get(iid)
        a = after_map.get(iid)

        if b and not a:
            removed.append(b)
            newly_uncovered.append(iid)

        elif a and not b:
            added.append(a)
            newly_covered.append(iid)

        elif a and b:
            if a.unit_id != b.unit_id:
                changed.append({
                    "incident": iid,
                    "before_unit": b.unit_id,
                    "after_unit": a.unit_id,
                    "before_eta": b.eta_minutes,
                    "after_eta": a.eta_minutes,
                })
            eta_diff = round(a.eta_minutes - b.eta_minutes, 1)
            if abs(eta_diff) > 0.1:
                eta_changes[iid] = eta_diff

    reallocation_reasons = []

    # Build explanation from actual changes
    explanation_parts = []
    if trigger:
        explanation_parts.append(f"Trigger: {trigger}")
    if changed:
        for c in changed:
            inc = state.get_incident(c["incident"])
            inc_label = f"{inc.type}" if inc else c["incident"]
            explanation_parts.append(
                f"{c['before_unit']} replaced by {c['after_unit']} for {inc_label}"
            )
            
            # Phase 4 explicit reallocation reason evidence
            new_u = state.get_unit(c["after_unit"])
            reason_dict = {
                "incident_id": c["incident"],
                "previous_unit": c["before_unit"],
                "new_unit": c["after_unit"],
                "trigger": trigger,
                "incident_severity": getattr(inc, "severity", None) if inc else None,
                "resource_availability": getattr(new_u, "status", None).value if new_u else None,
                "eta_impact": round(c["after_eta"] - c["before_eta"], 1),
                "reason_for_change": f"Reassigned to {c['after_unit']} due to {trigger}. Provides feasible route with ETA {c['after_eta']}m."
            }
            reallocation_reasons.append(reason_dict)
    if newly_uncovered:
        for iid in newly_uncovered:
            inc = state.get_incident(iid)
            label = inc.type if inc else iid
            explanation_parts.append(f"{label} ({iid}) is now uncovered")
    if newly_covered:
        for iid in newly_covered:
            inc = state.get_incident(iid)
            label = inc.type if inc else iid
            explanation_parts.append(f"{label} ({iid}) is now covered")
    for iid, delta in eta_changes.items():
        sign = "+" if delta > 0 else ""
        inc = state.get_incident(iid)
        label = inc.type if inc else iid
        explanation_parts.append(f"{label} ETA {sign}{delta} min")

    return PlanDiff(
        before_plan_id=before.id,
        after_plan_id=after.id,
        added_assignments=added,
        removed_assignments=removed,
        changed_units=changed,
        newly_uncovered=newly_uncovered,
        newly_covered=newly_covered,
        eta_changes=eta_changes,
        explanation="\n".join(explanation_parts),
        trigger=trigger,
        reallocation_reasons=reallocation_reasons,
    )
