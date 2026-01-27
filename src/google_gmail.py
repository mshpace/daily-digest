from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .utils import log, safe_int

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


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


def _header(headers: List[Dict[str, str]], name: str) -> str:
    target = name.lower()
    for h in headers:
        if (h.get("name") or "").lower() == target:
            return h.get("value") or ""
    return ""


def _gmail_query() -> str:
    # Inbox only, last 48h
    return "in:inbox newer_than:2d"


def _has_question(text: str, extra_phrases: List[str]) -> bool:
    t = (text or "").lower()
    if "?" in t:
        return True
    for p in extra_phrases:
        if (p or "").lower() in t:
            return True
    return False


def build_gmail_section(cfg: Dict[str, Any], now: dt.datetime) -> Dict[str, Any]:
    inbox_cfg = cfg.get("inbox_summary")
