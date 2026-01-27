from __future__ import annotations

import argparse
import datetime as dt
import os
import traceback
from typing import Any, Dict, List

import pytz

from .config import load_config, resolve_env_vars
from .utils import log
from .weather import build_weather_section
from .news import build_news_sections
from .google_calendar import build_calendar_section_google
from .google_gmail import build_gmail_section
from .outlook_calendar import build_calendar_section_outlook
from .outlook_email import build_outlook_inbox_section
from .render import render_digest_html, render_email_html
from .publish import write_archive, update_home_index
from .send_resend import send_email_resend


def _now_local(tz_name: str) -> dt.datetime:
    tz = pytz.timezone(tz_name)
    return dt.datetime.now(tz)


def _should_send(now_local: dt.datetime, send_time_local: str) -> bool:
    hh, mm = map(int, send_time_local.split(":"))
    target = now_local.replace(hour=hh, minute=mm, second=0, microsecond=0)
    delta_minutes = abs((now_local - target).total_seconds()) / 60.0
    return delta_minutes <= 15.0


def _safe_add(sections: List[Dict[str, Any]], builder, name: str) -> None:
    try:
        sections.extend(builder() if isinstance(builder(), list) else [builder()])
    except Exception as e:
        log(f"[section] {name} failed: {e}")
        log(traceback.format_exc())
        sections.append({"id": f"error_{name}", "title": f"{name} (Error)", "type": "error", "data": {"error": str(e)}})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--force-send", action="store_true", help="Bypass 08:00 local guard (testing).")
    ap.add_argument("--no-email", action="store_true", help="Build archive only; do not send email (testing).")
    args = ap.parse_args()

    cfg = resolve_env_vars(load_config(args.config))

    tz_name = cfg.get("timezone", "America/Chicago")
    send_time = cfg.get("send_time_local", "08:00")
    now = _now_local(tz_name)

    if not args.force_send and not _should_send(now, send_time):
        log(f"Skip: local time is {now.strftime('%Y-%m-%d %H:%M %Z')}, not within send window.")
        return 0

    digest_date = now.strftime("%Y-%m-%d")
    sections: List[Dict[str, Any]] = []

    # Weather
    _safe_add(sections, lambda: build_weather_section(cfg, now), "Weather")

    # News (returns list)
    try:
        sections.extend(build_news_sections(cfg, now))
    except Exception as e:
        log(f"[section] News failed: {e}")
        sections.append({"id": "error_news", "title": "News (Error)", "type": "error", "data": {"error": str(e)}})

    # Calendar
    cal_provider = (cfg.get("calendar", {}) or {}).get("provider", "google")
    if cal_provider == "google":
        _safe_add(sections, lambda: build_calendar_section_google(cfg, now), "Events (Google)")
    else:
        _safe_add(sections, lambda: build_calendar_section_outlook(cfg, now), "Events (Outlook)")

    # Inbox
    inbox_provider = (cfg.get("inbox_summary", {}) or {}).get("provider", "gmail")
    if inbox_provider == "gmail":
        _safe_add(sections, lambda: build_gmail_section(cfg, now), "Inbox (Gmail)")
    else:
        _safe_add(sections, lambda: build_outlook_inbox_section(cfg, now), "Inbox (Outlook)")

    page_html = render_digest_html(digest_date, sections)

    archive_url = None
    if (cfg.get("archive", {}) or {}).get("enabled", True):
        archive_url = write_archive(cfg, digest_date, page_html)
        update_home_index(cfg)

    email_html = render_email_html(digest_date, sections, archive_url=archive_url)

    if args.no_email:
        log("No-email mode: archive built; email not sent.")
        return 0

    api_key = os.environ["RESEND_API_KEY"]
    email_from = os.environ["EMAIL_FROM"]
    to_list = (cfg.get("email", {}) or {}).get("to", [])
    subject_prefix = (cfg.get("email", {}) or {}).get("subject_prefix", "Daily Digest")

    send_email_resend(
        api_key=api_key,
        email_from=email_from,
        email_to=to_list,
        subject=f"{subject_prefix} — {digest_date}",
        html=email_html,
    )

    log("Digest sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
