import json
from backend.route import build_graph, find_nearest_node, calculate_routes
from backend.models import RoadCondition

def load_data():
    with open('data/roads.json') as f:
        roads = json.load(f)
    with open('data/units.json') as f:
        units = json.load(f)
    with open('data/incidents.json') as f:
        incidents = json.load(f)
        
    road_conditions = []
    for r in roads:
        road_conditions.append(RoadCondition(**r))
        
    return road_conditions, units, incidents
    
def test_routing():
    roads, units, incidents = load_data()
    graph = build_graph(roads)
    
    nodes = set(graph.keys())
    
    print(f"ROAD NODES: {len(nodes)}")
    print(f"ROAD EDGES: {len(roads)}")
    
    # Check components
    def bfs(start):
        q = [start]
        visited = set([start])
        while q:
            curr = q.pop(0)
            for edge in graph[curr]:
                if edge["node"] not in visited:
                    visited.add(edge["node"])
                    q.append(edge["node"])
        return visited
        
    components = 0
    unvisited = set(nodes)
    while unvisited:
        start = unvisited.pop()
        comp = bfs(start)
        unvisited -= comp
        components += 1
        
    print(f"CONNECTED COMPONENTS: {components}")
    
    # 1 & 2
    units_conn = sum(1 for u in units if find_nearest_node(u['latitude'], u['longitude'], graph))
    inc_conn = sum(1 for i in incidents if find_nearest_node(i['latitude'], i['longitude'], graph))
    print(f"UNITS CONNECTED: {units_conn}/{len(units)}")
    print(f"INCIDENTS CONNECTED: {inc_conn}/{len(incidents)}")
    
    # 3, 4, 5
    def get_unit(uid): return next(u for u in units if u['id'] == uid)
    def get_inc(iid): return next(i for i in incidents if i['id'] == iid)
    
    inc1 = get_inc('INC-001')
    
    for uid in ['AMB-01', 'AMB-02', 'AMB-03']:
        u = get_unit(uid)
        routes = calculate_routes(u['latitude'], u['longitude'], inc1['latitude'], inc1['longitude'], roads)
        assert len(routes) > 0 and routes[0].status == "FEASIBLE", f"Failed route {uid} -> INC-001"
        
    # 6: Two feasible routes
    u2 = get_unit('AMB-02')
    routes = calculate_routes(u2['latitude'], u2['longitude'], inc1['latitude'], inc1['longitude'], roads)
    assert len(routes) >= 2, "Failed to find alternative route"
    print(f"ALTERNATIVE ROUTES AVAILABLE: {'YES' if len(routes) >= 2 else 'NO'}")
    
    # 7: Block primary road
    primary_route = routes[0]
    first_road = primary_route.road_segments[0]
    
    for r in roads:
        if r.id == first_road:
            r.blocked = True
            
    routes_after = calculate_routes(u2['latitude'], u2['longitude'], inc1['latitude'], inc1['longitude'], roads)
    assert first_road not in routes_after[0].road_segments, "Blocked road was still used!"
    assert routes_after[0].status == "FEASIBLE", "Did not find alternative route after block"
    
    # 8: Block ALL roads
    for r in roads:
        r.blocked = True
    routes_all_blocked = calculate_routes(u2['latitude'], u2['longitude'], inc1['latitude'], inc1['longitude'], roads)
    assert routes_all_blocked[0].status == "NO_FEASIBLE_ROUTE", "Route found when all roads blocked"
    
    print("ALL TESTS PASSED")

if __name__ == '__main__':
    test_routing()
