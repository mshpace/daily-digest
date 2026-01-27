from __future__ import annotations

import datetime as dt
import re
import time
from typing import Any, Dict, List, Optional

import requests

from .utils import log, safe_int

WATCHLIST_TOKEN_RE = re.compile(r"\{\{watchlist:([a-zA-Z0-9_]+)(\|only:([^}]+))?\}\}")


def _quote_term(term: str) -> str:
    t = (term or "").strip()
    if not t:
        return ""
    if ":" in t or any(op in t for op in [" AND ", " OR ", "(", ")", '"']):
        return t
    if any(ch.isspace() for ch in t):
        return f'"{t}"'
    return t


def _join_or(terms: List[str]) -> str:
    clean = [x.strip() for x in terms if x and x.strip()]
    if not clean:
        return ""
    parts = [_quote_term(x) for x in clean]
    if len(parts) == 1:
        return parts[0]
    return "(" + " OR ".join(parts) + ")"


def _join_and(parts: List[str]) -> str:
    clean = [p.strip() for p in parts if p and p.strip()]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    return "(" + " AND ".join(clean) + ")"


def _expand_watchlist_tokens(text: str, watchlists: Dict[str, List[str]]) -> str:
    def repl(m: re.Match) -> str:
        name = m.group(1)
        only_val = (m.group(3) or "").strip() if m.group(2) else ""
        if name not in watchlists:
            raise KeyError(f"Missing watchlist '{name}' in config.yaml")
        terms = watchlists[name]
        if only_val:
            terms = [t for t in terms if t.strip().lower() == only_val.lower()]
        return _join_or([str(t) for t in terms])
    return WATCHLIST_TOKEN_RE.sub(repl, text)


def _build_query_from_template(
    template: Optional[Dict[str, Any]],
    watchlists: Dict[str, List[str]],
    global_and: str = "",
    exclude_domains: Optional[List[str]] = None,
) -> str:
    exclude_domains = exclude_domains or []
    and_parts: List[str] = []

    template = template or {}
    or_terms = template.get("or", [])
    if isinstance(or_terms, list) and or_terms:
        and_parts.append(_join_or([str(x) for x in or_terms]))

    and_list = template.get("and", [])
    if isinstance(and_list, list):
        for item in and_list:
            frag = str(item).strip()
            if frag:
                frag = _expand_watchlist_tokens(frag, watchlists)
                and_parts.append(frag)

    if global_and:
        and_parts.append(str(global_and).strip())

    if exclude_domains:
        ex = [f"domain:{d.strip()}" for d in exclude_domains if d and d.strip()]
        if ex:
            and_parts.append(f"-({_join_or(ex)})")

    return _join_and(and_parts)


def _gdelt_search(query: str, lookback_hours: int, max_items: int) -> List[Dict[str, Any]]:
    now_utc = dt.datetime.now(dt.timezone.utc)
    start = now_utc - dt.timedelta(hours=lookback_hours)
    start_str = start.strftime("%Y%m%d%H%M%S")

    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": max_items,
        "startdatetime": start_str,
        "sort": "HybridRel",
    }

    # Backoff policy: 429/5xx -> retry
    backoffs = [5, 5, 10, 15]  # seconds
    last_err: Optional[Exception] = None

    for attempt, wait_s in enumerate([0] + backoffs):
        if wait_s:
            time.sleep(wait_s)

        try:
            r = requests.get("https://api.gdeltproject.org/api/v2/doc/doc", params=params, timeout=30)
            if r.status_code in (429, 500, 502, 503, 504):
                raise RuntimeError(f"GDELT HTTP {r.status_code}: {r.text[:200]}")
            r.raise_for_status()
            data = r.json()
            articles = data.get("articles", []) or []
            out: List[Dict[str, Any]] = []
            for a in articles[:max_items]:
                out.append(
                    {
                        "title": a.get("title") or "",
                        "domain": a.get("domain") or "",
                        "url": a.get("url") or "",
                        "seendate": a.get("seendate") or "",
                    }
                )
            return out

        except Exception as e:
            last_err = e
            if attempt == len(backoffs):
                break

    raise last_err or RuntimeError("GDELT failed")


def build_news_sections(cfg: Dict[str, Any], now: dt.datetime) -> List[Dict[str, Any]]:
    news_cfg = cfg.get("news", {}) or {}
    defaults = news_cfg.get("defaults", {}) or {}

    global_and = str(defaults.get("global_and", "") or "").strip()
    exclude_domains = defaults.get("exclude_domains", []) or []

    base_lookback = safe_int(news_cfg.get("lookback_hours", 24), 24)
    watchlists = news_cfg.get("watchlists", {}) or {}
    throttle_s = float(news_cfg.get("throttle_seconds_between_sections", 1.5))

    out_sections: List[Dict[str, Any]] = []
    for idx, s in enumerate((news_cfg.get("sections", []) or [])):
        name = s.get("name", "News")
        s_type = s.get("type", "gdelt_template")
        count = safe_int(s.get("count", defaults.get("count", 10)), 10)
        lookback = safe_int(s.get("lookback_hours", base_lookback), base_lookback)

        # small throttle between sections to reduce 429s
        if idx > 0 and throttle_s > 0:
            time.sleep(throttle_s)

        try:
            if s_type == "gdelt":
                query = str(s["query"])
            else:
                query = _build_query_from_template(
                    template=s.get("template", {}) or {},
                    watchlists=watchlists,
                    global_and=global_and,
                    exclude_domains=exclude_domains,
                )

            items = _gdelt_search(query=query, lookback_hours=lookback, max_items=count)
            out_sections.append(
                {
                    "id": f"news_{name.lower().replace(' ', '_').replace('/', '_')}",
                    "title": f"News — {name}",
                    "type": "news",
                    "data": {"items": items, "count": count, "lookback_hours": lookback, "query": query},
                }
            )
        except Exception as e:
            log(f"[news] section '{name}' failed: {e}")
            out_sections.append(
                {
                    "id": f"news_{name.lower().replace(' ', '_').replace('/', '_')}",
                    "title": f"News — {name}",
                    "type": "news",
                    "data": {"items": [], "count": count, "lookback_hours": lookback, "query": "", "error": str(e)},
                }
            )

    return out_sections
