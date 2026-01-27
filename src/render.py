from __future__ import annotations

import html
from typing import Any, Dict, List, Optional


def escape(s: Any) -> str:
    return html.escape("" if s is None else str(s), quote=True)


# -----------------------
# Color helpers (Weather)
# -----------------------
def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _rgb(r: float, g: float, b: float) -> str:
    return f"rgb({int(round(r))},{int(round(g))},{int(round(b))})"


def _temp_to_color_f(temp_f: float, tmin: float = -30.0, tmax: float = 110.0) -> str:
    """
    Map temp to deep-blue -> red.
    """
    t = (temp_f - tmin) / (tmax - tmin)
    t = _clamp(t, 0.0, 1.0)

    # deep blue -> red
    # blue: (20, 60, 200)  red: (220, 60, 60)
    r = _lerp(20, 220, t)
    g = _lerp(60, 60, t)
    b = _lerp(200, 60, t)
    return _rgb(r, g, b)


def _best_text_color(bg_rgb: str) -> str:
    """
    Choose black/white text based on background brightness.
    bg_rgb like "rgb(r,g,b)".
    """
    try:
        nums = bg_rgb.replace("rgb(", "").replace(")", "").split(",")
        r, g, b = [int(x.strip()) for x in nums[:3]]
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        return "#000" if lum > 150 else "#fff"
    except Exception:
        return "#000"


def _rain_to_overlay_alpha(rain_pct: float) -> float:
    """
    0% -> 0.00 overlay, 100% -> 0.45 overlay (subtle).
    """
    t = _clamp(rain_pct / 100.0, 0.0, 1.0)
    return _lerp(0.0, 0.45, t)


# -----------------------
# Page wrapper + cards
# -----------------------
_BASE_CSS = """
  :root { color-scheme: light; }
  body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; background: #f5f6f8; }
  .container { max-width: 980px; margin: 0 auto; padding: 18px; }
  .title { font-size: 22px; font-weight: 700; margin: 8px 0 14px; }
  .subtle { color: #6b7280; font-size: 12px; line-height: 1.4; }
  .grid { display: grid; grid-template-columns: 1fr; gap: 12px; }
  @media (min-width: 920px) { .grid { grid-template-columns: 1fr 1fr; } }

  .card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px; padding: 14px; box-shadow: 0 1px 1px rgba(0,0,0,.04); }
  .card h2 { font-size: 14px; margin: 0 0 10px; }
  .card h3 { font-size: 13px; margin: 10px 0 6px; }
  .divider { height: 1px; background: #eef0f3; margin: 10px 0; }

  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; font-size: 12px; color: #6b7280; font-weight: 600; padding: 8px 8px; }
  td { padding: 8px 8px; vertical-align: top; }
  tr.row { border-top: 1px solid #eef0f3; }
  a { color: #2563eb; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .pill { display:inline-block; font-size: 11px; padding: 2px 8px; border-radius: 999px; background:#f3f4f6; color:#111827; border:1px solid #e5e7eb; }
"""

_EMAIL_WRAPPER_CSS = """
  body { margin: 0; padding: 0; background: #f5f6f8; }
  .email-wrap { max-width: 980px; margin: 0 auto; padding: 16px; }
"""

def _wrap_card(title: str, inner_html: str) -> str:
    return f"""
    <div class="card">
      <h2>{escape(title)}</h2>
      {inner_html}
    </div>
    """


