from __future__ import annotations

import datetime as dt
import re
from typing import Any, Dict, List, Optional
import requests


WATCHLIST_TOKEN_RE = re.compile(r"\{\{watchlist:([a-zA-Z0-9_]+)(\|only:([^}]+))?\}\}")


def _quote_term(term: str) -> str:
    """
    Quote terms containing spaces or special chars (simple heuristic).
    GDELT query language supports quoted strings.
    """
    t = term.strip()
    if not t:
        return t
    if any(ch.isspace() for ch in t) or any(ch in t for ch in ['"', ":", "(", ")", "/"]):
        # If already quoted, keep it
        if t.startswith('"') and t.endswith('"'):
            return t
        return f'"{t}"'
    return t


def _join_or(terms: List[str]) -> str:
    clean = [x for x in (t.strip() for t in terms) if x]
    if not clean:
        return ""
    # Quote selectively, but allow advanced query fragments as-is if they contain operators
    # If user writes something like 'sourceCountry:US' keep it.
    def normalize(x: str) -> str:
        if any(op in x for op in [":", " OR ", " AND ", "(", ")", '"']):
            return x.strip()
        return _quote_term(x)

    parts = [normalize(x) for x in clean]
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
    """
    Replaces tokens like:
      {{watchlist:competitors}}
      {{watchlist:competitors|only:Experian}}
    with an OR group of watchlist terms.
    """
    def repl(m: re.Match) -> str:
        name = m.group(1)
        only_val = (m.group(3) or "").strip() if m.group(2) else ""
        if name not in watchlists:
            raise KeyError(f"Missing watchlist '{name}' in config.yaml")
        terms = watchlists[name]
        if only_val:
            # filter to exact match ignoring case
            terms = [t for t in terms if t.strip().lower() == only_val.lower()]
        return _join_or(terms)

    return WATCHLIST_TOKEN_RE.sub(repl, text)


def _build_query_from_template(
    template: Optional[Dict[str, Any]],
    watchlists: Dict[str, List[str]],
    global_and: str = "",
    exclude_domains: Optional[List[str]] = None,
) -> str:
    """
    Template schema:
      template:
        and: [ ... ]   # list of strings/fragments OR watchlist token strings
        or:  [ ... ]   # list of terms/fragments (becomes OR group)
    Either/both can exist.
    """
    exclude_domains = exclude_domains or []

    and_parts: List[str] = []
    if template:
        # OR group (turn list into (a OR b OR c))
        or_terms = template.get("or", [])
        if isinstance(or_terms, list) and or_terms:
            and_parts.append(_join_or([str(x) for x in or_terms]))

        # AND list (each item can be a fragment or watchlist token)
        and_list = template.get("and", [])
        if isinstance(and_list, list):
            for item in and_list:
                frag = str(item).strip()
                if frag:
                    frag = _expand_watchlist_tokens(frag, watchlists)
                    and_parts.append(frag)

    # global AND (e.g., lang:english)
    if global_and:
        and_parts.append(global_and.strip())

    # Exclude domains
    # GDELT supports domain filtering in various ways; simplest is to add NOT domain:xxx when possible.
    # We'll do best-effort: -(domain:example.com OR domain:foo.com)
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
    r = requests.get("https://api.gdeltproject.org/api/v2/doc/doc", params=params, timeout=25)
    r.raise_for_status()
    data = r.json()
    articles = data.get("articles", []) or []

    out: List[Dict[str, Any]] = []
    for a in articles[:max_items]:
        out.append({
            "title": a.get("title"),
            "domain": a.get("domain"),
            "url": a.get("url"),
            "seendate": a.get("seendate"),
        })
    return out


def build_news_sections(cfg: Dict[str, Any], now: dt.datetime) -> List[Dict[str, Any]]:
    news_cfg = cfg["news"]
    defaults = news_cfg.get("defaults", {})
    global_and = str(defaults.get("global_and", "") or "").strip()
    exclude_domains = defaults.get("exclude_domains", []) or []

    base_lookback = int(news_cfg.get("lookback_hours", 24))
    watchlists = news_cfg.get("watchlists", {}) or {}

    sections_out = []
    for s in news_cfg.get("sections", []):
        s_type = s.get("type", "gdelt")
        count = int(s.get("count", defaults.get("count", 10)))
        lookback = int(s.get("lookback_hours", base_lookback))

        if s_type == "gdelt":
            query = s["query"]
        elif s_type == "gdelt_template":
            template = s.get("template", {}) or {}
            query = _build_query_from_template(
                template=template,
                watchlists=watchlists,
                global_and=global_and,
                exclude_domains=exclude_domains,
            )
        else:
            continue

        items = _gdelt_search(query=query, lookback_hours=lookback, max_items=count)
        sections_out.append({
            "id": f"news_{s['name'].lower().replace(' ', '_').replace('/', '_')}",
            "title": f"News — {s['name']}",
            "type": "news",
            "data": {
                "items": items,
                "count": count,
                "lookback_hours": lookback,
                "query": query,
            },
        })

    return sections_out
