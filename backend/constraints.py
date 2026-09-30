"""
Crisis Command — Constraint Checker

Deterministic plan validator.  Rejects plans that violate any of the
following hard constraints:

  1. Nonexistent unit
  2. Unavailable unit (only AVAILABLE units can be assigned)
  3. Wrong unit type for incident requirement
  4. Same unit assigned to more than one incident
  5. Required resource count not satisfied for a covered incident
  6. Reserve requirement violated (at least MIN_RESERVE_UNITS kept idle)
  7. Invalid / nonexistent incident ID
  8. ETA beyond MAX_ETA_MINUTES

Returns structured ValidationResult with typed Violation objects.
"""

from typing import Dict, Set

from backend.models import (
    Assignment,
    Plan,
    UnitStatus,
    UnitType,
    ValidationResult,
    Violation,
)
from backend.state import CrisisState

# ---------------------------------------------------------------------------
# Configurable limits
# ---------------------------------------------------------------------------

MIN_RESERVE_UNITS = 1
MAX_ETA_MINUTES = 30.0


def validate_plan(plan: Plan, state: CrisisState) -> ValidationResult:
    """Validate a plan against the current crisis state.

    Mutates ``plan.validation`` and returns the result.
    """
    violations: list[Violation] = []

    incident_map: Dict[str, object] = {inc.id: inc for inc in state.incidents}
    unit_map: Dict[str, object] = {u.id: u for u in state.units}

    assigned_units: Set[str] = set()
    # Track how many of each type are assigned per incident
    satisfied: Dict[str, Dict[UnitType, int]] = {
        inc.id: {ut: 0 for ut in UnitType} for inc in state.incidents
    }
    covered_incidents: Set[str] = set()

    for asgn in plan.assignments:
        uid = asgn.unit_id
        iid = asgn.incident_id

        # --- nonexistent unit ---
        if uid not in unit_map:
            violations.append(
                Violation(type="NONEXISTENT_UNIT", unit=uid, message=f"Unit {uid} does not exist.")
            )
            continue

        # --- nonexistent incident ---
        if iid not in incident_map:
            violations.append(
                Violation(type="INVALID_INCIDENT", incident=iid, message=f"Incident {iid} does not exist.")
            )
            continue

        unit = unit_map[uid]
        incident = incident_map[iid]

        # --- unavailable unit ---
        if unit.status != UnitStatus.AVAILABLE:
            violations.append(
                Violation(
                    type="UNAVAILABLE_UNIT",
                    unit=uid,
                    message=f"Unit {uid} is {unit.status.value}, not AVAILABLE.",
                )
            )

        # --- duplicate assignment ---
        if uid in assigned_units:
            violations.append(
                Violation(type="DUPLICATE_ASSIGNMENT", unit=uid, message=f"Unit {uid} is assigned more than once.")
            )
        assigned_units.add(uid)

        # --- wrong unit type ---
        if unit.type not in incident.required_units:
            violations.append(
                Violation(
                    type="WRONG_UNIT_TYPE",
                    unit=uid,
                    incident=iid,
                    message=f"Unit {uid} ({unit.type.value}) does not match any requirement of {iid}.",
                )
            )
        else:
            satisfied[iid][unit.type] += 1

        # --- ETA beyond limit ---
        if asgn.eta_minutes > MAX_ETA_MINUTES:
            violations.append(
                Violation(
                    type="ETA_EXCEEDED",
                    unit=uid,
                    incident=iid,
                    message=f"ETA {asgn.eta_minutes:.1f} min exceeds limit of {MAX_ETA_MINUTES} min.",
                )
            )

        covered_incidents.add(iid)

    # --- required resource count check for covered incidents ---
    for iid in covered_incidents:
        incident = incident_map[iid]
        for utype, required in incident.required_units.items():
            actual = satisfied[iid].get(utype, 0)
            if actual != required:
                violations.append(
                    Violation(
                        type="INSUFFICIENT_RESOURCES",
                        incident=iid,
                        message=(
                            f"Incident {iid} requires {required} {utype.value} "
                            f"but plan assigns {actual}."
                        ),
                    )
                )

    # --- reserve requirement ---
    available_count = sum(1 for u in state.units if u.status == UnitStatus.AVAILABLE)
    if available_count > MIN_RESERVE_UNITS and len(assigned_units) > (available_count - MIN_RESERVE_UNITS):
        violations.append(
            Violation(
                type="RESERVE_VIOLATION",
                message=(
                    f"Plan uses {len(assigned_units)} of {available_count} available units, "
                    f"violating the reserve requirement of {MIN_RESERVE_UNITS}."
                ),
            )
        )

    result = ValidationResult(valid=len(violations) == 0, violations=violations)
    plan.validation = result
    return result
