from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class ImpactAnalysis(BaseModel):
    trigger: str
    affected_allocations: List[Dict[str, str]]
    unaffected_allocations: List[Dict[str, str]]
    coverage_lost: List[str]
    unavailable_resources: List[str]
    new_resource_requirements: List[str]
    replan_required: bool

def analyze_impact(state: Any, trigger: str, event_type: str, payload: dict) -> ImpactAnalysis:
    """
    Deterministically analyze the impact of a disruption BEFORE replanning.
    """
    analysis = ImpactAnalysis(
        trigger=trigger,
        affected_allocations=[],
        unaffected_allocations=[],
        coverage_lost=[],
        unavailable_resources=[],
        new_resource_requirements=[],
        replan_required=False
    )

    # Gather existing active missions/assignments
    for mission in state.active_missions.values():
        analysis.unaffected_allocations.append({
            "incident_id": mission.incident_id,
            "unit_id": mission.unit_id
        })

    if event_type == "unit_failure":
        unit_id = payload.get("unit_id")
        if unit_id:
            analysis.unavailable_resources.append(unit_id)
            analysis.replan_required = True
            
            # Find if this unit was allocated
            affected_mission = None
            for mission in state.active_missions.values():
                if mission.unit_id == unit_id:
                    affected_mission = mission
                    break
            
            if affected_mission:
                alloc = {"incident_id": affected_mission.incident_id, "previous_unit": unit_id}
                analysis.affected_allocations.append(alloc)
                analysis.coverage_lost.append(affected_mission.incident_id)
                # Remove from unaffected
                analysis.unaffected_allocations = [
                    a for a in analysis.unaffected_allocations 
                    if not (a.get("unit_id") == unit_id and a.get("incident_id") == affected_mission.incident_id)
                ]

    elif event_type == "road_block":
        road_id = payload.get("road_id")
        if road_id:
            # We don't always replan for road blocks if we can reroute, but it's an impact
            analysis.replan_required = True
            for mission in list(state.active_missions.values()):
                route = state.get_mission_route(mission.mission_id)
                if route and road_id in route.road_segments:
                    alloc = {"incident_id": mission.incident_id, "previous_unit": mission.unit_id, "reason": f"Route blocked at {road_id}"}
                    analysis.affected_allocations.append(alloc)
                    # We might not lose coverage if rerouted, but it's affected
                    # analysis.coverage_lost.append(mission.incident_id)
                    analysis.unaffected_allocations = [
                        a for a in analysis.unaffected_allocations 
                        if not (a.get("unit_id") == mission.unit_id and a.get("incident_id") == mission.incident_id)
                    ]

    elif event_type == "new_incident":
        analysis.replan_required = True
        inc_id = payload.get("incident_id")
        if inc_id:
            req_units = payload.get("required_units", {})
            for r_type, count in req_units.items():
                analysis.new_resource_requirements.append(f"{count}x {r_type} for {inc_id}")

    return analysis
