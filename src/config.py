from __future__ import annotations

import os
import re
from typing import Any, Dict

import yaml

ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def load_config(path: str) -> Dict[str, Any]:
    """Load YAML config from disk."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def _resolve_value(val: Any) -> Any:
    """Recursively replace ${ENV_VAR} placeholders with environment variables."""
    if isinstance(val, str):
        def repl(m: re.Match) -> str:
            key = m.group(1)
            if key not in os.environ:
                raise KeyError(f"Missing required environment variable: {key}")
            return os.environ[key]
        return ENV_PATTERN.sub(repl, val)

    if isinstance(val, list):
        return [_resolve_value(v) for v in val]

    if isinstance(val, dict):
        return {k: _resolve_value(v) for k, v in val.items()}

    return val


def resolve_env_vars(cfg: Dict[str, Any]) -> Dict[str, Any]:
    return _resolve_value(cfg)