# -----------------------
# Section renderers
# -----------------------
def _render_weather(section: Dict[str, Any]) -> str:
    title = section.get("title", "Weather")
    data = section.get("data", {}) or {}

    # New compact-table format
    if "locations" in data and "rows" in data:
        locations = data.get("locations", []) or []
        rows = data.get("rows", []) or []
        alerts = data.get("alerts", []) or []

        alert_html = ""
        if alerts:
            parts = []
            for a in alerts:
                zipc = escape(str(a.get("zip", "")))
                items = a.get("items", []) or []
                if items:
                    li = "".join(f"<li>{escape(str(x))}</li>" for x in items)
                    parts.append(f"<div><b>{zipc}</b><ul style='margin:6px 0 0 18px;'>{li}</ul></div>")
            if parts:
                alert_html = f"<div class='subtle' style='margin-bottom:10px;'>{''.join(parts)}</div>"

        # Table header
        header_cells = "<th>Day</th>" + "".join(
            f"<th>{escape(str(loc.get('label', loc.get('zip',''))))}</th>" for loc in locations
        )

        body_rows = []
        for r in rows:
            day = escape(str(r.get("day", "")))
            cells = r.get("cells", []) or []

            tds = []
            for c in cells:
                lo = c.get("low")
                hi = c.get("high")
                rn = c.get("rain")

                lo_s = "–" if lo is None else str(lo)
                hi_s = "–" if hi is None else str(hi)
                rn_s = "–" if rn is None else str(rn)

                # Requested format: low/high · rain%
                txt = f"{lo_s}/{hi_s} &nbsp;·&nbsp; {rn_s}%"

                # Base cell style
                style = (
                    "padding:8px 10px; border-radius:12px; text-align:center; white-space:nowrap;"
                    "border:1px solid rgba(0,0,0,0.06);"
                )

                # Temp background uses midpoint of low/high
                if lo is not None and hi is not None:
                    mid = (float(lo) + float(hi)) / 2.0
                    bg = _temp_to_color_f(mid)
                    fg = _best_text_color(bg)
                    style += f" background:{bg}; color:{fg};"
                else:
                    style += " background:#f3f4f6; color:#111827;"

                # Rain overlay as an inset tint; keeps temp color visible
                if rn is not None:
                    alpha = _rain_to_overlay_alpha(float(rn))
                    style += f" box-shadow: inset 0 0 0 9999px rgba(30, 120, 255, {alpha:.3f});"

                tds.append(f"<td style='{style}'>{txt}</td>")

            body_rows.append(f"<tr><td style='padding:8px 10px;'><b>{day}</b></td>{''.join(tds)}</tr>")

        table_html = f"""
        {alert_html}
        <table style="width:100%; border-collapse:separate; border-spacing:0 8px;">
          <thead><tr>{header_cells}</tr></thead>
          <tbody>
            {''.join(body_rows)}
          </tbody>
        </table>
        """
        return _wrap_card(title, table_html)

    # Backward compatibility: older per-zip cards
    cards = data.get("cards", []) or []
    parts = []
    for c in cards:
        zipc = escape(str(c.get("zip", "")))
        place = escape(str(c.get("place", "")))
        table = c.get("table", []) or []
        rows_html = "".join(
            f"<tr class='row'><td>{escape(str(x.get('date','')))}</td>"
            f"<td>{escape(str(x.get('low','')))}</td>"
            f"<td>{escape(str(x.get('high','')))}</td>"
            f"<td>{escape(str(x.get('rain_chance','')))}%</td></tr>"
            for x in table
        )
        parts.append(
            f"<div style='margin-bottom:10px;'><b>{zipc}</b> {place}"
            f"<table><thead><tr><th>Date</th><th>Low</th><th>High</th><th>Rain</th></tr></thead>"
            f"<tbody>{rows_html}</tbody></table></div>"
        )
    return _wrap_card(title, "".join(parts) if parts else "<div class='subtle'>No weather data.</div>")


def _render_news(section: Dict[str, Any]) -> str:
    title = section.get("title", "News")
    data = section.get("data", {}) or {}
    items = data.get("items", []) or []
    err = data.get("error")

    if err:
        return _wrap_card(title, f"<div class='subtle'>Error: {escape(err)}</div>")

    if not items:
        return _wrap_card(title, "<div class='subtle'>No results.</div>")

    rows = []
    for it in items:
        t = escape(it.get("title", ""))
        url = it.get("url") or it.get("url", "")
        url = escape(url)
        domain = escape(it.get("domain", ""))
        when = escape(it.get("seendate", ""))
        meta = " · ".join([x for x in [domain, when] if x])
        meta_html = f"<div class='subtle'>{meta}</div>" if meta else ""
        rows.append(f"<div style='margin:8px 0;'><a href='{url}'><b>{t}</b></a>{meta_html}</div>")

    return _wrap_card(title, "".join(rows))


