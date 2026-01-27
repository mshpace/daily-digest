from __future__ import annotations

import datetime as dt
from typing import Any, Dict


def build_calendar_section_outlook(cfg: Dict[str, Any], now: dt.datetime) -> Dict[str, Any]:
    days_ahead = int(cfg.get("calendar", {}).get("days_ahead", 21))
    return {
        "id": "events_outlook",
        "title": f"Events (Outlook) — Not configured yet (Next {days_ahead} Days)",
        "type": "events",
        "data": {"events": [], "days_ahead": days_ahead},
    }
