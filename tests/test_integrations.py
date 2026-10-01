import pytest
import json
import urllib.request
import urllib.error
from unittest.mock import patch, MagicMock
from backend.integrations.weather import get_weather
from backend.integrations.ors import get_external_route
import os

@patch('urllib.request.urlopen')
def test_weather_success(mock_urlopen):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps({
        "current": {
            "temperature_2m": 25.0,
            "precipitation": 1.5,
            "rain": 1.5,
            "weather_code": 61,
            "wind_speed_10m": 15.0
        }
    }).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    ctx = get_weather(21.0, 72.0)
    assert ctx.available is True
    assert ctx.source_type == "EXTERNAL"
    assert ctx.precipitation == 1.5
    assert ctx.weather_code == 61

@patch('urllib.request.urlopen')
def test_weather_failure(mock_urlopen):
    mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
    ctx = get_weather(21.0, 72.0)
    assert ctx.available is False
    assert ctx.source_type == "FALLBACK"

@patch.dict(os.environ, {"ORS_API_KEY": "dummy_key"})
@patch('urllib.request.urlopen')
def test_ors_success(mock_urlopen):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps({
        "features": [
            {
                "properties": {
                    "summary": {
                        "distance": 15000,
                        "duration": 1200
                    }
                },
                "geometry": "dummy_geom"
            }
        ]
    }).encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    res = get_external_route(21.0, 72.0, 21.1, 72.1)
    assert res.available is True
    assert res.distance_km == 15.0
    assert res.duration_min == 20.0
    assert res.source_type == "EXTERNAL"

@patch.dict(os.environ, clear=True)
def test_ors_missing_key():
    res = get_external_route(21.0, 72.0, 21.1, 72.1)
    assert res.available is False
    assert res.source_type == "FALLBACK"
    assert "Missing ORS_API_KEY" in res.error_reason

@patch.dict(os.environ, {"ORS_API_KEY": "dummy_key"})
@patch('urllib.request.urlopen')
def test_ors_failure(mock_urlopen):
    mock_urlopen.side_effect = urllib.error.URLError("Timeout")
    res = get_external_route(21.0, 72.0, 21.1, 72.1)
    assert res.available is False
    assert res.source_type == "FALLBACK"
