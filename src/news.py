from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import feedparser

from .utils import log, safe_int


def _google_news_rss_url(query: str, hl: str = "en-US", gl: str = "US", ceid: str = "US:en") -> str:
    # Google News RSS search endpoint
    q = quote_plus(query)
    return f"https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"


def _parse_entry(e: Any) -> Dict[str, Any]:
    title = getattr(e, "title", "") or ""
    link = getattr(e, "link", "") or ""
    published = getattr(e, "published", "") or getattr(e, "updated", "") or ""
    source = ""
    # feedparser sometimes includes source in tags or via "source" field; we keep it best-effort
    if hasattr(e, "source") and e.source:
        try:
            source = getattr(e.source, "title", "") or ""
        except Exception:
            source = ""
    return {
        "title": title,
        "url": link,
        "seendate": published,
        "domain": source,  # keep field name consistent with renderer
    }


def _fetch_rss_items(url: str, max_items: int) -> List[Dict[str, Any]]:
    feed = feedparser.parse(url)
    if getattr(feed, "bozo", 0):
        # bozo indicates malformed feed or parse issue; still may contain entries
        err = getattr(feed, "bozo_exception", None)
        if err:
            log(f"[news/rss] parse warning: {err}")

    entries = getattr(feed, "entries", []) or []
    out: List[Dict[str, Any]] = []
    for e in entries[:max_items]:
        out.append(_parse_entry(e))
    return out


def build_news_sections(cfg: Dict[str, Any], now: dt.datetime) -> List[Dict[str, Any]]:
    """
    RSS-based news sections (no GDELT). Uses Google News RSS search.
    Config shape:

    news:
      defaults:
        count: 10
      rss:
        hl: en-US
        gl: US
        ceid: US:en
      sections:
        - name: "US (Top)"
          rss_query: "top stories United States"
          count: 10
    """
    news_cfg = cfg.get("news", {}) or {}
    defaults = news_cfg.get("defaults", {}) or {}
    base_count = safe_int(defaults.get("count", 10), 10)

    rss_cfg = (news_cfg.get("rss", {}) or {})
    hl = rss_cfg.get("hl", "en-US")
    gl = rss_cfg.get("gl", "US")
    ceid = rss_cfg.get("ceid", "US:en")

    sections = news_cfg.get("sections", []) or []
    out_sections: List[Dict[str, Any]] = []

    for s in sections:
        name = s.get("name", "News")
        count = safe_int(s.get("count", base_count), base_count)

        rss_query = (s.get("rss_query") or "").strip()
        if not rss_query:
            # Backwards-compat: if you kept gdelt_template config, we can't reliably translate it.
            out_sections.append(
                {
                    "id": f"news_{name.lower().replace(' ', '_').replace('/', '_')}",
                    "title": f"News — {name}",
                    "type": "news",
                    "data": {
                        "items": [],
                        "count": count,
                        "lookback_hours": safe_int(news_cfg.get("lookback_hours", 24), 24),
                        "query": "",
                        "error": "Missing rss_query for this section. Add news.sections[].rss_query in config.yaml.",
                    },
                }
            )
            continue

        try:
            url = _google_news_rss_url(rss_query, hl=hl, gl=gl, ceid=ceid)
            items = _fetch_rss_items(url, max_items=count)
            out_sections.append(
                {
                    "id": f"news_{name.lower().replace(' ', '_').replace('/', '_')}",
                    "title": f"News — {name}",
                    "type": "news",
                    "data": {
                        "items": items,
                        "count": count,
                        "lookback_hours": safe_int(news_cfg.get("lookback_hours", 24), 24),
                        "query": rss_query,
                    },
                }
            )
        except Exception as e:
            log(f"[news/rss] section '{name}' failed: {e}")
            out_sections.append(
                {
                    "id": f"news_{name.lower().replace(' ', '_').replace('/', '_')}",
                    "title": f"News — {name}",
                    "type": "news",
                    "data": {
                        "items": [],
                        "count": count,
                        "lookback_hours": safe_int(news_cfg.get("lookback_hours", 24), 24),
                        "query": rss_query,
                        "error": str(e),
                    },
                }
            )

    return out_sections
