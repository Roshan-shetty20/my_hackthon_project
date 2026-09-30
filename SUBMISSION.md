# Crisis Command - Hackathon Submission

**Team:** Team Rocket
**Hackathon:** GATEWAYS 2026
**Category:** Emergency Decision Support

## One-Line Summary
"Don't just find a response plan. Find a response plan that can survive the next surprise."

## Key Innovation
**Counterfactual Resilience Engine** - A deterministic safety layer that stress-tests emergency response plans against hypothetical unit breakdowns and road blocks to calculate **Decision Debt** and **Fragility** before human approval.

## The Dashboard Experience
SEE → TEST → DECIDE → REPLAN

## Demo Commands
```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the deterministic test suite (45/45 passing)
python -m pytest -q

# 3. Run the CLI simulation (Golden Demo scenario)
python -m backend.main

# 4. Launch the Command Center Dashboard (Use this exact command)
python -m streamlit run app.py
```