def _render_events(section: Dict[str, Any]) -> str:
    title = section.get("title", "Events")
    data = section.get("data", {}) or {}
    events = data.get("events", []) or []
    err = data.get("error")

    if err:
        return _wrap_card(title, f"<div class='subtle'>Error: {escape(err)}</div>")

    if not events:
        return _wrap_card(title, "<div class='subtle'>No upcoming events.</div>")

    # Expect each event: {"start": "...", "end": "...", "summary": "...", "location": "..."}
    rows = []
    for e in events:
        summary = escape(e.get("summary", "") or e.get("title", ""))
        start = escape(e.get("start", ""))
        end = escape(e.get("end", ""))
        loc = escape(e.get("location", ""))
        line1 = f"<b>{summary}</b>"
        line2_parts = [p for p in [start, ("– " + end) if end else "", loc] if p]
        line2 = " ".join(line2_parts)
        rows.append(f"<div style='margin:8px 0;'>{line1}<div class='subtle'>{line2}</div></div>")

    return _wrap_card(title, "".join(rows))


def _render_inbox(section: Dict[str, Any]) -> str:
    title = section.get("title", "Inbox")
    data = section.get("data", {}) or {}
    err = data.get("error")

    if err:
        return _wrap_card(title, f"<div class='subtle'>Error: {escape(err)}</div>")

    needs = data.get("needs_response", []) or []
    items = data.get("items", []) or []

    top = []
    if needs:
        top.append("<div><span class='pill'>Needs response</span></div>")
        for m in needs[:10]:
            subj = escape(m.get("subject", ""))
            frm = escape(m.get("from", ""))
            snippet = escape(m.get("snippet", ""))
            top.append(f"<div style='margin:8px 0;'><b>{subj}</b><div class='subtle'>From: {frm}</div><div class='subtle'>{snippet}</div></div>")
        top.append("<div class='divider'></div>")

    if items:
        top.append("<div><span class='pill'>Last 48 hours</span></div>")
        for m in items[:10]:
            subj = escape(m.get("subject", ""))
            frm = escape(m.get("from", ""))
            snippet = escape(m.get("snippet", ""))
            top.append(f"<div style='margin:8px 0;'><b>{subj}</b><div class='subtle'>From: {frm}</div><div class='subtle'>{snippet}</div></div>")
    else:
        top.append("<div class='subtle'>No messages found.</div>")

    return _wrap_card(title, "".join(top))


def _render_error(section: Dict[str, Any]) -> str:
    title = section.get("title", "Error")
    data = section.get("data", {}) or {}
    err = data.get("error", "Unknown error")
    return _wrap_card(title, f"<div class='subtle'>Error: {escape(err)}</div>")


def _render_section(section: Dict[str, Any]) -> str:
    t = (section.get("type") or "").lower()

    if t == "weather":
        return _render_weather(section)
    if t == "news":
        return _render_news(section)
    if t in ("events", "calendar"):
        return _render_events(section)
    if t in ("inbox", "gmail", "email_summary"):
        return _render_inbox(section)
    if t == "error":
        return _render_error(section)

    # Fallback
    title = section.get("title", "Section")
    return _wrap_card(title, f"<pre class='subtle' style='white-space:pre-wrap'>{escape(section)}</pre>")


# -----------------------
# Public render functions
# -----------------------
def render_digest_html(digest_date: str, sections: List[Dict[str, Any]]) -> str:
    cards = "\n".join(_render_section(s) for s in sections if s)
    body = f"""
    <div class="container">
      <div class="title">Daily Digest — {escape(digest_date)}</div>
      <div class="grid">
        {cards}
      </div>
      <div class="subtle" style="margin-top:14px;">
        Generated automatically.
      </div>
    </div>
    """
    return f"<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
    f"<style>{_BASE_CSS}</style></head><body>{body}</body></html>"


def render_email_html(digest_date: str, sections: List[Dict[str, Any]], archive_url: Optional[str] = None) -> str:
    cards = "\n".join(_render_section(s) for s in sections if s)

    link_html = ""
    if archive_url:
        link_html = f"<div class='subtle' style='margin:6px 0 0;'>Archive: <a href='{escape(archive_url)}'>{escape(archive_url)}</a></div>"

    body = f"""
    <div class="email-wrap">
      <div class="title">Daily Digest — {escape(digest_date)}</div>
      {link_html}
      <div class="grid">
        {cards}
      </div>
      <div class="subtle" style="margin-top:14px;">
        Generated automatically.
      </div>
    </div>
    """
    return (
        "<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<style>{_BASE_CSS}{_EMAIL_WRAPPER_CSS}</style></head><body>{body}</body></html>"
    )
