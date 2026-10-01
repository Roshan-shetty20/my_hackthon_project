from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.models import UnitStatus

class ImpactAnalysis(BaseModel):
    trigger: str
    affected_allocations: List[Dict[str, str]] = Field(default_factory=list)
    unaffected_allocations: List[Dict[str, str]] = Field(default_factory=list)
    coverage_lost: List[str] = Field(default_factory=list)
    unavailable_resources: List[str] = Field(default_factory=list)
    new_resource_requirements: List[str] = Field(default_factory=list)
    replan_required: bool = False
    
    # Global Conflict
    global_demand: Dict[str, int] = Field(default_factory=dict)
    global_available: Dict[str, int] = Field(default_factory=dict)
    resource_shortfalls: Dict[str, int] = Field(default_factory=dict)
    
    affected_incidents: List[str] = Field(default_factory=list)

def analyze_global_impact(state: Any, events: List[Any], trigger: str) -> ImpactAnalysis:
    """
    Deterministically analyze the impact of a batch of events AFTER state has been updated,
    but BEFORE replanning.
    """
    analysis = ImpactAnalysis(trigger=trigger)

    # 1. Determine Unaffected Allocations
    for mission in state.active_missions.values():
        analysis.unaffected_allocations.append({
            "incident_id": mission.incident_id,
            "unit_id": mission.unit_id
        })

    # 2. Process events to find direct impacts
    for ev in events:
        if ev.event_type == "unit_failure":
            unit_id = ev.payload.get("unit_id")
            if unit_id:
                analysis.unavailable_resources.append(unit_id)
                analysis.replan_required = True
                
                # Check if this unit was in an active mission
                affected_mission = None
                for mission in state.active_missions.values():
                    if mission.unit_id == unit_id:
                        affected_mission = mission
                        break
                
                if affected_mission:
                    alloc = {"incident_id": affected_mission.incident_id, "previous_unit": unit_id}
                    analysis.affected_allocations.append(alloc)
                    analysis.coverage_lost.append(affected_mission.incident_id)
                    if affected_mission.incident_id not in analysis.affected_incidents:
                        analysis.affected_incidents.append(affected_mission.incident_id)
                    
                    analysis.unaffected_allocations = [
                        a for a in analysis.unaffected_allocations 
                        if not (a.get("unit_id") == unit_id and a.get("incident_id") == affected_mission.incident_id)
                    ]

        elif ev.event_type == "road_block":
            road_id = ev.payload.get("road_id")
            if road_id:
                analysis.replan_required = True
                for mission in list(state.active_missions.values()):
                    route = state.get_mission_route(mission.mission_id)
                    if route and road_id in route.road_segments:
                        alloc = {"incident_id": mission.incident_id, "previous_unit": mission.unit_id, "reason": f"Route blocked at {road_id}"}
                        analysis.affected_allocations.append(alloc)
                        if mission.incident_id not in analysis.affected_incidents:
                            analysis.affected_incidents.append(mission.incident_id)
                        
                        analysis.unaffected_allocations = [
                            a for a in analysis.unaffected_allocations 
                            if not (a.get("unit_id") == mission.unit_id and a.get("incident_id") == mission.incident_id)
                        ]

        elif ev.event_type == "new_incident":
            analysis.replan_required = True
            inc_id = ev.payload.get("incident_id") or ev.payload.get("id")
            if inc_id:
                if inc_id not in analysis.affected_incidents:
                    analysis.affected_incidents.append(inc_id)
                req_units = ev.payload.get("required_units", {})
                for r_type, count in req_units.items():
                    analysis.new_resource_requirements.append(f"{count}x {r_type} for {inc_id}")

    # 3. Global Resource Conflict Analysis
    # Tally all required units across ALL unresolved incidents
    for inc in state.incidents:
        if inc.status != "RESOLVED":
            for r_type, count in inc.required_units.items():
                analysis.global_demand[r_type] = analysis.global_demand.get(r_type, 0) + count

    # Tally available/working units
    for unit in state.units:
        if unit.status not in [UnitStatus.UNAVAILABLE, UnitStatus.BROKEN_DOWN]:
            u_type = unit.type.value if hasattr(unit.type, "value") else str(unit.type)
            analysis.global_available[u_type] = analysis.global_available.get(u_type, 0) + 1

    # Find shortfalls
    for r_type, demand in analysis.global_demand.items():
        avail = analysis.global_available.get(r_type, 0)
        if demand > avail:
            analysis.resource_shortfalls[r_type] = demand - avail
            analysis.replan_required = True

    return analysis

# Keeping original analyze_impact for backward compatibility with existing tests
def analyze_impact(state: Any, trigger: str, event_type: str, payload: dict) -> ImpactAnalysis:
    class MockEvent:
        def __init__(self, t, p):
            self.event_type = t
            self.payload = p
    return analyze_global_impact(state, [MockEvent(event_type, payload)], trigger)
