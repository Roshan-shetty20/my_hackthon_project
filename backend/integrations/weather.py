"""
Crisis Command — Weather Integration (Stub)

Phase 2: Fetch real-time weather from Open-Meteo to adjust
severity and route planning.  MVP uses no weather data.
"""


def get_weather(lat: float, lon: float) -> dict:
    """Stub: returns clear weather. Phase 2 will call Open-Meteo."""
    return {"condition": "clear", "wind_kmh": 0, "rain_mm": 0}
