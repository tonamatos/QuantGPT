# src/quantgpt/config.py
from __future__ import annotations

import os
import pathlib
import typing as t
import yaml


DEFAULT_PROFILE_ENV = "QUANTGPT_PROFILE"


def _merge(a: dict, b: dict) -> dict:
    """
    Shallow+recursive merge of dict b into a and return result.
    Values in b override a.
    """
    out = dict(a or {})
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _load_yaml(path: pathlib.Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(*, profile: str | None = None, root: str | None = None) -> dict:
    """
    Load config.yaml if present; otherwise fall back to config.example.yaml.
    Apply an optional profile overlay from `profiles.<name>`.
    """
    root_path = pathlib.Path(root or ".").resolve()
    cfg_path = root_path / "config.yaml"
    example_path = root_path / "config.example.yaml"

    base = _load_yaml(example_path)
    local = _load_yaml(cfg_path)
    cfg = _merge(base, local)

    prof_name = profile or os.getenv(DEFAULT_PROFILE_ENV)
    if prof_name:
        prof = ((cfg.get("profiles") or {}).get(prof_name)) or {}
        # Overlay profile on top-level cfg
        cfg = _merge(cfg, prof)

    return cfg
