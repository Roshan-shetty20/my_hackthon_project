"""
Crisis Command — OpenStreetMap Integration (Stub)

Phase 2: Replace haversine ETA with real road-network routing
via OSRM or Valhalla.  MVP uses deterministic local simulation.
"""


def get_route(lat1: float, lon1: float, lat2: float, lon2: float) -> dict:
    """Stub: returns empty route data. Phase 2 will call OSRM."""
    return {"distance_km": 0, "duration_min": 0, "geometry": []}
