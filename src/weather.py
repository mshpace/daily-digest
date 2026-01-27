from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

import requests

from .utils import log, safe_int


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


def _fmt_day_label(date_str: str) -> str:
    d = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
    return d.strftime("%a %m/%d")  # Tue 01/27


def _to_int(x: Any) -> Optional[int]:
    try:
        if x is None:
            return None
        return int(round(float(x)))
    except Exception:
        return None


def build_weather_section(cfg: Dict[str, Any], now: dt.datetime) -> Dict[str, Any]:
    """
    Builds ONE table across multiple zips.

    data = {
      "locations": [{"zip":"35209","label":"35209 (BHM)"}, ...],
      "rows": [
        {"day":"Tue 01/27", "cells":[{"low":13,"high":26,"rain":9}, ...]},
        ...
      ],
      "alerts": [...]
    }
    """
    try:
        weather_cfg = cfg.get("weather", {}) or {}
        zips: List[str] = weather_cfg.get("zips", []) or []
        days = safe_int(weather_cfg.get("forecast_days", 7), 7)
        labels_map: Dict[str, str] = weather_cfg.get("labels", {}) or {}

        if not zips:
            raise RuntimeError("Missing config: weather.zips (add a top-level 'weather:' block in config.yaml)")

        per_zip: List[Dict[str, Any]] = []
        locations: List[Dict[str, str]] = []

        for z in zips:
            z_str = str(z)
            try:
                geo = _zip_to_latlon(z_str)
                lat = float(geo["latitude"])
                lon = float(geo["longitude"])

                place_name = (geo.get("name") or "").strip()
                pretty_label = labels_map.get(z_str) or place_name or z_str
                label = f"{z_str} ({pretty_label})" if pretty_label != z_str else z_str

                forecast = _fetch_forecast(lat, lon, days=days)
                daily = forecast.get("daily", {}) or {}

                dates = daily.get("time", []) or []
                highs = daily.get("temperature_2m_max", []) or []
                lows = daily.get("temperature_2m_min", []) or []
                rains = daily.get("precipitation_probability_max", []) or []

                series = []
                n = min(len(dates), len(highs), len(lows), len(rains))
                for i in range(n):
                    series.append(
                        {
                            "date": dates[i],
                            "high": _to_int(highs[i]),
                            "low": _to_int(lows[i]),
                            "rain": _to_int(rains[i]),
                        }
                    )

                locations.append({"zip": z_str, "label": label})
                per_zip.append({"zip": z_str, "label": label, "series": series})

            except Exception as e:
                log(f"[weather] zip {z_str} failed: {e}")
                label = f"{z_str} ({labels_map.get(z_str)})" if labels_map.get(z_str) else z_str
                locations.append({"zip": z_str, "label": label})
                per_zip.append({"zip": z_str, "label": label, "series": [], "error": str(e)})

        # Use date order from first successful series
        date_order: List[str] = []
        for p in per_zip:
            if p.get("series"):
                date_order = [x["date"] for x in p["series"]]
                break
        if not date_order:
            s = set()
            for p in per_zip:
                for x in p.get("series", []):
                    s.add(x["date"])
            date_order = sorted(s)

        rows: List[Dict[str, Any]] = []
        for dstr in date_order[:days]:
            cells: List[Dict[str, Any]] = []
            for p in per_zip:
                found = None
                for x in p.get("series", []):
                    if x["date"] == dstr:
                        found = x
                        break
                if found:
                    cells.append({"low": found.get("low"), "high": found.get("high"), "rain": found.get("rain")})
                else:
                    cells.append({"low": None, "high": None, "rain": None})
            rows.append({"day": _fmt_day_label(dstr), "cells": cells})

        alerts: List[Dict[str, Any]] = []
        for p in per_zip:
            if p.get("error"):
                alerts.append({"zip": p["zip"], "items": [f"Weather lookup error: {p['error']}"]})

        return {"id": "weather", "title": "Weather", "type": "weather", "data": {"locations": locations, "rows": rows, "alerts": alerts}}

    except Exception as e:
        log(f"[weather] build section failed: {e}")
        return {"id": "weather_error", "title": "Weather (Error)", "type": "error", "data": {"error": str(e)}}
