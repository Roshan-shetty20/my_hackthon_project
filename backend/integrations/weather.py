"""
Crisis Command — Weather Integration

Uses Open-Meteo Forecast API.
"""

import urllib.request
import urllib.error
import json
from datetime import datetime
from backend.models import WeatherContext

def get_weather(lat: float, lon: float, timeout_sec: float = 3.0) -> WeatherContext:
    """Fetch external weather context from Open-Meteo."""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,precipitation,rain,weather_code,wind_speed_10m"
    
    ctx = WeatherContext(
        latitude=lat,
        longitude=lon,
        timestamp=datetime.utcnow().isoformat(),
        source="Open-Meteo",
        source_type="EXTERNAL",
        available=False
    )
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'CrisisCommand/1.0'})
        with urllib.request.urlopen(req, timeout=timeout_sec) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                current = data.get("current", {})
                
                ctx.precipitation = float(current.get("precipitation", 0.0))
                ctx.rain = float(current.get("rain", 0.0))
                ctx.wind_speed = float(current.get("wind_speed_10m", 0.0))
                ctx.weather_code = int(current.get("weather_code", 0))
                ctx.available = True
    except Exception:
        ctx.source_type = "FALLBACK"
        
    return ctx
