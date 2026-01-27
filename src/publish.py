from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from .utils import log


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_archive(cfg: Dict[str, Any], digest_date: str, html: str) -> Optional[str]:
    """
    Writes docs/YYYY-MM-DD/index.html by default.
    Returns a relative archive URL path (for linking in email).
    Never KeyErrors on missing config.
    """
    archive_cfg = cfg.get("archive", {}) or {}
    enabled = bool(archive_cfg.get("enabled", True))
    if not enabled:
        return None

    site_dir = archive_cfg.get("site_dir", "docs")
    out_dir = Path(site_dir) / digest_date
    out_path = out_dir / "index.html"
    _write_text(out_path, html)

    # GitHub Pages: if site_dir is docs, /daily-digest/YYYY-MM-DD/ is served depending on repo settings.
    # We return a relative path; renderer will use it as-is.
    return f"{digest_date}/"


def update_home_index(cfg: Dict[str, Any]) -> None:
    """
    Writes docs/index.html as a basic landing page listing latest digests.
    Never KeyErrors on missing config.
    """
    archive_cfg = cfg.get("archive", {}) or {}
    enabled = bool(archive_cfg.get("enabled", True))
    if not enabled:
        return

    site_dir = archive_cfg.get("site_dir", "docs")
    root = Path(site_dir)
    root.mkdir(parents=True, exist_ok=True)

    # Find dated folders
    dates = []
    for p in root.iterdir():
        if p.is_dir() and len(p.name) == 10 and p.name[4] == "-" and p.name[7] == "-":
            if (p / "index.html").exists():
                dates.append(p.name)
    dates.sort(reverse=True)

    items = "\n".join([f"<li><a href='{d}/'>{d}</a></li>" for d in dates[:60]])
    html = f"""<html><head><meta charset="utf-8">
    <style>
      body {{ font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; }}
      .container {{ max-width: 780px; margin: 0 auto; }}
    </style>
    </head><body><div class="container">
      <h1>Daily Digest Archive</h1>
      <ul>{items}</ul>
    </div></body></html>"""

    _write_text(root / "index.html", html)
    log(f"[archive] updated {site_dir}/index.html with {min(len(dates), 60)} entries")
