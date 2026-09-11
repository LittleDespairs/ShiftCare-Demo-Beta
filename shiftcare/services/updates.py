"""Services: updates for ShiftCare."""
from __future__ import annotations

from fastapi import HTTPException
from pathlib import Path
from shiftcare import config as app_constants
from shiftcare.services import cloud_client as services_cloud_client
from shiftcare.services import runtime as services_runtime
import database
import json
import update_service

def is_newer_version(candidate: str, current: str | None = None) -> bool:
    return update_service.is_newer_version(candidate, current or app_constants.APP_VERSION)


def request_github_releases() -> list[dict]:
    return update_service.request_github_releases(app_constants.APP_VERSION)


def request_demo_github_releases() -> list[dict]:
    return update_service.request_github_releases(app_constants.APP_VERSION, update_service.GITHUB_DEMO_REPO_NAME)


def update_notifications_are_enabled() -> bool:
    return services_cloud_client.is_desktop_sqlite_runtime() and not services_runtime.is_demo_mode_enabled()


def upsert_local_app_setting(cursor, key: str, value: str, organization_id: int = 1) -> None:
    cursor.execute(
        """
        INSERT INTO app_settings (organization_id, key, value)
        VALUES (?, ?, ?)
        ON CONFLICT(organization_id, key)
        DO UPDATE SET organization_id = excluded.organization_id,
                      value = excluded.value
        """,
        (organization_id, key, value),
    )


def read_local_app_settings(cursor, keys: set[str], organization_id: int = 1) -> dict[str, str]:
    if not keys:
        return {}
    placeholders = ",".join(["?"] * len(keys))
    cursor.execute(
        f"""
        SELECT key, value
        FROM app_settings
        WHERE organization_id = ? AND key IN ({placeholders})
        """,
        (organization_id, *sorted(keys)),
    )
    return {str(row["key"]): str(row["value"] or "") for row in cursor.fetchall()}


def update_changelog_payload_from_release(release: dict) -> dict:
    body = str(release.get("body") or "")
    summary = release.get("changelog_summary")
    if not isinstance(summary, list):
        summary = update_service.summarize_release_notes(body)
    return {
        "version": release.get("version") or "",
        "release_name": release.get("release_name") or release.get("tag_name") or release.get("version") or "",
        "body": body,
        "summary": [str(item) for item in summary if str(item).strip()],
        "html_url": release.get("html_url") or "",
        "published_at": release.get("published_at") or "",
    }


def remember_pending_update_changelog(release: dict) -> None:
    if not update_notifications_are_enabled():
        return
    payload = update_changelog_payload_from_release(release)
    if not payload["version"]:
        return

    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        upsert_local_app_setting(cursor, app_constants.PENDING_UPDATE_CHANGELOG_VERSION_KEY, update_service.normalize_version(payload["version"]))
        upsert_local_app_setting(cursor, app_constants.PENDING_UPDATE_CHANGELOG_NAME_KEY, str(payload["release_name"] or payload["version"]))
        upsert_local_app_setting(cursor, app_constants.PENDING_UPDATE_CHANGELOG_BODY_KEY, payload["body"])
        upsert_local_app_setting(cursor, app_constants.PENDING_UPDATE_CHANGELOG_SUMMARY_KEY, json.dumps(payload["summary"]))
        connection.commit()
    finally:
        connection.close()


def read_pending_update_changelog() -> dict | None:
    if not update_notifications_are_enabled():
        return None
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        settings = read_local_app_settings(
            cursor,
            {
                app_constants.PENDING_UPDATE_CHANGELOG_VERSION_KEY,
                app_constants.PENDING_UPDATE_CHANGELOG_NAME_KEY,
                app_constants.PENDING_UPDATE_CHANGELOG_BODY_KEY,
                app_constants.PENDING_UPDATE_CHANGELOG_SUMMARY_KEY,
                app_constants.UPDATE_CHANGELOG_SEEN_VERSION_KEY,
            },
        )
    finally:
        connection.close()

    pending_version = settings.get(app_constants.PENDING_UPDATE_CHANGELOG_VERSION_KEY) or ""
    if not pending_version or update_service.normalize_version(pending_version) != update_service.normalize_version(app_constants.APP_VERSION):
        return None
    if update_service.normalize_version(settings.get(app_constants.UPDATE_CHANGELOG_SEEN_VERSION_KEY) or "") == update_service.normalize_version(app_constants.APP_VERSION):
        return None

    body = settings.get(app_constants.PENDING_UPDATE_CHANGELOG_BODY_KEY) or ""
    try:
        summary = json.loads(settings.get(app_constants.PENDING_UPDATE_CHANGELOG_SUMMARY_KEY) or "[]")
    except json.JSONDecodeError:
        summary = []
    if not isinstance(summary, list) or not summary:
        summary = update_service.summarize_release_notes(body)

    return {
        "version": app_constants.APP_VERSION,
        "release_name": settings.get(app_constants.PENDING_UPDATE_CHANGELOG_NAME_KEY) or app_constants.APP_VERSION,
        "summary": [str(item) for item in summary if str(item).strip()],
        "body": body,
    }


def mark_update_changelog_seen() -> None:
    if not update_notifications_are_enabled():
        return
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        upsert_local_app_setting(cursor, app_constants.UPDATE_CHANGELOG_SEEN_VERSION_KEY, update_service.normalize_version(app_constants.APP_VERSION))
        cursor.execute(
            """
            DELETE FROM app_settings
            WHERE organization_id = 1
              AND key IN (?, ?, ?, ?)
            """,
            (
                app_constants.PENDING_UPDATE_CHANGELOG_VERSION_KEY,
                app_constants.PENDING_UPDATE_CHANGELOG_NAME_KEY,
                app_constants.PENDING_UPDATE_CHANGELOG_BODY_KEY,
                app_constants.PENDING_UPDATE_CHANGELOG_SUMMARY_KEY,
            ),
        )
        connection.commit()
    finally:
        connection.close()


def get_update_status() -> dict:
    latest_release = update_service.find_latest_installable_release(request_github_releases())
    if latest_release is None:
        return {
            "current_version": app_constants.APP_VERSION,
            "update_available": False,
            "message": "No installable Windows release asset was found.",
        }

    return {
        "current_version": app_constants.APP_VERSION,
        "update_available": is_newer_version(latest_release["version"]),
        "latest": latest_release,
    }


def get_latest_download_payload() -> dict:
    latest_release = update_service.find_latest_installable_release(request_github_releases())
    if latest_release is None:
        raise HTTPException(status_code=404, detail="No installable Windows release asset was found.")
    return {
        "product": "ShiftCare",
        "latest": latest_release,
    }


def get_latest_demo_download_payload() -> dict:
    latest_release = update_service.find_latest_installable_release(request_demo_github_releases())
    if latest_release is None:
        raise HTTPException(status_code=404, detail="No installable ShiftCare Demo Windows release asset was found.")
    return {
        "product": "ShiftCare Demo",
        "latest": latest_release,
    }


def download_update_installer(download_url: str, asset_name: str) -> Path:
    return update_service.download_update_installer(download_url, asset_name, app_constants.APP_VERSION)
