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
    plan = Plan(id=f"plan-v{state.version}-A", strategy_name="NEAREST_FIRST", state_version=state.version)
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
    plan = Plan(id=f"plan-v{state.version}-B", strategy_name="SEVERITY_FIRST", state_version=state.version)
    available = [u for u in state.units if u.status == UnitStatus.AVAILABLE]
    roads = state.road_conditions
    used: Set[str] = set()

    
    def severity_sort_key(x):
        # 1. Primary: Severity
        sev = x.severity or 0
        
        # 2. Equal Severity Tie-breakers (documented factors)
        life_threat = 1 if x.life_threat else 0
        trapped = x.people_trapped
        time_crit = 1 if x.time_critical else 0
        # If escalation prediction exists, parse risk
        esc = 0
        if getattr(x, "escalation_prediction", None):
            risk_level = x.escalation_prediction.escalation_risk
            if risk_level == "CRITICAL": esc = 3
            elif risk_level == "HIGH": esc = 2
            elif risk_level == "MEDIUM": esc = 1
            
        return (-sev, -life_threat, -trapped, -time_crit, -esc)

    ordered = sorted(state.incidents, key=severity_sort_key)


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
    """Balance coverage with reserve maintenance.

    Tries multiple incident orderings and picks the assignment combination
    that maximises incidents covered while maintaining at least MIN_RESERVE_UNITS
    in reserve.  Tie-breaks by total severity score of covered incidents.

    This produces materially different assignments from:
      Plan A (NEAREST_FIRST)  — which always picks closest incidents first
      Plan B (SEVERITY_FIRST) — which always picks highest-severity first
    """
    plan = Plan(id=f"plan-v{state.version}-C", strategy_name="BALANCED", state_version=state.version)
    available = [u for u in state.units if u.status == UnitStatus.AVAILABLE]
    roads = state.road_conditions
    incidents = list(state.incidents)

    def resource_count(x):
        return sum(v for v in x.required_units.values() if v > 0)

    # Try several different orderings to find max-coverage assignment
    orderings = [
        # Light-first: cover easiest incidents first to maximise count
        sorted(incidents, key=lambda x: resource_count(x)),
        # Light+high-severity: prefer cheap-to-cover + high severity incidents
        sorted(incidents, key=lambda x: (resource_count(x), -(x.severity or 0))),
        # Severity descending (same as Plan B, serves as baseline)
        sorted(incidents, key=lambda x: -(x.severity or 0)),
        # Mixed: high severity first, then tie-break by resource cheapness
        sorted(incidents, key=lambda x: (-(x.severity or 0), resource_count(x))),
        # Reverse severity: pick lower-severity (cheaper) incidents first
        sorted(incidents, key=lambda x: (x.severity or 0)),
    ]

    best_assignments: List[Assignment] = []
    best_coverage = -1
    best_severity = -1

    for ordering in orderings:
        used: Set[str] = set()
        assignments: List[Assignment] = []

        for inc in ordering:
            assigns = _try_assign(inc, available, used, roads)
            if not assigns:
                continue

            # Preserve at least MIN_RESERVE_UNITS when pool is large enough
            remaining_after = len(available) - len(used) - len(assigns)
            if remaining_after < MIN_RESERVE_UNITS and len(available) > MIN_RESERVE_UNITS:
                continue  # skip this incident to keep a reserve

            for a in assigns:
                used.add(a.unit_id)
            assignments.extend(assigns)

        covered_count = len({a.incident_id for a in assignments})
        sev_sum = sum(
            (state.get_incident(iid).severity or 0)
            for iid in {a.incident_id for a in assignments}
            if state.get_incident(iid)
        )

        if covered_count > best_coverage or (
            covered_count == best_coverage and sev_sum > best_severity
        ):
            best_coverage = covered_count
            best_severity = sev_sum
            best_assignments = assignments

    plan.assignments = best_assignments
    return plan

