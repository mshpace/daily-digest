from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

import requests

from .utils import log, safe_int


def _get_place_name(lat: float, lon: float) -> str:
    # Best-effort reverse geocode using Open-Meteo's geocoding endpoint (free)
    try:
        r = requests.get(
            "https://geocoding-api.open-meteo.com/v1/reverse",
            params={"latitude": lat, "longitude": lon, "language": "en"},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json() or {}
        results = data.get("results", []) or []
        if results:
            x = results[0]
            parts = [x.get("name"), x.get("admin1"), x.get("country")]
            return ", ".join([p for p in parts if p])
    except Exception:
        pass
    return ""


def _zip_to_latlon(zip_code: str) -> Dict[str, Any]:
    r = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": zip_code, "count": 1, "language": "en", "format": "json"},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json() or {}
    results = data.get("results", []) or []
    if not results:
        raise RuntimeError(f"Unable to geocode zip {zip_code}")
    return results[0]


def _fetch_forecast(lat: float, lon: float, days: int) -> Dict[str, Any]:
    # Daily forecast + precipitation probability.
    # Note: alerts are not provided by Open-Meteo in all regions; we keep alerts best-effort.
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": days,
            "timezone": "auto",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json() or {}


def build_weather_section(cfg: Dict[str, Any], now: dt.datetime) -> Dict[str, Any]:
    """
    Returns a single section dict of type=weather.
    Never KeyErrors on missing config; returns an error section instead.
    """
    try:
        weather_cfg = cfg.get("weather", {}) or {}
        zips: List[str] = weather_cfg.get("zips", []) or []
        days = safe_int(weather_cfg.get("forecast_days", 7), 7)

        if not zips:
            raise RuntimeError("Missing config: weather.zips (add a top-level 'weather:' block in config.yaml)")

        cards: List[Dict[str, Any]] = []
        for z in zips:
            try:
                geo = _zip_to_latlon(str(z))
                lat = float(geo["latitude"])
                lon = float(geo["longitude"])
                place = geo.get("name") or _get_place_name(lat, lon)

                forecast = _fetch_forecast(lat, lon, days=days)
                daily = forecast.get("daily", {}) or {}

                dates = daily.get("time", []) or []
                highs = daily.get("temperature_2m_max", []) or []
                lows = daily.get("temperature_2m_min", []) or []
                rains = daily.get("precipitation_probability_max", []) or []

                table = []
                for i in range(min(len(dates), len(highs), len(lows), len(rains))):
                    table.append(
                        {
                            "date": dates[i],
                            "high": highs[i],
                            "low": lows[i],
                            "rain_chance": rains[i],
                        }
                    )

                cards.append(
                    {
                        "zip": str(z),
                        "place": place or "",
                        "table": table,
                        "alerts": [],  # placeholder; provider may not support alerts
                    }
                )
            except Exception as e:
                log(f"[weather] zip {z} failed: {e}")
                cards.append({"zip": str(z), "place": "", "table": [], "alerts": [], "error": str(e)})

        return {"id": "weather", "title": "Weather", "type": "weather", "data": {"cards": cards}}

    except Exception as e:
        log(f"[weather] build section failed: {e}")
        return {"id": "weather_error", "title": "Weather (Error)", "type": "error", "data": {"error": str(e)}}
