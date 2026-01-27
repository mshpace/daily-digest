from __future__ import annotations

import datetime as dt
from typing import Any, Dict


def build_outlook_inbox_section(cfg: Dict[str, Any], now: dt.datetime) -> Dict[str, Any]:
    return {
        "id": "inbox_outlook",
        "title": "Inbox Summary (Outlook) — Not configured yet",
        "type": "inbox",
        "data": {"needs_response": [], "items": [], "query": "TODO(Graph)"},
    }
