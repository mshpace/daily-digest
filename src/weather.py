from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Tuple

import requests

from .utils import log


def zip_to_latlon(zip_code: str) -> Tuple[float, float, str]:
    """ZIP -> (lat, lon, 'Place, ST') via Zippopotam.us"""
    r = requests.get(f"https://api.zippopotam.us/us/{zip_code}", timeout=25)
    r.raise_for_status()
    data = r.json()
    place = data["places"][0]
    lat = float(place["latitude"])
    lon = float(place["longitude"])
    name = f'{place["place name"]}, {place["state abbreviation"]}'
    return lat, lon, name


def forecast_open_meteo(lat: float, lon: float, days: int) -> Dict[str, Any]:
    """Daily forecast (max/min + precip prob) via Open-Meteo."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "auto",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "forecast_days": days,
    }
    r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=25)
    r.raise_for_status()
    return r.json()


def nws_alerts(lat: float, lon: float) -> List[Dict[str, Any]]:
    """Active NWS alerts for a point."""
    r = requests.get(
        "https://api.weather.gov/alerts/active",
        params={"point": f"{lat},{lon}"},
        headers={"User-Agent": "daily-digest/1.0 (contact: you@example.com)"},
        timeout=25,
    )
    r.raise_for_status()
    data = r.json()
    feats = data.get("features", []) or []
    out: List[Dict[str, Any]] = []
    for f in feats:
        p = f.get("properties", {}) or {}
        out.append(
            {
                "event": p.get("event") or "",
                "severity": p.get("severity") or "",
                "headline": p.get("headline") or "",
                "expires": p.get("expires") or "",
                "uri": p.get("uri") or "",
            }
        )
    return out


def build_weather_section(cfg: Dict[str, Any], now: dt.datetime) -> Dict[str, Any]:
    zips: List[str] = cfg["weather"]["zips"]
    days = int(cfg["weather"].get("forecast_days", 7))
    include_alerts = bool(cfg["weather"].get("include_alerts", True))

    cards = []
    for z in zips:
        try:
            lat, lon, place = zip_to_latlon(z)
            fc = forecast_open_meteo(lat, lon, days)
            daily = fc.get("daily", {}) or {}

            dates = daily.get("time", []) or []
            tmax = daily.get("temperature_2m_max", []) or []
            tmin = daily.get("temperature_2m_min", []) or []
            pop = daily.get("precipitation_probability_max", []) or []

            table = []
            for i in range(min(days, len(dates))):
                table.append(
                    {
                        "date": dates[i],
                        "high": tmax[i] if i < len(tmax) else None,
                        "low": tmin[i] if i < len(tmin) else None,
                        "rain_chance": pop[i] if i < len(pop) else None,
                    }
                )

            alerts = nws_alerts(lat, lon) if include_alerts else []
            cards.append({"zip": z, "place": place, "table": table, "alerts": alerts})
        except Exception as e:
            log(f"[weather] zip {z} failed: {e}")
            cards.append({"zip": z, "place": "", "table": [], "alerts": [], "error": str(e)})

    return {
        "id": "weather",
        "title": "Weather (Today + 7-Day + Alerts)",
        "type": "weather",
        "data": {"cards": cards},
    }
