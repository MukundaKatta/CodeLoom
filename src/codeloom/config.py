"""Configuration management for CodeLoom."""

from __future__ import annotations

import os
from pathlib import Path

# Default database location
DEFAULT_DB_DIR = Path.home() / ".codeloom"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "snippets.db"


def get_db_path() -> str:
    """Return the database path, respecting CODELOOM_DB_PATH env var."""
    env_path = os.environ.get("CODELOOM_DB_PATH")
    if env_path:
        return env_path
    DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
    return str(DEFAULT_DB_PATH)


def get_export_dir() -> Path:
    """Return the default export directory."""
    export_dir = DEFAULT_DB_DIR / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir
