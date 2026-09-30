import sys

def patch_app():
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    # We replace generate_why_explanation(state) with a custom wrapper that prefers AI explanation
    
    wrapper = """def get_explanation_data(plan, state):
    if plan and hasattr(plan, "ai_explanation") and plan.ai_explanation:
        ai = plan.ai_explanation
        why_not_val = ai.get("why_not_alternatives", {})
        if isinstance(why_not_val, str):
            why_not_val = {p.id: why_not_val for p in state.candidate_plans}
        return {
            "why": ai.get("why_this_plan", ""),
            "tradeoff": ai.get("trade_off", ""),
            "why_not": why_not_val,
            "ai_summary": ai.get("summary", ""),
            "ai_risk": ai.get("risk", ""),
            "is_ai": True
        }
    else:
        return generate_why_explanation(state)"""
        
    # Let's insert the wrapper near the top, after imports
    if "def get_explanation_data" not in content:
        content = content.replace("from backend.simulator import DeterministicSimulator\n", "from backend.simulator import DeterministicSimulator\n\n" + wrapper + "\n")
        
    # Replace calls
    content = content.replace("why_data = generate_why_explanation(state)", "why_data = get_explanation_data(plan, state) if 'plan' in locals() and plan else get_explanation_data(state.recommended_plan, state)")
    
    # We need to add the AI Decision Explanation banner
    why_this_plan_orig = """<div style="font-size:0.62rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#64748b;margin-bottom:4px;">Why this plan?</div>"""
    why_this_plan_new = """<div style="font-size:0.62rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#64748b;margin-bottom:4px;">Why this plan? { ' (AI GENERATED)' if why_data.get('is_ai') else '' }</div>"""
    content = content.replace(why_this_plan_orig, why_this_plan_new)
    
    tradeoff_orig = """<div style="font-size:0.62rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#f59e0b;margin-bottom:4px;">Trade-Off</div>"""
    tradeoff_new = """<div style="font-size:0.62rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#f59e0b;margin-bottom:4px;">Trade-Off { ' (AI GENERATED)' if why_data.get('is_ai') else '' }</div>"""
    content = content.replace(tradeoff_orig, tradeoff_new)
    
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched app.py")

patch_app()
