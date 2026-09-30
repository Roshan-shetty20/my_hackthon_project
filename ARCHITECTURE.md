# Crisis Command - Architecture

## Separation of Concerns

### Deterministic (Python)
- Severity calculation
- Resource availability checks
- Constraint enforcement
- ETA calculation
- Plan validation and comparison
- Resilience simulation
- State transitions and versioning

### AI/LLM (Future)
- Free-text incident parsing
- Natural-language explanations
- Trade-off summaries

LLMs NEVER directly allocate resources, bypass constraints, or modify state.

## Severity Formula

```
Base: 1
+ people_affected:   >20 -> +3, >5 -> +2, >0 -> +1
+ people_trapped:    >5  -> +3, >0 -> +2
+ vulnerable_people: >2  -> +2, >0 -> +1
+ life_threat:       +3
+ time_critical:     +2
+ spreading_hazard:  +1
+ uncertainty:       +1 (if all numeric fields are zero)
Clamped to [1, 10]
```

PROTOTYPE DECISION POLICY - NOT MEDICALLY VALIDATED.

## Comparator Scoring Formula

```
score = (critical_covered  x 40)
      + (high_covered      x 25)
      + (medium_covered    x 15)
      + (low_covered       x  5)
      - (uncovered_critical x 50)
      - (uncovered_high     x 30)
      - (uncovered_other    x 10)
      + (reserve_units     x  8)
      + (resilience_score  x  0.5)
      - (average_eta       x  2)
      - (max_eta           x  1)
```

## Resilience Formulas

```
fragility_index  = (degrading_scenarios / total_scenarios) x 100
resilience_score = 100 - fragility_index
```

A scenario is "degrading" if it causes a critical/high incident to become uncovered or the plan to become invalid.

## State Versioning

Every meaningful mutation increments the version counter. Previous snapshots are preserved in StateHistory and are never modified.
