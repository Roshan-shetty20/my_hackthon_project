# Crisis Command: Judge Q&A

**1. Why multi-agent?**
Complex systems require bounded contexts. Having a single agent manage routing, dispatch, explanation, and stress-testing introduces hallucination risks. By separating the deterministic constraint-solvers from the explanation LLM, we guarantee correctness while preserving natural language insights.

**2. Why not a single LLM?**
LLMs are probabilistic. You cannot mathematically guarantee an LLM won't double-book an ambulance or ignore a road closure. We use deterministic algorithms for the math, and the LLM strictly for translation.

**3. What happens when conditions change?**
The system treats dynamic conditions (disruptions) as state mutations. It triggers a global impact analysis, invalidates the current plan, generates a new versioned Plan A/B/C, and alerts the commander to review a Plan Diff.

**4. How are hard constraints enforced?**
Through a dedicated Python validation layer that checks the output of the assignment algorithms before the plan is ever presented to the user. 

**5. How are plans compared?**
We use a multi-factor scoring mechanism assessing: Critical Coverage, Average ETA, Reserve Units kept in pool, and the Resilience Score derived from stress-testing.

**6. How do you handle simultaneous incidents?**
The API accepts atomic batch payloads (POST /events). The engine evaluates the global supply/demand simultaneously rather than sequentially, avoiding race conditions and sub-optimal greedy assignments.

**7. What happens when resources are insufficient?**
The system explicitly shows the shortfall in the Global Impact tab. It prioritizes Critical/High severity incidents based on triage algorithms and leaves Low severity incidents uncovered, flagging them in red for the commander.

**8. What happens when an ambulance breaks down?**
The unit status becomes UNAVAILABLE. Its active mission fails. The system automatically recalculates the global map, finds the next nearest available unit, and presents a Plan Diff for the commander to approve the reassignment.

**9. What happens when a road is blocked?**
The graph network edge is severed.

**10. How does rerouting work?**
The deterministic routing engine runs Dijkstra's algorithm again, excluding the severed edges. If a path exists, the ETA updates. If no path exists, the mission fails and global replanning triggers.

**11. Why is human approval required?**
Because in life-critical systems, accountability remains human. AI is a copilot, not an autopilot.

**12. What does Gemini actually do?**
It acts as the "AI Command Brief." It translates the complex JSON constraints, plan differences, and resilience stress-tests into a highly readable strategic summary (Trade-offs, Risks, Why this plan).

**13. What happens if Gemini is unavailable?**
The system falls back to a deterministic text generator. The application is entirely capable of running without the LLM.

**14. How do you prevent hallucinated operational decisions?**
By hard-coding state mutations behind API boundaries that Gemini literally cannot access. Gemini only has read access to the finalized Plan.

**15. How is resilience measured?**
The backend generates 100 permutations of unit failures and road blocks. It scores how well Plan A survives these failures compared to Plan B.

**16. What makes this different from a static dashboard?**
Static dashboards require the human to calculate impact manually. Crisis Command actively computes the impact, solves the logistical puzzle, and presents mathematically verified options.

**17. Can the architecture use real emergency feeds?**
Yes. The /events batch endpoint is designed to ingest standardized JSON payloads from external CAD (Computer-Aided Dispatch) systems or IoT weather sensors.

**18. What is simulated versus externally sourced?**
Currently, the incident generation and ticks are simulated for the hackathon, but the entire CrisisState management backend treats them exactly as real external API requests.

**19. How is state versioning handled?**
Every mutation increments a state version (e.g., 21). Plans generated under 20 cannot be approved in 21, strictly preventing stale execution.

**20. How is the system auditable?**
Every state mutation (approval, dispatch, disruption) is appended to an immutable chronological ction_log array.
