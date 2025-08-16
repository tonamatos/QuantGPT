# src/quantgpt/utils/env.py
from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None


def load_env(dotenv_path: str | Path = None) -> None:
    """
    Load environment variables from .env if python-dotenv is installed.
    This keeps runtime tolerant if the package isn't present.
    """
    if load_dotenv:
        if dotenv_path:
            load_dotenv(dotenv_path=dotenv_path)
        else:
            env_path = Path(".") / ".env"
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
    # Always ensure we don't accidentally echo secrets
    os.environ.setdefault("PYTHONWARNINGS", "ignore")
