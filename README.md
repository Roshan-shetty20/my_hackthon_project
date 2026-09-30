# Crisis Command
### Resilient Decision Intelligence for Emergency Response

> **Team Rocket | GATEWAYS 2026 Hackathon**
> ⚠ SIMULATION DATA — No real emergency data is used.

---

## One-Line Pitch

An emergency decision-support system that doesn't just recommend a response — it tries to break the response plan before reality does.

---

## The Problem

Emergency dispatchers face a multi-objective problem under time pressure:

- Multiple simultaneous incidents at different severity levels
- Limited units with different types and locations
- No systematic way to know if a plan will survive the next failure
- Trade-offs between speed, coverage, and operational reserve

Most systems ask: **"What should we do now?"**

---

## The Solution

Crisis Command asks: **"What happens if our plan fails?"**

```
SEE → TEST → DECIDE → REPLAN
```

1. **SEE** — Understand the crisis: incidents, units, routes, severity
2. **TEST** — Stress-test every candidate response plan against simulated failures
3. **DECIDE** — Compare plans with full trade-offs, approve with confidence
4. **REPLAN** — When reality changes, replan instantly and explain what changed

---

## Why It's Different

**Most emergency systems recommend a plan.**

Crisis Command uses a **Counterfactual Resilience Engine** to ask:

> *"What if AMB-01 breaks down? What if this road is blocked? Which incidents become uncovered?"*

For every candidate plan, the system simulates every single-unit failure and every road blockage, measures the impact, and tells the commander:

- **Resilience Score** (how many scenarios the plan survives)
- **Fragility Index** (% of scenarios that degrade the plan)
- **Single Points of Failure** (which units, if lost, cause critical incidents to go uncovered)
- **Decision Debt** (hidden dependencies introduced by the current assignment)

---

## Core Product Loop

```
Crisis Incident Events
        ↓
Incident Assessment Agent
[Deterministic Severity Engine]
        ↓
Resource Allocation Agent
[3 Independent Strategies: NEAREST / SEVERITY / BALANCED]
        ↓
Route / Logistics Agent
[Haversine ETA + Road Block Penalties]
        ↓
Constraint Checker (8 Hard Rules)
        ↓
Plan Comparator (11-Factor Scoring Formula)
        ↓
Counterfactual Resilience Engine
[Deep-copy failure simulations — real state never mutated]
        ↓
Why This Plan? + Trade-Off + Decision Debt
        ↓
Human Dispatcher Approval / Rejection
        ↓
Dynamic Replanning on Disruption
        ↓
Plan Diff (What Changed? Why?)
        ↓
Action Log (Full Audit Trail)
```

---

## Architecture

### Four Agents

| Agent | Role | Implementation |
|-------|------|---------------|
| Incident Assessment Agent | Score incidents 1-10 | `backend/severity.py` |
| Resource Allocation Agent | Generate 3 candidate plans | `backend/allocator.py` |
| Route / Logistics Agent | ETA + route feasibility | `backend/route.py` |
| Command / Planning Agent | Select, explain, compare | `backend/comparator.py` |

### Deterministic Safety Layer

No LLM can bypass these:

| Component | File | Role |
|-----------|------|------|
| Severity Engine | `severity.py` | Documented formula, 1-10, clamped |
| Constraint Checker | `constraints.py` | 8 hard rules, rejects invalid plans |
| Plan Comparator | `comparator.py` | 11-factor transparent scoring |
| Resilience Engine | `resilience.py` | Deep-copy counterfactual simulation |
| Plan Diff | `diff.py` | Actual-change explanations, nothing fabricated |
| State Versioning | `state.py` | Immutable history of all state transitions |
| Action Log | `state.py` | Full timestamped audit trail |
| Replanner | `replanner.py` | Handles breakdown, road block, new incident |

### LLM Architecture

The system works fully without any API key.

LLM integration is stubbed in `backend/llm/` for future work. Deterministic template fallback ensures demo always works.

**LLMs may assist with:** free-text incident parsing, narrative explanations.

**LLMs may NOT control:** feasibility, availability, hard constraints, resource allocation, CrisisState mutation.

---

## Plan Survivability

The hero feature of Crisis Command.

For every valid plan, the resilience engine runs controlled failure simulations:

```
fragility_index  = (degrading_scenarios / total_scenarios) × 100
resilience_score = 100 − fragility_index
```

A scenario is "degrading" if it causes a CRITICAL or HIGH incident to become uncovered, or makes the plan invalid.

This gives the dispatcher a concrete, honest answer to:

**"Can this plan survive the next failure?"**

---

## Decision Debt

A novel concept derived entirely from runtime data.

When a plan assigns a critical unit to a critical incident, it creates a dependency. If that unit fails, coverage is lost. Decision Debt surfaces this dependency before the commander commits.

