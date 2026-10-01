# Crisis Command: Architecture Diagram

`mermaid
flowchart TD
    classDef input fill:#1e293b,stroke:#475569,color:#f8fafc;
    classDef deterministic fill:#0284c7,stroke:#0369a1,color:#f0f9ff;
    classDef ai fill:#7e22ce,stroke:#581c87,color:#faf5ff;
    classDef human fill:#059669,stroke:#047857,color:#ecfdf5;

    Events["External / Simulation / Operator Events"]:::input
    InputNorm["Input Normalization"]:::deterministic
    State["CrisisState (Versioned)"]:::deterministic
    
    Events --> InputNorm
    InputNorm --> State

    Assess["Incident Assessment"]:::deterministic
    Alloc["Resource Allocation"]:::deterministic
    Route["Network Routing"]:::deterministic

    State --> Assess
    State --> Alloc
    State --> Route

    Plans["Candidate Plans (A/B/C)"]:::deterministic
    Assess & Alloc & Route --> Plans

    Constraints["Constraint Checker"]:::deterministic
    Resilience["Resilience Engine (Stress Tests)"]:::deterministic
    Comparator["Plan Comparator"]:::deterministic

    Plans --> Constraints
    Constraints --> Resilience
    Resilience --> Comparator

    RecPlan["Recommended Plan"]:::deterministic
    Comparator --> RecPlan

    Gemini["Gemini Explanation Layer (Read-Only)"]:::ai
    RecPlan -.-> Gemini
    
    HumanApprove["Human Commander / Dispatcher"]:::human
    RecPlan --> HumanApprove
    Gemini -.-> HumanApprove

    Exec["Execution / Map UI"]:::deterministic
    HumanApprove --> Exec

    NewEvents["New Disruptions"]:::input
    Exec --> NewEvents
    
    Replan["Global Replanning"]:::deterministic
    NewEvents --> Replan
    Replan --> State

    Diff["Plan Diff Engine"]:::deterministic
    Replan --> Diff
    
    Log["Immutable Action Log"]:::deterministic
    HumanApprove --> Log
    NewEvents --> Log
`

### Legend
* **Slate (Dark Gray):** Inputs & External Triggers
* **Blue:** Deterministic Core Algorithms (Python/FastAPI)
* **Purple:** Large Language Model (Gemini)
* **Emerald (Green):** Human Authority
