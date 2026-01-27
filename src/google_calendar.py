from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .utils import log

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def _creds_from_env() -> Credentials:
    import os
    return Credentials(
        None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=SCOPES,
    )


def build_calendar_section_google(cfg: Dict[str, Any], now: dt.datetime) -> Dict[str, Any]:
    days_ahead = int(cfg.get("calendar", {}).get("days_ahead", 21))
    time_min = now.isoformat()
    time_max = (now + dt.timedelta(days=days_ahead)).isoformat()

    creds = _creds_from_env()
    svc = build("calendar", "v3", credentials=creds, cache_discovery=False)

    cals = svc.calendarList().list().execute().get("items", []) or []
    all_events: List[Dict[str, Any]] = []

    for cal in cals:
        cal_id = cal["id"]
        cal_name = cal.get("summary", cal_id)
        try:
            events = (
                svc.events()
                .list(
                    calendarId=cal_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=2500,
                )
                .execute()
                .get("items", [])
                or []
            )
        except Exception as e:
            log(f"[calendar] calendar '{cal_name}' fetch failed: {e}")
            continue

        for e in events:
            start = e.get("start", {}).get("dateTime") or e.get("start", {}).get("date") or ""
            end = e.get("end", {}).get("dateTime") or e.get("end", {}).get("date") or ""
            all_events.append(
                {
                    "calendar": cal_name,
                    "summary": e.get("summary", "(No title)"),
                    "start": start,
                    "end": end,
                    "location": e.get("location"),
                    "htmlLink": e.get("htmlLink"),
                }
            )

    all_events.sort(key=lambda x: x.get("start", "") or "")
    return {
        "id": "events",
        "title": f"Events (Next {days_ahead} Days — All Google Calendars)",
        "type": "events",
        "data": {"events": all_events, "days_ahead": days_ahead},
    }
