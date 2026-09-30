import pytest
from backend.state import CrisisState
from backend.models import Unit, Incident, RoadCondition, UnitStatus, RouteOption
from backend.route import calculate_routes

@pytest.fixture
def base_state():
    state = CrisisState()
    state.units.append(Unit(id="U1", type="ambulance", status=UnitStatus.AVAILABLE, latitude=21.1850, longitude=72.8250))
    state.incidents.append(Incident(id="I1", type="Medical", location="Test", latitude=21.1950, longitude=72.8190))
    # Add a mock route
    state.road_conditions.append(RoadCondition(
        id="R1", name="Road 1", from_lat=21.1850, from_lon=72.8250, to_lat=21.1950, to_lon=72.8190, distance_km=2.0
    ))
    return state

def test_dispatch_workflow(base_state):
    # 1. RouteOption integration
    routes = calculate_routes(
        base_state.units[0].latitude, base_state.units[0].longitude,
        base_state.incidents[0].latitude, base_state.incidents[0].longitude,
        base_state.road_conditions
    )
    assert len(routes) > 0
    primary_route = routes[0]
    assert isinstance(primary_route, RouteOption)
    
    # 2 & 3. Dispatch creates DispatchMission, Unit changes AVAILABLE -> EN_ROUTE
    initial_version = base_state.version
    base_state.dispatch_unit("U1", "I1", primary_route)
    
    assert len(base_state.active_missions) == 1
    mission_id = list(base_state.active_missions.keys())[0]
    mission = base_state.active_missions[mission_id]
    
    assert mission.unit_id == "U1"
    assert mission.status == "EN_ROUTE"
    assert base_state.units[0].status == UnitStatus.EN_ROUTE
    assert base_state.version == initial_version + 1 # 10. State version remains consistent
    
    # 9. Action Log records dispatch
    assert any("DISPATCHED" in entry.action for entry in base_state.action_log)
    
    # 4. Step advances position
    base_state.advance_missions(step_percent=50.0)
    assert mission.progress_percent == 50.0
    assert mission.eta_minutes < primary_route.eta_minutes
    assert base_state.version == initial_version + 2
    
    # 5. Arrival changes EN_ROUTE -> ON_SCENE
    base_state.advance_missions(step_percent=60.0)
    assert mission.progress_percent == 100.0
    assert mission.status == "ON_SCENE"
    assert base_state.units[0].status == UnitStatus.ON_SCENE

def test_dynamic_rerouting(base_state):
    # Setup multiple roads for alternative
    base_state.road_conditions.append(RoadCondition(
        id="R2", name="Road 2", from_lat=21.1850, from_lon=72.8250, to_lat=21.1950, to_lon=72.8190, distance_km=3.0
    ))
    routes = calculate_routes(
        base_state.units[0].latitude, base_state.units[0].longitude,
        base_state.incidents[0].latitude, base_state.incidents[0].longitude,
        base_state.road_conditions
    )
    
    base_state.dispatch_unit("U1", "I1", routes[0])
    
    # 6 & 7. Blocked active route triggers recalculation & alternative route selected
    for r in base_state.road_conditions:
        if r.id == routes[0].road_segments[0]:
            r.blocked = True
    base_state.handle_road_block(routes[0].road_segments[0])
    
    mission = list(base_state.active_missions.values())[0]
    assert mission.status == "EN_ROUTE" # Found an alternative, so resumed!
    new_route = base_state.get_mission_route(mission.mission_id)
    assert new_route.road_segments[0] == "R2" # Uses the alternative road now!
    assert "ROUTE RECALCULATED" in base_state.action_log[-1].action
    
    # 8. No alternative produces NO_FEASIBLE_ROUTE
    base_state.road_conditions[1].blocked = True # Block the alternative too
    base_state.handle_road_block(mission.get_mission_route(mission.mission_id) if hasattr(mission, 'get_mission_route') else "R2") # Trigger the block manually
    # Actually wait, handle_road_block takes road_id, the new mission is using R2.
    # Let's just pass "R2"
    base_state.handle_road_block("R2")
    
    assert mission.status == "INTERRUPTED"
    assert "NO FEASIBLE ROUTE" in base_state.action_log[-1].action