Example:
```
DECISION DEBT
Plan depends on RES-02 for: Flood Rescue (INC-001)
If RES-02 fails: Coverage lost: Flood Rescue (INC-001)
⚠ SINGLE POINT OF FAILURE
```

All debt is backed by actual resilience simulation data. Nothing is fabricated.

---

## Human-in-the-Loop

The commander is always in control:

1. System recommends a plan with evidence
2. Commander reviews Why This Plan? + Trade-Offs + Decision Debt
3. Commander approves or rejects
4. All decisions recorded in Action Log
5. After disruptions, commander approves the new recommendation

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Data models | Python + Pydantic v2 |
| Backend logic | Python (pure deterministic) |
| REST API | FastAPI + Uvicorn |
| Dashboard | Streamlit |
| Map | Folium + streamlit-folium |
| Persistence | SQLite |
| Testing | pytest (45 tests) |
| LLM (optional) | Google Gemini (stubbed) |

---

## Setup

```bash
# Clone the repository
git clone <repo-url>
cd crisis-command

# Install dependencies
pip install -r requirements.txt
```

No API key required for the core demonstration.

Optional: add `GEMINI_API_KEY=your_key` to `.env` for LLM-assisted explanations.

---

## Run Instructions

```bash
# Run all tests (should show 45 passed)
python -m pytest -q

# CLI demo (full pipeline + breakdown simulation)
python -m backend.main

# Streamlit command center (recommended for demo)
python -m streamlit run app.py
# Open: http://localhost:8501

# REST API (14 endpoints)
uvicorn backend.api:app --reload
# Docs: http://localhost:8000/docs
```

---

## Demo Instructions (3 minutes)

Follow this exact sequence for maximum impact:

1. **Initialize Crisis** — 3 incidents (Flood CRITICAL, Medical HIGH, Road Accident MEDIUM) + 6 units appear on the map

2. **Generate & Evaluate Plans** — System shows Plan A (Fastest), Plan B (Critical-First), Plan C (Resilient Balance). Validation status for each.

3. **TEST tab → Resilience Lab** — Show scenario-by-scenario stress tests. Single Points of Failure highlighted. Resilience scores compared.

4. **DECIDE tab → Plan Comparison** — Side-by-side table with "Why not Plan A/B?" explanations.

5. **Command Decision panel** — "Why This Plan?" and "Trade-Off" generated from runtime metrics.

6. **Decision Debt** — Show dependencies if present.

7. **Approve Plan** — Dispatcher commits. Assignment lines drawn on map.

8. **Simulate Breakdown (AMB-01)** — Major demo moment. Map updates. Plan automatically replans.

9. **REPLAN tab → What Changed?** — BEFORE/AFTER view showing exactly which assignments changed, which incidents became uncovered, ETA changes.

10. **Action Log** — Full audit trail of every agent action and dispatcher decision.

11. **Reset Demo** — Full reset for repeated demonstrations.

---

## Testing

```
45 tests across 8 modules:

test_severity.py     — 8 tests: formula, bands, clamping, missing data
test_constraints.py  — 9 tests: all 8 violation types + valid plan
test_allocator.py    — 4 tests: 3 strategies + no-units edge case
test_planner.py      — 6 tests: generation, validation, selection
test_resilience.py   — 4 tests: scenarios, score range, SPOF detection
test_state.py        — 5 tests: versioning, snapshots, history
test_replanning.py   — 4 tests: breakdown, road block, new incident
test_plan_diff.py    — 5 tests: add, remove, change, ETA, trigger
```

---

## Deployment

The application runs locally without any cloud dependencies.

For deployment:

```bash
# Environment setup
cp .env.example .env
# Edit .env to add optional API keys

# Production API
uvicorn backend.api:app --host 0.0.0.0 --port 8000

# Production dashboard
python -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

Docker support: add a `Dockerfile` targeting Python 3.11+ with `pip install -r requirements.txt`.

---

## Simulation Disclaimer

⚠ **All emergency incidents, response units, and disruptions in this system are simulated for demonstration purposes only.**

No real emergency data, real dispatch systems, or real geographic emergency information is used.

Public map tiles are provided by OpenStreetMap contributors under the ODbL license.

The severity formula is a prototype decision policy and is **not medically validated**.

---

## Known Limitations

- ETA uses Haversine distance, not real road network routing (OSM integration is stubbed)
- Severity formula is a prototype, not validated against real emergency protocols
- LLM integration is stubbed (system works fully without API key)
- No real-time sensor or weather data (stubs exist in `backend/integrations/`)
- Single-machine deployment only in MVP

---

## Team

**Team Rocket | GATEWAYS 2026**

---

*"Don't just find a response plan. Try to break it before reality does."*
