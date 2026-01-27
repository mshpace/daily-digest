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
    return f"""<html><head><meta charset='utf-8'>{BASE_CSS}</head>
<body><div class="container">
  <div class="h1">Daily Digest — {escape(digest_date)}</div>
  <div class="meta small">Generated automatically.</div>
  {cards}
</div></body></html>"""


def render_email_html(digest_date: str, sections: List[Dict[str, Any]], archive_url: Optional[str]) -> str:
    top = ""
    if archive_url:
        top = f'<div class="card"><div><span class="pill">Archive</span> <a href="{escape(archive_url)}">View today’s digest page</a></div></div>'
    cards = top + "".join(_render_section(s) for s in sections)
    return f"""<html><head><meta charset='utf-8'>{BASE_CSS}</head>
<body><div class="container">
  <div class="h1">Daily Digest — {escape(digest_date)}</div>
  {cards}
</div></body></html>"""


def _render_section(section: Dict[str, Any]) -> str:
    t = section.get("type", "")
    title = section.get("title", "")
    data = section.get("data", {}) or {}

    if t == "weather":
        cards_html = []
        for c in data.get("cards", []) or []:
            if c.get("error"):
                cards_html.append(
                    f'<div class="card"><div><strong>{escape(c.get("zip",""))}</strong></div>'
                    f'<div class="small">Error: {escape(c.get("error",""))}</div></div>'
                )
                continue

            rows = "".join(
                f"<tr><td>{escape(str(r.get('date','')))}</td>"
                f"<td>{escape(str(r.get('high','')))}</td>"
                f"<td>{escape(str(r.get('low','')))}</td>"
                f"<td>{'' if r.get('rain_chance') is None else escape(str(r.get('rain_chance'))) + '%'}"
                f"</td></tr>"
                for r in (c.get("table", []) or [])
            )

            alerts = c.get("alerts", []) or []
            alerts_html = ""
            if alerts:
                arows = "".join(
                    f"<tr><td>{escape(a.get('event',''))}</td><td>{escape(a.get('severity',''))}</td><td>{escape(a.get('headline',''))}</td></tr>"
                    for a in alerts[:10]
                )
                alerts_html = (
                    "<div class='small' style='margin-top:10px;'><strong>Active Alerts</strong></div>"
                    "<table><thead><tr><th>Event</th><th>Severity</th><th>Headline</th></tr></thead>"
                    f"<tbody>{arows}</tbody></table>"
                )

            cards_html.append(
                f"""<div class="card">
  <div><strong>{escape(c.get('zip',''))}</strong> <span class="small">({escape(c.get('place',''))})</span></div>
  <table><thead><tr><th>Date</th><th>High</th><th>Low</th><th>Rain %</th></tr></thead>
  <tbody>{rows}</tbody></table>
  {alerts_html}
</div>"""
            )
        return _card(title, f'<div class="two-col">{"".join(cards_html)}</div>')

    if t == "news":
        if data.get("error"):
            return _card(title, f"<div class='small'>Error: {escape(data.get('error',''))}</div>")

        items = data.get("items", []) or []
        q = data.get("query", "") or ""
        rows = "".join(
            f'<tr><td><a href="{escape(i.get("url",""))}">{escape(i.get("title",""))}</a>'
            f'<div class="small">{escape((i.get("domain","") or "") + (" • " + (i.get("seendate","") or "") if i.get("seendate") else ""))}</div>'
            f"</td></tr>"
            for i in items
        )
        html = f"<div class='small'>Query: {escape(q)}</div><table><thead><tr><th>Top Headlines</th></tr></thead><tbody>{rows}</tbody></table>"
        return _card(title, html)

    if t == "events":
        evs = data.get("events", []) or []
        if not evs:
            return _card(title, "<div class='small'>No events found.</div>")
        rows = "".join(
            f"<tr><td>{escape(e.get('start',''))}</td>"
            f"<td><a href="{escape(e.get('htmlLink','') or '')}">{escape(e.get('summary',''))}</a>"
            f"<div class='small'>{escape(e.get('calendar',''))}</div></td>"
            f"<td>{escape(e.get('location') or '')}</td></tr>"
            for e in evs[:500]
        )
        return _card(title, f"<table><thead><tr><th>Start</th><th>Event</th><th>Location</th></tr></thead><tbody>{rows}</tbody></table>")

    if t == "inbox":
        needs = data.get("needs_response", []) or []
        items = data.get("items", []) or []
        query = data.get("query", "") or ""

        def rows_for(lst):
            return "".join(
                f"<tr><td>{escape(i.get('date',''))}</td><td>{escape(i.get('from',''))}</td>"
                f"<td><strong>{escape(i.get('subject',''))}</strong><div class='small'>{escape(i.get('snippet',''))}</div></td></tr>"
                for i in lst
            )

        needs_html = "<div class='small'>No obvious question-style emails found.</div>"
        if needs:
            needs_html = f"<table><thead><tr><th>Date</th><th>From</th><th>Message</th></tr></thead><tbody>{rows_for(needs[:50])}</tbody></table>"

        all_html = "<div class='small'>No inbox messages found in the last 48 hours.</div>"
        if items:
            all_html = f"<table><thead><tr><th>Date</th><th>From</th><th>Message</th></tr></thead><tbody>{rows_for(items[:100])}</tbody></table>"

        html = (
            "<div class='small'><span class='pill'>Needs Response</span></div>"
            f"{needs_html}"
            "<div style='height:14px;'></div>"
            f"<div class='small'><span class='pill'>All Inbox (48h)</span> Query: {escape(query)}</div>"
            f"{all_html}"
        )
        return _card(title, html)

    if t == "error":
        return _card(title, f"<div class='small'>Error: {escape(str(data.get('error','')))}</div>")

    return _card(title, f"<div class='small'>Unsupported section type: {escape(t)}</div>")
