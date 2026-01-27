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
    inbox_cfg = cfg.get("inbox_summary", {}) or {}
    max_messages = safe_int(inbox_cfg.get("max_messages", 200), 200)
    extra_phrases = (inbox_cfg.get("detect_questions", {}) or {}).get("extra_phrases", []) or []

    creds = _creds_from_env()
    svc = build("gmail", "v1", credentials=creds, cache_discovery=False)

    q = _gmail_query()
    resp = svc.users().messages().list(userId="me", q=q, maxResults=max_messages).execute()
    msg_ids = [m["id"] for m in (resp.get("messages", []) or [])]

    items: List[Dict[str, Any]] = []
    needs_response: List[Dict[str, Any]] = []

    for mid in msg_ids:
        try:
            m = (
                svc.users()
                .messages()
                .get(userId="me", id=mid, format="metadata", metadataHeaders=["From", "Subject", "Date"])
                .execute()
            )
            payload = m.get("payload", {}) or {}
            headers = payload.get("headers", []) or []
            frm = _header(headers, "From")
            subject = _header(headers, "Subject")
            date = _header(headers, "Date")
            snippet = m.get("snippet", "") or ""

            is_question = _has_question(f"{subject}
{snippet}", extra_phrases)
            entry = {"from": frm, "subject": subject, "date": date, "snippet": snippet, "id": mid, "is_question": is_question}
            items.append(entry)
            if is_question:
                needs_response.append(entry)
        except Exception as e:
            log(f"[gmail] message {mid} failed: {e}")

    return {
        "id": "inbox",
        "title": "Inbox Summary (Last 48 Hours — Inbox Only)",
        "type": "inbox",
        "data": {"query": q, "needs_response": needs_response, "items": items},
    }
