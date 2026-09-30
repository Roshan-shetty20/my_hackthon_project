"""
Crisis Command — Resource Allocator

Three genuinely different allocation strategies.  Each calculates
assignments independently from the current crisis state.

  PLAN_A  NEAREST_FIRST   — prioritise proximity / lowest ETA
  PLAN_B  SEVERITY_FIRST  — prioritise highest severity
  PLAN_C  BALANCED        — balance severity, ETA, reserve

None of the strategies hard-code the winning plan.
"""

from typing import List, Set

from backend.models import Assignment, Plan, UnitStatus, UnitType
from backend.route import calculate_eta
from backend.state import CrisisState
from backend.constraints import MIN_RESERVE_UNITS


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _try_assign(
    incident,
    available_units: list,
    used: Set[str],
    road_conditions,
) -> List[Assignment]:
    """Try to fully satisfy one incident's requirements.

    Returns assignments only if *all* required units can be fulfilled.
    """
    assignments: List[Assignment] = []
    for utype, count in incident.required_units.items():
        candidates = sorted(
            [u for u in available_units if u.type == utype and u.id not in used],
            key=lambda u: calculate_eta(
                u.latitude, u.longitude,
                incident.latitude, incident.longitude,
                road_conditions,
            ),
        )
        if len(candidates) < count:
            return []  # cannot satisfy
        for u in candidates[:count]:
            eta = calculate_eta(
                u.latitude, u.longitude,
                incident.latitude, incident.longitude,
                road_conditions,
            )
            assignments.append(Assignment(incident_id=incident.id, unit_id=u.id, eta_minutes=eta))
    return assignments


# ---------------------------------------------------------------------------
# Strategy A — Nearest-First
# ---------------------------------------------------------------------------

def generate_plan_a_nearest(state: CrisisState) -> Plan:
    """Process incidents in order of minimum-distance to any matching unit."""
    plan = Plan(id="PLAN_A", strategy_name="NEAREST_FIRST")
    available = [u for u in state.units if u.status == UnitStatus.AVAILABLE]
    roads = state.road_conditions
    used: Set[str] = set()

    # Compute min-ETA for each incident and sort ascending (closest first)
    def min_eta(inc):
        etas = []
        for utype in inc.required_units:
            for u in available:
                if u.type == utype:
                    etas.append(
                        calculate_eta(u.latitude, u.longitude, inc.latitude, inc.longitude, roads)
                    )
        return min(etas) if etas else 999.0

    ordered = sorted(state.incidents, key=min_eta)

    for inc in ordered:
        assigns = _try_assign(inc, available, used, roads)
        if assigns:
            for a in assigns:
                used.add(a.unit_id)
            plan.assignments.extend(assigns)

    return plan


# ---------------------------------------------------------------------------
# Strategy B — Severity-First
# ---------------------------------------------------------------------------

def generate_plan_b_severity(state: CrisisState) -> Plan:
    """Process incidents by descending severity (highest first)."""
    plan = Plan(id="PLAN_B", strategy_name="SEVERITY_FIRST")
    available = [u for u in state.units if u.status == UnitStatus.AVAILABLE]
    roads = state.road_conditions
    used: Set[str] = set()

    ordered = sorted(state.incidents, key=lambda x: -(x.severity or 0))

    for inc in ordered:
        assigns = _try_assign(inc, available, used, roads)
        if assigns:
            for a in assigns:
                used.add(a.unit_id)
            plan.assignments.extend(assigns)

    return plan


# ---------------------------------------------------------------------------
# Strategy C — Balanced
# ---------------------------------------------------------------------------

def generate_plan_c_balanced(state: CrisisState) -> Plan:
    """Balance severity with reserve maintenance.

    Processes incidents by severity but skips the lowest-priority incident
    when doing so would consume the last reserve unit.
    """
    plan = Plan(id="PLAN_C", strategy_name="BALANCED")
    available = [u for u in state.units if u.status == UnitStatus.AVAILABLE]
    roads = state.road_conditions
    used: Set[str] = set()

    ordered = sorted(state.incidents, key=lambda x: -(x.severity or 0))

    for inc in ordered:
        assigns = _try_assign(inc, available, used, roads)
        if not assigns:
            continue

        # Would this exhaust reserves?
        remaining = len(available) - len(used) - len(assigns)
        if remaining < MIN_RESERVE_UNITS and len(available) > MIN_RESERVE_UNITS:
            continue  # skip to preserve reserve

        for a in assigns:
            used.add(a.unit_id)
        plan.assignments.extend(assigns)

    return plan
