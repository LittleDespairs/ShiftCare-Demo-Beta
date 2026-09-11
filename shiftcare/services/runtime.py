"""Services: runtime for ShiftCare."""
from __future__ import annotations

from fastapi import Request
from pathlib import Path
from shiftcare import config as app_constants
from urllib.parse import quote
from urllib.parse import urlparse
import app_config
import os
import sqlite3

def is_developer_mode_enabled() -> bool:
    if os.environ.get("SCHEDULE_APP_DEVELOPER_MODE", "").strip().lower() in app_constants.TRUTHY_ENV_VALUES:
        return True
    app_data_root = os.environ.get("LOCALAPPDATA", "").strip()
    if not app_data_root:
        return False
    return (Path(app_data_root) / "Schedule App" / "developer_mode.flag").exists()


def is_demo_mode_enabled() -> bool:
    return app_constants.APP_DEMO_MODE


def is_license_bypass_enabled() -> bool:
    config = app_config.get_app_config()
    if config.is_deployed_env:
        return False
    if not is_developer_mode_enabled():
        return False
    return os.environ.get("SCHEDULE_APP_LICENSE_BYPASS", "").strip().lower() in app_constants.TRUTHY_ENV_VALUES


def is_cloud_employee_portal_mode() -> bool:
    return app_config.get_app_config().is_deployed_env


def is_trusted_desktop_cloud_request(request: Request) -> bool:
    return request.headers.get("X-ShiftCare-Desktop-Client", "").strip().lower() in app_constants.TRUTHY_ENV_VALUES


def normalize_public_app_base_url(value: str) -> str:
    trimmed = (value or "").strip().rstrip("/")
    if not trimmed:
        return ""
    parsed = urlparse(trimmed)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def get_public_app_base_url() -> str:
    config = app_config.get_app_config()
    configured_url = normalize_public_app_base_url(config.public_app_base_url)
    if configured_url:
        return configured_url
    if config.is_deployed_env:
        return app_constants.DEFAULT_CLOUD_API_BASE_URL
    return app_constants.DEFAULT_PUBLIC_APP_BASE_URL


def build_public_app_url(path: str) -> str:
    base_url = get_public_app_base_url()
    if not base_url:
        return ""
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{base_url}{normalized_path}"


def build_invitation_url(invitation_token: str) -> str:
    return build_public_app_url(f"/accept-invitation?token={quote(invitation_token)}")


def build_password_reset_url(reset_token: str) -> str:
    return build_public_app_url(f"/reset-password?token={quote(reset_token)}")


def build_email_verification_url(verification_token: str) -> str:
    return build_public_app_url(f"/verify-email?token={quote(verification_token)}")


def build_invitation_url_for_request(request: Request | None, invitation_token: str) -> str:
    configured_url = build_invitation_url(invitation_token)
    if configured_url:
        return configured_url
    if request:
        parsed = urlparse(str(request.base_url))
        if parsed.hostname and parsed.hostname not in {"127.0.0.1", "localhost", "::1", "testserver"}:
            return f"{parsed.scheme}://{parsed.netloc}/accept-invitation?token={quote(invitation_token)}"
    return f"/accept-invitation?token={quote(invitation_token)}"


def build_password_reset_url_for_request(request: Request | None, reset_token: str) -> str:
    configured_url = build_password_reset_url(reset_token)
    if configured_url:
        return configured_url
    if request:
        parsed = urlparse(str(request.base_url))
        if parsed.hostname and parsed.hostname not in {"127.0.0.1", "localhost", "::1", "testserver"}:
            return f"{parsed.scheme}://{parsed.netloc}/reset-password?token={quote(reset_token)}"
    return f"/reset-password?token={quote(reset_token)}"


def build_email_verification_url_for_request(request: Request | None, verification_token: str) -> str:
    configured_url = build_email_verification_url(verification_token)
    if configured_url:
        return configured_url
    if request:
        parsed = urlparse(str(request.base_url))
        if parsed.hostname and parsed.hostname not in {"127.0.0.1", "localhost", "::1", "testserver"}:
            return f"{parsed.scheme}://{parsed.netloc}/verify-email?token={quote(verification_token)}"
    return f"/verify-email?token={quote(verification_token)}"


def read_organization_cloud_link_settings(cursor: sqlite3.Cursor, organization_id: int) -> dict:
    cursor.execute(
        """
        SELECT key, value
        FROM app_settings
        WHERE organization_id = ?
          AND key IN (
              'cloud_api_base_url',
              'cloud_organization_id',
              'cloud_organization_public_id',
              'cloud_linked_at'
          )
        """,
        (organization_id,),
    )
    return {row["key"]: row["value"] for row in cursor.fetchall()}


def organization_has_cloud_link(settings: dict) -> bool:
    return bool(settings.get("cloud_api_base_url") and settings.get("cloud_organization_id"))


def build_linked_organization_invitation_url(
    cursor: sqlite3.Cursor,
    organization_id: int,
    invitation_token: str,
) -> str:
    return build_invitation_url(invitation_token)
