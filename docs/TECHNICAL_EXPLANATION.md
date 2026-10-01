# Crisis Command: Technical Explanation

## The Decision Pipeline

Crisis Command utilizes a 16-step strict operational decision pipeline designed to absolutely guarantee human control and mathematical correctness while utilizing LLMs purely for semantic understanding.

`	ext
       [INPUT] (Simulated / Live Events)
          ↓
[INCIDENT ASSESSMENT] (Deterministic Severity Triage)
          ↓
  [RESOURCE DEMAND] (Required vs Available Units)
          ↓
[PLAN A / PLAN B / PLAN C] (Generation via Constraints)
          ↓
[CONSTRAINT VALIDATION] (Hard Requirement Checks)
          ↓
[RESILIENCE / COUNTERFACTUAL TESTING] (Monte Carlo Failure Scenarios)
          ↓
  [PLAN COMPARISON] (Scoring Metrics)
          ↓
   [RECOMMENDATION] (Best scoring resilient plan)
          ↓
    [HUMAN APPROVAL] (Commander Authority)
          ↓
 [DISPATCH / EXECUTION] (State transition to EN_ROUTE)
          ↓
[EVENT / DISRUPTION] (Batch-processed dynamic changes)
          ↓
   [GLOBAL IMPACT] (Supply/Demand recalculation)
          ↓
       [REPLAN] (Triggered by material state change)
          ↓
      [PLAN DIFF] (Before / After Reassignment delta)
          ↓
      [AUDIT LOG] (Immutable event timeline)
`

## System Boundaries: Deterministic Core vs Gemini Explanation Layer

Crisis Command explicitly isolates algorithmic planning from Large Language Models to prevent operational hallucinations.

### The Deterministic Core (Python/FastAPI)
The core backend is entirely deterministic code. It is responsible for:
* Incident severity scoring.
* Unit allocation and coverage assignments.
* Dijkstra-based map routing on network graphs.
* Resilience stress-testing (generating failure permutations).
* Constraint validation (ensuring units aren't double-booked).
* Plan scoring.

### The Gemini Explanation Layer
Google Gemini is invoked strictly as a read-only translation layer. The deterministic core generates a vast JSON payload of metrics, scores, and diffs, which is injected into the Gemini context window.

**Gemini DOES NOT:**
* Allocate resources.
* Dispatch units.
* Change severity or ETA.
* Change resilience scores.
* Approve plans.
* Mutate CrisisState.

**Gemini DOES:**
* Translate complex mathematical tradeoffs into human-readable strategic summaries ("Plan A leaves the East quadrant exposed").
* Highlight "Single Points of Failure" identified by the deterministic engine.
* Explain the "Plan Diff" so commanders instantly understand why a unit was dynamically rerouted.
