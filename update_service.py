from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from fastapi import HTTPException


GITHUB_REPO_OWNER = "LittleDespairs"
GITHUB_REPO_NAME = "Schedule_app_releases"
GITHUB_RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases"
GITHUB_RELEASE_ASSET_PATTERN = re.compile(
    r"^(?:ScheduleApp|ShiftCare)_Setup_(?P<version>\d+\.\d+\.\d+(?:[-_][A-Za-z0-9.]+)?)\.exe$"
)


def normalize_version(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized.startswith("v"):
        normalized = normalized[1:]
    return normalized.replace("_", "-")


def version_sort_key(value: str) -> tuple[int, int, int, int]:
    normalized = normalize_version(value)
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", normalized)
    if not match:
        return 0, 0, 0, 0

    major, minor, patch = (int(part) for part in match.groups())
    stability = 0 if any(label in normalized for label in ("alpha", "beta", "rc")) else 1
    return major, minor, patch, stability


def is_newer_version(candidate: str, current: str) -> bool:
    return version_sort_key(candidate) > version_sort_key(current)


def request_github_releases(app_version: str) -> list[dict]:
    request = urllib.request.Request(
        GITHUB_RELEASES_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"ShiftCare/{app_version}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Could not contact GitHub Releases: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="GitHub Releases returned invalid JSON") from exc


def release_asset_version(asset_name: str) -> str | None:
    match = GITHUB_RELEASE_ASSET_PATTERN.match(asset_name or "")
    if not match:
        return None
    return normalize_version(match.group("version"))


def find_latest_installable_release(releases: list[dict]) -> dict | None:
    candidates: list[dict] = []
    for release in releases:
        if release.get("draft"):
            continue

        release_version = normalize_version(release.get("tag_name") or release.get("name") or "")
        for asset in release.get("assets") or []:
            asset_version = release_asset_version(asset.get("name", ""))
            if not asset_version:
                continue

            candidates.append(
                {
                    "version": asset_version or release_version,
                    "release_name": release.get("name") or release.get("tag_name") or asset_version,
                    "tag_name": release.get("tag_name") or "",
                    "body": release.get("body") or "",
                    "published_at": release.get("published_at") or "",
                    "asset_name": asset.get("name") or "",
                    "download_url": asset.get("browser_download_url") or "",
                    "size_bytes": asset.get("size") or 0,
                    "html_url": release.get("html_url") or "",
                    "prerelease": bool(release.get("prerelease")),
                }
            )

    if not candidates:
        return None

    return max(candidates, key=lambda candidate: version_sort_key(candidate["version"]))


def no_store_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }


def validate_release_download_url(download_url: str) -> None:
    parsed = urlparse(download_url)
    if parsed.scheme != "https":
        raise HTTPException(status_code=400, detail="Update download URL must use HTTPS")

    if parsed.netloc.lower() not in {"github.com", "objects.githubusercontent.com"}:
        raise HTTPException(status_code=400, detail="Update download URL is not a GitHub release asset")


def download_update_installer(download_url: str, asset_name: str, app_version: str) -> Path:
    validate_release_download_url(download_url)
    safe_asset_name = Path(asset_name).name
    if not release_asset_version(safe_asset_name):
        raise HTTPException(status_code=400, detail="Release asset is not a ShiftCare installer")

    target_dir = Path(tempfile.gettempdir()) / "ShiftCare" / "updates"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / safe_asset_name

    request = urllib.request.Request(
        download_url,
        headers={"User-Agent": f"ShiftCare/{app_version}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response, target_path.open("wb") as output_file:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output_file.write(chunk)
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Could not download update: {exc}") from exc

    return target_path


def schedule_desktop_shutdown(delay_seconds: float = 2.0) -> None:
    if not getattr(sys, "frozen", False):
        return

    def delayed_exit() -> None:
        import time as time_module

        time_module.sleep(delay_seconds)
        os._exit(0)

    threading.Thread(target=delayed_exit, daemon=True).start()
