"""
Crisis Command — Route and ETA Calculation

Phase 2 implementation uses deterministic graph-based routing (Dijkstra)
over known road segments. Connects units and incidents to the nearest
graph node.
"""

import math
import heapq
from typing import List, Optional, Tuple, Dict, Any

from backend.models import RoadCondition, RouteOption

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AVERAGE_SPEED_KMH = 40.0
EARTH_RADIUS_KM = 6371.0


# ---------------------------------------------------------------------------
# Distance
# ---------------------------------------------------------------------------

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Routing Core
# ---------------------------------------------------------------------------

def build_graph(road_conditions: List[RoadCondition]) -> Dict[Tuple[float, float], List[Dict[str, Any]]]:
    """Builds an adjacency list graph from road conditions."""
    graph = {}
    for r in road_conditions:
        u = (round(r.from_lat, 5), round(r.from_lon, 5))
        v = (round(r.to_lat, 5), round(r.to_lon, 5))
        
        if u not in graph: graph[u] = []
        if v not in graph: graph[v] = []
        
        if r.blocked:
            continue
            
        dist = r.distance_km if r.distance_km > 0 else haversine_km(u[0], u[1], v[0], v[1])
        speed = r.speed_kmh if r.speed_kmh > 0 else AVERAGE_SPEED_KMH
        cost = (dist / speed) * 60.0 + r.delay_minutes
        
        graph[u].append({"node": v, "road_id": r.id, "dist": dist, "cost": cost})
        graph[v].append({"node": u, "road_id": r.id, "dist": dist, "cost": cost}) # Assume bidirectional
        
    return graph

def find_nearest_node(lat: float, lon: float, graph: dict) -> Tuple[float, float]:
    """Finds the closest node in the graph."""
    if not graph:
        return (lat, lon)
    best_node = None
    best_dist = float('inf')
    for node in graph.keys():
        d = haversine_km(lat, lon, node[0], node[1])
        if d < best_dist:
            best_dist = d
            best_node = node
    return best_node

def dijkstra(start: Tuple[float, float], end: Tuple[float, float], graph: dict, penalized_edges: set = None) -> Optional[Dict]:
    """Runs Dijkstra's algorithm to find the shortest path (lowest cost)."""
    if start not in graph or end not in graph:
        return None
        
    import itertools
    counter = itertools.count()
    pq = [(0.0, next(counter), start, [])] # (cost, count, node, path_of_edges)
    visited = set()
    
    while pq:
        cost, _, current, path = heapq.heappop(pq)
        
        if current == end:
            return {"cost": cost, "path": path}
            
        if current in visited:
            continue
        visited.add(current)
        
        for edge in graph[current]:
            nxt = edge["node"]
            if nxt in visited:
                continue
                
            edge_cost = edge["cost"]
            if penalized_edges and edge["road_id"] in penalized_edges:
                edge_cost += 10.0 # 10 min penalty to find alternative
                
            new_path = path + [edge]
            heapq.heappush(pq, (cost + edge_cost, next(counter), nxt, new_path))
            
    return None

def calculate_routes(
    unit_lat: float,
    unit_lon: float,
    incident_lat: float,
    incident_lon: float,
    road_conditions: List[RoadCondition]
) -> List[RouteOption]:
    """
    Returns [fastest_route, alternative_route(optional)] or a BLOCKED route.
    """
    graph = build_graph(road_conditions)
    if not graph:
        return []
        
    start_node = find_nearest_node(unit_lat, unit_lon, graph)
    end_node = find_nearest_node(incident_lat, incident_lon, graph)
    
    # Connection distances from actual unit/incident location to the graph nodes
    conn_dist_start = haversine_km(unit_lat, unit_lon, start_node[0], start_node[1])
    conn_dist_end = haversine_km(incident_lat, incident_lon, end_node[0], end_node[1])
    conn_cost = ((conn_dist_start + conn_dist_end) / AVERAGE_SPEED_KMH) * 60.0
    
    res1 = dijkstra(start_node, end_node, graph)
    
    if not res1:
        return [RouteOption(
            route_id="NO_ROUTE",
            name="No Feasible Route",
            status="NO_FEASIBLE_ROUTE",
            blocked=True,
            reason="All paths are blocked or disjoint."
        )]
        
    def _build_option(res_dict, name, route_id):
        total_dist = conn_dist_start + conn_dist_end
        total_eta = conn_cost
        waypoints = [[unit_lat, unit_lon]]
        if conn_dist_start > 0.05:
            waypoints.append([start_node[0], start_node[1]])
            
        road_ids = []
        for edge in res_dict["path"]:
            total_dist += edge["dist"]
            total_eta += edge["cost"]
            road_ids.append(edge["road_id"])
            waypoints.append([edge["node"][0], edge["node"][1]])
            
        if conn_dist_end > 0.05:
            waypoints.append([incident_lat, incident_lon])
            
        return RouteOption(
            route_id=route_id,
            name=name,
            waypoints=waypoints,
            road_segments=road_ids,
            distance_km=round(total_dist, 2),
            eta_minutes=round(total_eta, 1),
            status="FEASIBLE"
        )
        
    r1 = _build_option(res1, "FASTEST FEASIBLE", "R-FAST")
    options = [r1]
    
    # Find alternative route by penalizing the primary route
    used_edges = set(r1.road_segments)
    if used_edges:
        res2 = dijkstra(start_node, end_node, graph, penalized_edges=used_edges)
        if res2 and res2["cost"] < 999: # Valid alternative found
            # Make sure it's actually different
            alt_edges = [e["road_id"] for e in res2["path"]]
            if alt_edges != r1.road_segments:
                # Recalculate true cost without the penalty for accurate reporting
                r2 = _build_option(res2, "ALTERNATIVE ROUTE", "R-ALT")
                # Subtract penalty that was added during Dijkstra
                penalty_sub = sum(10.0 for e in res2["path"] if e["road_id"] in used_edges)
                r2.eta_minutes = round(r2.eta_minutes - penalty_sub, 1)
                options.append(r2)
                
    return options

def calculate_eta(
    unit_lat: float,
    unit_lon: float,
    incident_lat: float,
    incident_lon: float,
    road_conditions: Optional[List[RoadCondition]] = None,
) -> float:
    """Wrapper to maintain compatibility with existing system."""
    if not road_conditions:
        dist = haversine_km(unit_lat, unit_lon, incident_lat, incident_lon)
        return round((dist / AVERAGE_SPEED_KMH) * 60, 1)
        
    options = calculate_routes(unit_lat, unit_lon, incident_lat, incident_lon, road_conditions)
    if options and options[0].status == "FEASIBLE":
        return options[0].eta_minutes
    return 999.0 # Effectively infinite ETA if blocked
