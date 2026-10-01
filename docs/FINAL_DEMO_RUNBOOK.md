# Crisis Command — Final Demo Runbook

This document specifies the exact, manual judge-facing demonstration workflow for the Crisis Command platform.

## Pre-Requisites
1. Ensure python -m uvicorn backend.server:app --port 8000 is running.
2. Ensure 
pm run dev is running on port 3000.
3. Open a **fresh browser session** (Incognito recommended) to http://localhost:3000/command.

---

## 1. Introduction (0:00 - 0:30)
**Action:** Open http://localhost:3000/command.
* **Click:** START SESSION (Do not click Guided Demo).
* **Verbal:** "Welcome to Crisis Command. We are looking at a live emergency response copilot. We just received an initial situation involving multiple critical incidents in Surat."
* **Concept:** Human-in-the-loop initialization.

## 2. Assessment & Generation (0:30 - 1:00)
**Action:** Direct attention to the Incident Queue on the left.
* **Verbal:** "The system has aggregated incidents. We have severe resource constraints."
* **Click:** GENERATE RESPONSE PLANS
* **Verbal:** "Instead of asking an LLM to guess, our deterministic backend calculates constraint-checked alternatives."
* **Concept:** Deterministic generation. LLMs are NOT routing ambulances.

## 3. Plan Comparison & Recommendation (1:00 - 1:30)
**Action:** Look at the right panel.
* **Verbal:** "The engine generated Plan A, B, and C, ran them through a Resilience Stress Test (simulating 100 parallel failures), and recommended Plan A."
* **Click:** AI Command Brief
* **Verbal:** "Gemini is used purely as an explanation layer to translate the deterministic math into human tradeoffs."
* **Concept:** Explainable AI over deterministic math.

## 4. Human Approval & Dispatch (1:30 - 2:00)
**Action:** Review Plan A in the right panel.
* **Click:** APPROVE PLAN on the Plan Card.
* **Verbal:** "The AI does not dispatch. The human commander reviews the tradeoffs and formally approves."
* **Concept:** Human authority.
* **Action:** Direct attention to the Map and Incident Queue.
* **Verbal:** "Units immediately transition to EN_ROUTE."

## 5. Execution & Tick (2:00 - 2:30)
**Action:** Click ADVANCE TICK multiple times.
* **Verbal:** "As time passes, units move along calculated Dijkstra routes."
* **Action:** Click a route on the map.
* **Concept:** Live operational state integration.

## 6. Single Disruption (2:30 - 3:00)
**Action:** Open Disruption Panel. Select Road Block. Click APPLY.
* **Verbal:** "A road has flooded. The system intercepts the disruption, recalculates global impact, and invalidates the active route."
* **Concept:** Dynamic condition changes.

## 7. Multi-Disruption & Replanning (3:00 - 4:00)
**Action:** Open Disruption Panel. Select Unit Breakdown AND New Incident (Chemical Spill + Building Collapse). Click APPLY N DISRUPTIONS.
* **Verbal:** "In real crises, disasters cascade. We just lost an ambulance while two new critical incidents spawned simultaneously."
* **Action:** Observe the Global Impact analysis tab.
* **Verbal:** "The system evaluates the global supply/demand shortfall atomically."
* **Click:** REVIEW & REPLAN
* **Action:** Open Plan Diff tab.
* **Verbal:** "The system generated a new resilient recommendation, and generated a surgical Plan Diff explaining exactly who was reassigned and why."
* **Concept:** Atomic multi-disruption processing and Plan Diff transparency.

## 8. Secondary Evidence (4:00 - 5:00)
**Action:** Navigate to the Resilience Lab and Timeline tabs.
* **Verbal:** "Every decision is backed by mathematical stress-testing and an immutable audit log."
* **Concept:** Auditability and trust.
