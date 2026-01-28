# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
from pathlib import Path

from app_version import APP_ID


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_path(rel: str) -> Path:
    """Get absolute path to bundled resource (works for PyInstaller)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / rel


def appdata_dir() -> Path:
    root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    p = Path(root) / APP_ID
    p.mkdir(parents=True, exist_ok=True)
    return p


def user_db_path() -> Path:
    return appdata_dir() / "bot_system.db"


def templates_dir() -> Path:
    return resource_path("assets/db")
