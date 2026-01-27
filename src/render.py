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

    for c in (data.get("cards", []) or []):
        if c.get("error"):
            cards_html.append(
                "<div class='card'>"
                f"<div><strong>{escape(c.get('zip',''))}</strong></div>"
                f"<div class='small'>Error: {escape(c.get('error',''))}</div>"
                "</div>"
            )
            continue

        rows: List[str] = []
        for r in (c.get("table", []) or []):
            rain = "" if r.get("rain_chance") is None else f"{r.get('rain_chance')}%"
            rows.append(
                "<tr>"
                f"<td>{escape(str(r.get('date','')))}</td>"
                f"<td>{escape(str(r.get('high','')))}</td>"
                f"<td>{escape(str(r.get('low','')))}</td>"
                f"<td>{escape(rain)}</td>"
                "</tr>"
            )

        table_html = (
            "<table><thead><tr><th>Date</th><th>High</th><th>Low</th><th>Rain %</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )

        alerts = c.get("alerts", []) or []
        alerts_html = ""
        if alerts:
            arows: List[str] = []
            for a in alerts[:10]:
                arows.append(
                    "<tr>"
                    f"<td>{escape(a.get('event',''))}</td>"
                    f"<td>{escape(a.get('severity',''))}</td>"
                    f"<td>{escape(a.get('headline',''))}</td>"
                    "</tr>"
                )
            alerts_html = (
                "<div class='small' style='margin-top:10px;'><strong>Active Alerts</strong></div>"
                "<table><thead><tr><th>Event</th><th>Severity</th><th>Headline</th></tr></thead>"
                f"<tbody>{''.join(arows)}</tbody></table>"
            )

        cards_html.append(
            "<div class='card'>"
            f"<div><strong>{escape(c.get('zip',''))}</strong> "
            f"<span class='small'>({escape(c.get('place',''))})</span></div>"
            + table_html
            + alerts_html
            + "</div>"
        )

    return _card(title, f"<div class='two-col'>{''.join(cards_html)}</div>")


def _render_news(title: str, data: Dict[str, Any]) -> str:
    if data.get("error"):
        return _card(title, f"<div class='small'>Error: {escape(str(data.get('error')))}</div>")

    items = data.get("items", []) or []
    q = data.get("query", "") or ""

    rows: List[str] = []
    for i in items:
        url = i.get("url", "") or ""
        headline = i.get("title", "") or ""
        domain = i.get("domain", "") or ""
        seendate = i.get("seendate", "") or ""
        meta = domain + (f" • {seendate}" if seendate else "")
        rows.append(
            "<tr><td>"
            f"<a href='{escape(url)}'>{escape(headline)}</a>"
            f"<div class='small'>{escape(meta)}</div>"
            "</td></tr>"
        )

    html = (
        f"<div class='small'>Query: {escape(q)}</div>"
        "<table><thead><tr><th>Top Headlines</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )
    return _card(title, html)


def _render_events(title: str, data: Dict[str, Any]) -> str:
    evs = data.get("events", []) or []
    if not evs:
        return _card(title, "<div class='small'>No events found.</div>")

    rows: List[str] = []
    for e in evs[:500]:
        start = e.get("start", "") or ""
        link = e.get("htmlLink", "") or ""
        summary = e.get("summary", "") or ""
        cal = e.get("calendar", "") or ""
        loc = e.get("location") or ""
        rows.append(
            "<tr>"
            f"<td>{escape(start)}</td>"
            f"<td><a href='{escape(link)}'>{escape(summary)}</a>"
            f"<div class='small'>{escape(cal)}</div></td>"
            f"<td>{escape(loc)}</td>"
            "</tr>"
        )

    html = (
        "<table><thead><tr><th>Start</th><th>Event</th><th>Location</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )
    return _card(title, html)


def _render_inbox(title: str, data: Dict[str, Any]) -> str:
    needs = data.get("needs_response", []) or []
    items = data.get("items", []) or []
    query = data.get("query", "") or ""

    def _row(i: Dict[str, Any]) -> str:
        return (
            "<tr>"
            f"<td>{escape(i.get('date','') or '')}</td>"
            f"<td>{escape(i.get('from','') or '')}</td>"
            f"<td><strong>{escape(i.get('subject','') or '')}</strong>"
            f"<div class='small'>{escape(i.get('snippet','') or '')}</div></td>"
            "</tr>"
        )

    if needs:
        needs_html = (
            "<table><thead><tr><th>Date</th><th>From</th><th>Message</th></tr></thead>"
            f"<tbody>{''.join(_row(x) for x in needs[:50])}</tbody></table>"
        )
    else:
        needs_html = "<div class='small'>No obvious question-style emails found.</div>"

    if items:
        all_html = (
            "<table><thead><tr><th>Date</th><th>From</th><th>Message</th></tr></thead>"
            f"<tbody>{''.join(_row(x) for x in items[:100])}</tbody></table>"
        )
    else:
        all_html = "<div class='small'>No inbox messages found in the last 48 hours.</div>"

    html = (
        "<div class='small'><span class='pill'>Needs Response</span></div>"
        + needs_html
        + "<div style='height:14px;'></div>"
        + f"<div class='small'><span class='pill'>All Inbox (48h)</span> Query: {escape(query)}</div>"
        + all_html
    )
    return _card(title, html)
