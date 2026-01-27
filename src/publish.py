from __future__ import annotations

import os
from typing import Any, Dict, List


def write_archive(cfg: Dict[str, Any], digest_date: str, html: str) -> str:
    """Write <site_dir>/<YYYY-MM-DD>/index.html and return relative URL."""
    site_dir = cfg["archive"]["site_dir"]
    out_dir = os.path.join(site_dir, digest_date)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return f"./{digest_date}/"


def update_home_index(cfg: Dict[str, Any]) -> None:
    site_dir = cfg["archive"]["site_dir"]
    keep = int(cfg["archive"].get("days_to_keep_on_home", 14))

    dates: List[str] = []
    if os.path.isdir(site_dir):
        for name in os.listdir(site_dir):
            p = os.path.join(site_dir, name)
            if os.path.isdir(p) and len(name) == 10 and name[4] == "-" and name[7] == "-":
                dates.append(name)

    dates.sort(reverse=True)
    dates = dates[:keep]

    links = "".join(f'<li><a href="./{d}/">{d}</a></li>' for d in dates)
    html = f"""<html><head><meta charset='utf-8'><title>Daily Digest Archive</title></head>
<body style="font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; padding:24px;">
  <h1>Daily Digest Archive</h1>
  <ul>{links}</ul>
</body></html>"""

    os.makedirs(site_dir, exist_ok=True)
    with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
