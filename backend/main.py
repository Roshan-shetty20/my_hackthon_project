"""
Crisis Command - CLI Demo

Running:  python -m backend.main

Demonstrates the full deterministic pipeline:
  Load -> Assess -> Plan -> Validate -> Compare -> Resilience -> Recommend
"""

import json
import sys
from pathlib import Path

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.models import Incident, Unit, RoadCondition
from backend.state import CrisisState, StateHistory
from backend.severity import assess_incident
from backend.planner import generate_candidate_plans
from backend.comparator import compare_and_select
from backend.resilience import evaluate_plan_resilience, generate_resilience_summary
from backend.replanner import apply_unit_breakdown


def load_data():
    base = Path(__file__).parent.parent / "data"
    def _load(name):
        with open(base / name) as f:
            return json.load(f)

    incidents = [Incident(**{k: v for k, v in d.items() if k != "_comment"}) for d in _load("incidents.json")]
    units = [Unit(**{k: v for k, v in d.items() if k != "_comment"}) for d in _load("units.json")]
    roads = [RoadCondition(**{k: v for k, v in d.items() if k != "_comment"}) for d in _load("roads.json")]
    return incidents, units, roads


def main():
    print("=" * 60)
    print("  CRISIS COMMAND - Deterministic MVP")
    print("  SIMULATION DATA - No real emergency data is used.")
    print("=" * 60)

    try:
        incidents, units, roads = load_data()
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)

    state = CrisisState(incidents=incidents, units=units, road_conditions=roads)
    history = StateHistory()

    # ---- Assess ----
    for inc in state.incidents:
        assess_incident(inc)
    state.log_action("IncidentAssessmentAgent", "Assessed all incidents")

    print(f"\nSTATE VERSION: {state.version}\n")

    print("INCIDENTS")
    print("-" * 55)
    for inc in state.incidents:
        reqs = ", ".join(f"{k.value}x{v}" for k, v in inc.required_units.items())
        print(f"  {inc.id} | {inc.type:<20s} | Severity {inc.severity:>2} | {inc.urgency.value if inc.urgency else '?'}")
        print(f"         Requires: {reqs}")
    print()

    # ---- Plan ----
    state = generate_candidate_plans(state)
    state = compare_and_select(state)

    # ---- Resilience ----
    print("PLANS")
    print("-" * 55)
    for plan in state.candidate_plans:
        valid_str = "VALID" if plan.validation and plan.validation.valid else "INVALID"
        violations = ""
        if plan.validation and not plan.validation.valid:
            violations = " (" + "; ".join(v.message for v in plan.validation.violations[:2]) + ")"

        # Run resilience on valid plans
        res_str = ""
        if plan.validation and plan.validation.valid and len(plan.assignments) > 0:
            res = evaluate_plan_resilience(plan, state)
            state.resilience_results[plan.id] = res
            if plan.metrics:
                plan.metrics.resilience_score = res.resilience_score
                plan.metrics.fragility_index = res.fragility_index
            res_str = f" | Resilience {res.resilience_score}/100"

        score_str = f"Score: {plan.score}" if plan.score is not None else "Score: -"
        print(f"  {plan.strategy_name:<18s} | {valid_str:<7s} | {score_str}{res_str}{violations}")

        if plan.metrics:
            m = plan.metrics
            print(f"         Covered: {m.total_covered}/{m.total_incidents} | Avg ETA: {m.average_eta} min | Reserve: {m.reserve_units}")
        if plan.assignments:
            for a in plan.assignments:
                print(f"           {a.unit_id} -> {a.incident_id} (ETA {a.eta_minutes} min)")
    print()

    # ---- Recommendation ----
    print("RECOMMENDED PLAN")
    print("-" * 55)
    if state.recommended_plan:
        plan = state.recommended_plan
        print(f"  {plan.strategy_name}")
        print(f"  Score: {plan.score}")
        if plan.metrics:
            print(f"  Coverage: {plan.metrics.total_covered}/{plan.metrics.total_incidents}")
            print(f"  Avg ETA: {plan.metrics.average_eta} min")
            print(f"  Reserve: {plan.metrics.reserve_units} units")
        res = state.resilience_results.get(plan.id)
        if res:
            print()
            print("  RESILIENCE ANALYSIS")
            for line in generate_resilience_summary(res).split("\n"):
                print(f"    {line}")
    else:
        print("  NONE - no feasible plan found")
    print()

    # ---- Simulate breakdown ----
    history.save(state)
    prev_plan = state.recommended_plan

    print("=" * 60)
    print("  SIMULATION: AMB-01 BREAKDOWN")
    print("=" * 60)
    state = apply_unit_breakdown(state, history, "AMB-01")

    print(f"\nSTATE VERSION: {state.version}\n")
    if state.recommended_plan:
        plan = state.recommended_plan
        print(f"  NEW RECOMMENDATION: {plan.strategy_name}")
        print(f"  Score: {plan.score}")
        if plan.metrics:
            print(f"  Coverage: {plan.metrics.total_covered}/{plan.metrics.total_incidents}")
    else:
        print("  NONE - no feasible plan found after breakdown")

    # ---- Plan diff ----
    if state.plan_diffs:
        diff = state.plan_diffs[-1]
        print()
        print("  PLAN DIFF")
        print(f"  Trigger: {diff.trigger}")
        for line in diff.explanation.split("\n"):
            print(f"    {line}")
    print()

    # ---- Action log ----
    print("ACTION LOG")
    print("-" * 55)
    for entry in state.action_log[-10:]:
        print(f"  [{entry.agent}] {entry.action}  {entry.details}")
    print()


if __name__ == "__main__":
    main()
