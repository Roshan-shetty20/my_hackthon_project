"""
Crisis Command — OpenRouteService Integration

Provides external route enrichment.
Does not replace Dijkstra as the operational routing engine.
"""

import os
import urllib.request
import urllib.error
import json
from backend.models import ExternalRouteResult

def get_external_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float, timeout_sec: float = 3.0) -> ExternalRouteResult:
    """Fetch external route context from OpenRouteService."""
    api_key = os.environ.get("ORS_API_KEY")
    
    res = ExternalRouteResult(
        source="OpenRouteService",
        source_type="EXTERNAL",
        available=False
    )
    
    if not api_key:
        res.error_reason = "Missing ORS_API_KEY"
        res.source_type = "FALLBACK"
        return res
        
    # OpenRouteService uses lon,lat ordering
    url = f"https://api.openrouteservice.org/v2/directions/driving-car?start={start_lon},{start_lat}&end={end_lon},{end_lat}"
    
    try:
        req = urllib.request.Request(url, headers={
            'Authorization': api_key,
            'User-Agent': 'CrisisCommand/1.0',
            'Accept': 'application/json'
        })
        with urllib.request.urlopen(req, timeout=timeout_sec) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                features = data.get("features", [])
                if features:
                    props = features[0].get("properties", {})
                    summary = props.get("summary", {})
                    
                    res.distance_km = float(summary.get("distance", 0.0)) / 1000.0
                    res.duration_min = float(summary.get("duration", 0.0)) / 60.0
                    res.geometry = features[0].get("geometry")
                    res.available = True
                else:
                    res.error_reason = "No route features found"
                    res.source_type = "FALLBACK"
    except Exception as e:
        res.error_reason = f"API Error: {str(e)}"
        res.source_type = "FALLBACK"
        
    return res
