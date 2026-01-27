from __future__ import annotations

import datetime as dt
import os
from typing import Any, Dict, List

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .utils import log, safe_int

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _creds_from_env() -> Credentials:
    return Credentials(
        token=None,
        refresh_token=os.environ.get("GOOGLE_REFRESH_TOKEN", ""),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
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
    """
    Returns a section dict. Never returns None.
    """
    try:
        inbox_cfg = cfg.get("inbox_summary", {}) or {}
        max_messages = safe_int(inbox_cfg.get("max_messages", 200), 200)
        extra_phrases = (inbox_cfg.get("detect_questions", {}) or {}).get("extra_phrases", []) or []

        # Basic env validation so we fail with a nice error section
        missing = []
        for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"):
            if not os.environ.get(k):
                missing.append(k)
        if missing:
            raise RuntimeError(f"Missing required env vars for Gmail: {', '.join(missing)}")

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
                    .get(
                        userId="me",
                        id=mid,
                        format="metadata",
                        metadataHeaders=["From", "Subject", "Date"],
                    )
                    .execute()
                )

                payload = m.get("payload", {}) or {}
                headers = payload.get("headers", []) or []

                frm = _header(headers, "From")
                subject = _header(headers, "Subject")
                date_str = _header(headers, "Date")
                snippet = m.get("snippet", "") or ""

                # Keep this on ONE line to avoid copy/paste quote corruption
                is_question = _has_question(f"{subject}\n{snippet}", extra_phrases)

                entry = {
                    "from": frm,
                    "subject": subject,
                    "date": date_str,
                    "snippet": snippet,
                    "id": mid,
                    "is_question": is_question,
                }
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

    except Exception as e:
        log(f"[gmail] build section failed: {e}")
        return {
            "id": "inbox_error",
            "title": "Inbox Summary (Error)",
            "type": "error",
            "data": {"error": str(e)},
        }
