from __future__ import annotations

from typing import Any


def safe_int(v: Any, default: int) -> int:
    try:
        return int(v)
    except Exception:
        return default


def log(msg: str) -> None:
    # GitHub Actions-friendly
    print(msg, flush=True)
