# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import requests

from app_version import APP_ID, APP_VERSION, GITHUB_OWNER, GITHUB_REPO, APP_NAME
from paths import appdata_dir


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    asset_name: str
    asset_url: str


def _parse_version(v: str) -> Tuple[int, int, int]:
    # accepts 1.2.3 or v1.2.3
    v = v.strip()
    if v.startswith("v"):
        v = v[1:]
    parts = v.split(".")
    nums = []
    for p in parts[:3]:
        try:
            nums.append(int(p))
        except Exception:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)  # type: ignore


def _github_latest_release(timeout: int = 10) -> dict:
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{APP_NAME}/{APP_VERSION}",
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()


def check_update(asset_name_preference: Optional[str] = None) -> Optional[UpdateInfo]:
    """Return UpdateInfo if a newer version exists on GitHub Releases, else None."""
    try:
        rel = _github_latest_release()
        tag = rel.get("tag_name") or ""
        latest = _parse_version(str(tag))
        current = _parse_version(APP_VERSION)
        if latest <= current:
            return None

        assets = rel.get("assets") or []
        if not assets:
            return None

        # choose asset
        chosen = None
        if asset_name_preference:
            for a in assets:
                if a.get("name") == asset_name_preference:
                    chosen = a
                    break
        if chosen is None:
            # heuristic: prefer zip
            for a in assets:
                n = str(a.get("name") or "")
                if n.lower().endswith(".zip"):
                    chosen = a
                    break
        if chosen is None:
            chosen = assets[0]

        return UpdateInfo(
            version=str(tag).lstrip("v"),
            asset_name=str(chosen.get("name") or ""),
            asset_url=str(chosen.get("browser_download_url") or ""),
        )
    except Exception:
        return None


def _download(url: str, to_path: Path, timeout: int = 30) -> None:
    headers = {"User-Agent": f"{APP_NAME}/{APP_VERSION}"}
    with requests.get(url, headers=headers, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        to_path.parent.mkdir(parents=True, exist_ok=True)
        with open(to_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 128):
                if chunk:
                    f.write(chunk)


def _write_update_bat(bat_path: Path, install_dir: Path, new_dir: Path, exe_name: str) -> None:
    # Use robocopy for reliable copy; exclude user data by design (DB is in %APPDATA%\APP_ID)
    # Wait until app exits by waiting a moment and retrying.
    lines = [
        "@echo off",
        "setlocal enabledelayedexpansion",
        "chcp 65001>nul",
        "",
        "REM wait a bit for the main app to exit",
        "timeout /t 1 /nobreak >nul",
        "",
        f"set INSTALL_DIR={install_dir}",
        f"set NEW_DIR={new_dir}",
        "",
        "REM copy new files over current install dir",
        "REM /MIR mirrors directory; avoid deleting outside app folder by targeting INSTALL_DIR only",
        "robocopy \"%NEW_DIR%\" \"%INSTALL_DIR%\" /MIR /R:3 /W:1 >nul",
        "set RC=%ERRORLEVEL%",
        "REM robocopy returns 0-7 as success codes",
        "if %RC% GEQ 8 exit /b %RC%",
        "",
        f"start \"\" \"%INSTALL_DIR%\\{exe_name}\"",
        "endlocal",
    ]
    bat_path.parent.mkdir(parents=True, exist_ok=True)
    bat_path.write_text("\r\n".join(lines), encoding="utf-8")


def apply_update(info: UpdateInfo) -> bool:
    """Download the update asset, stage it, then spawn updater and exit.

    NOTE: The caller should quit the Qt app after this returns True.
    """
    try:
        if not info.asset_url:
            return False

        # install_dir: where current exe lives
        import sys
        current_exe = Path(os.path.abspath(os.getenv("_PYI_EXE_PATH", "") or sys.executable))
        install_dir = current_exe.parent
        exe_name = current_exe.name

        # stage
        upd_root = appdata_dir() / "updates"
        stage_dir = upd_root / f"stage_{int(time.time())}"
        zpath = stage_dir / info.asset_name
        _download(info.asset_url, zpath)

        # extract
        extract_dir = stage_dir / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)

        if zpath.suffix.lower() == ".zip":
            with zipfile.ZipFile(str(zpath), "r") as z:
                z.extractall(str(extract_dir))
        else:
            # if asset is exe, just place it
            shutil.copyfile(str(zpath), str(extract_dir / exe_name))

        # Determine new app dir contents: if zip contains a single top folder, use it.
        candidates = [p for p in extract_dir.iterdir() if p.is_dir()]
        new_app_dir = None
        if len(candidates) == 1 and (candidates[0] / exe_name).exists():
            new_app_dir = candidates[0]
        elif (extract_dir / exe_name).exists():
            new_app_dir = extract_dir
        else:
            # search
            for p in extract_dir.rglob(exe_name):
                new_app_dir = p.parent
                break
        if new_app_dir is None:
            return False

        # write updater bat
        bat_path = stage_dir / "update.bat"
        _write_update_bat(bat_path, install_dir=install_dir, new_dir=new_app_dir, exe_name=exe_name)

        # spawn detached updater
        subprocess.Popen(
            ["cmd.exe", "/c", str(bat_path)],
            cwd=str(stage_dir),
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
        return True
    except Exception:
        return False


def should_check_updates() -> bool:
    # Only auto-update in packaged builds
    try:
        import sys
        if not getattr(sys, "frozen", False):
            return False
    except Exception:
        return False

    # Allow disabling by env var
    v = os.environ.get("MIMISTOCK_NO_UPDATE", "").strip().lower()
    return v not in {"1", "true", "yes"}
