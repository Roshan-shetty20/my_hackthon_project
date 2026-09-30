"""
Crisis Command — Planner

Orchestrates candidate-plan generation, validation, and logging.
"""

from backend.allocator import (
    generate_plan_a_nearest,
    generate_plan_b_severity,
    generate_plan_c_balanced,
)
from backend.constraints import validate_plan
from backend.state import CrisisState


def generate_candidate_plans(state: CrisisState) -> CrisisState:
    """Generate three candidate plans and validate each one."""
    plan_a = generate_plan_a_nearest(state)
    plan_b = generate_plan_b_severity(state)
    plan_c = generate_plan_c_balanced(state)

    for plan in (plan_a, plan_b, plan_c):
        validate_plan(plan, state)

    state.candidate_plans = [plan_a, plan_b, plan_c]
    state.log_action("Planner", "Generated 3 candidate plans", "NEAREST, SEVERITY, BALANCED")
    state.increment_version()
    return state
