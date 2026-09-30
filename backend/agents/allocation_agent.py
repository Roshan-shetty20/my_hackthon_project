"""
Crisis Command — Resource Allocation Agent

Interface for future LLM integration.  Currently delegates to the
deterministic allocator and constraint checker.
"""

from backend.planner import generate_candidate_plans
from backend.state import CrisisState


class ResourceAllocationAgent:
    """Generate and validate candidate allocation plans.

    MVP: deterministic allocation only.
    Phase 2: LLM suggests allocation rationale / explanations.
    """

    def generate_plans(self, state: CrisisState) -> CrisisState:
        state = generate_candidate_plans(state)
        state.log_action("ResourceAllocationAgent", "Generated candidate allocations")
        return state
