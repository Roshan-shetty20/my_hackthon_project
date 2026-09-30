"""
Crisis Command — Command / Planning Agent

Interface for future LLM integration.  Currently uses the deterministic
comparator + resilience engine.  Phase 2: Gemini generates natural-language
explanations of trade-offs.
"""

from backend.comparator import compare_and_select
from backend.resilience import evaluate_plan_resilience
from backend.state import CrisisState


class CommandPlanningAgent:
    """Select and explain the recommended plan.

    MVP: deterministic scoring + template explanations.
    Phase 2: LLM summarises trade-offs in natural language.
    """

    def select_plan(self, state: CrisisState) -> CrisisState:
        state = compare_and_select(state)

        # Run resilience on valid plans
        for plan in state.candidate_plans:
            if plan.validation and plan.validation.valid:
                result = evaluate_plan_resilience(plan, state)
                state.resilience_results[plan.id] = result
                if plan.metrics:
                    plan.metrics.resilience_score = result.resilience_score
                    plan.metrics.fragility_index = result.fragility_index
                from backend.comparator import evaluate_human_attention
                evaluate_human_attention(plan, state, result)

        # Generate template explanation
        if state.recommended_plan:
            plan = state.recommended_plan
            res = state.resilience_results.get(plan.id)
            parts = [f"Selected {plan.strategy_name} (score {plan.score})"]
            if plan.metrics:
                parts.append(f"Covers {plan.metrics.total_covered}/{plan.metrics.total_incidents} incidents")
                parts.append(f"Average ETA: {plan.metrics.average_eta} min")
                parts.append(f"Reserve: {plan.metrics.reserve_units} units")
            if res:
                parts.append(f"Resilience: {res.resilience_score}/100")
            plan.explanation = " | ".join(parts)
            
            # Fetch AI explanation
            try:
                from backend.llm.gemini_provider import GeminiProvider
                import json
                
                provider = GeminiProvider()
                if provider.is_available():
                    evidence = {
                        "state_version": state.version,
                        "recommended_plan": plan.model_dump() if hasattr(plan, "model_dump") else plan.dict(),
                        "resilience": res.model_dump() if res and hasattr(res, "model_dump") else (res.dict() if res else None),
                        "decision_debts": [d.model_dump() if hasattr(d, "model_dump") else d.dict() for d in state.decision_debts],
                        "alternative_plans": [p.model_dump() if hasattr(p, "model_dump") else p.dict() for p in state.candidate_plans if p.id != plan.id]
                    }
                    prompt = f"Analyze the following verified decision evidence and explain the recommended plan, alternatives, tradeoffs, and risks:\n{json.dumps(evidence, default=str)}"
                    llm_response = provider.generate_explanation(prompt)
                    if llm_response:
                        plan.ai_explanation = json.loads(llm_response)
            except Exception as e:
                print(f"Failed to generate or parse AI explanation: {e}")

        state.log_action("CommandPlanningAgent", "Plan selection and explanation complete")
        return state
