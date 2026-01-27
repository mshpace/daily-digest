from __future__ import annotations

from html import escape
from typing import Any, Dict, List, Optional

BASE_CSS = """
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; background:#f6f7f9; margin:0; padding:24px; }
  .container { max-width: 980px; margin: 0 auto; }
  .h1 { font-size: 24px; margin: 0 0 12px 0; }
  .meta { color:#555; margin-bottom: 18px; }
  .card { background:#fff; border:1px solid #e6e8ec; border-radius: 12px; padding:16px; margin: 14px 0; box-shadow: 0 1px 1px rgba(0,0,0,.03); }
  .card h2 { font-size: 18px; margin: 0 0 10px 0; }
  table { width:100%; border-collapse: collapse; }
  th, td { text-align:left; padding:8px; border-bottom:1px solid #eee; vertical-align: top; }
  th { background:#fafafa; font-weight:600; }
  .pill { display:inline-block; padding:2px 8px; border-radius: 999px; background:#eef2ff; font-size:12px; }
  .small { color:#666; font-size: 12px; }
  a { color:#0b57d0; text-decoration:none; }
  a:hover { text-decoration:underline; }
  .two-col { display:grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  @media (max-width: 760px) { .two-col { grid-template-columns: 1fr; } }
</style>
"""


def _card(title: str, inner_html: str) -> str:
    return f'<div class="card"><h2>{escape(title)}</h2>{inner_html}</div>'


def render_digest_html(digest_date: str, sections: List[Dict[str, Any]]) -> str:
    cards = "".join(_render_section(s) for s in sections)
    return (
        "<html><head><meta charset='utf-8'>"
        + BASE_CSS
        + "</head><body><div class='container'>"
        + f"<div class='h1'>Daily Digest — {escape(digest_date)}</div>"
        + "<div class='meta small'>Generated automatically.</div>"
        + cards
        + "</div></body></html>"
    )


def render_email_html(digest_date: str, sections: List[Dict[str, Any]], archive_url: Optional[str]) -> str:
    top = ""
    if archive_url:
        top = (
            "<div class='card'><div>"
            "<span class='pill'>Archive</span> "
            f"<a href='{escape(archive_url)}'>View today’s digest page</a>"
            "</div></div>"
        )
    cards = top + "".join(_render_section(s) for s in sections)
    return (
        "<html><head><meta charset='utf-8'>"
        + BASE_CSS
        + "</head><body><div class='container'>"
        + f"<div class='h1'>Daily Digest — {escape(digest_date)}</div>"
        + cards
        + "</div></body></html>"
    )


def _render_section(section: Dict[str, Any]) -> str:
    t = section.get("type", "")
    title = section.get("title", "")
    data = section.get("data", {}) or {}

    if t == "weather":
        return _render_weather(title, data)

    if t == "news":
        return _render_news(title, data)

    if t == "events":
        return _render_events(title, data)

    if t == "inbox":
        return _render_inbox(title, data)

    if t == "error":
        msg = str((data or {}).get("error", "Unknown error"))
        return _card(title, f"<div class='small'>Error: {escape(msg)}</div>")

    return _card(title, f"<div class='small'>Unsupported section type: {escape(t)}</div>")


def _render_weather(title: str, data: Dict[str, Any]) -> str:
    cards_html: List[str] = []
    for c i
