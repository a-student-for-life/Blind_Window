"""Hourly cloud-cover forecasts from Open-Meteo (up to 16 days ahead)."""
from datetime import datetime, timezone

from . import http

API = "https://api.open-meteo.com/v1/forecast"


def hourly_cloud(lat, lon):
    resp = http.get_json(API, {"latitude": lat, "longitude": lon, "hourly": "cloud_cover",
                               "forecast_days": 16, "timezone": "GMT"}, cache=False)
    h = resp.get("hourly", {})
    return {datetime.fromisoformat(t).replace(tzinfo=timezone.utc): v
            for t, v in zip(h.get("time", []), h.get("cloud_cover", [])) if v is not None}


def at(series, when):
    """Cloud cover at the nearest forecast hour, or None if outside the forecast."""
    if not series:
        return None
    nearest = min(series, key=lambda t: abs((t - when).total_seconds()))
    if abs((nearest - when).total_seconds()) > 3600:
        return None
    return series[nearest]
