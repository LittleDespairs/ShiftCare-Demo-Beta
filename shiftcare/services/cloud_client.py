"""Services: cloud client for ShiftCare."""
from __future__ import annotations

from fastapi import HTTPException
from fastapi import Request
from shiftcare import config as app_constants
from shiftcare.services import common as services_common
from shiftcare.services import runtime as services_runtime
from time import sleep
import app_config
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request

def get_desktop_cloud_login_base_url() -> str:
    configured_url = services_runtime.normalize_public_app_base_url(os.environ.get("SCHEDULE_APP_CLOUD_LOGIN_BASE_URL", ""))
    return configured_url or app_constants.DESKTOP_CLOUD_LOGIN_BASE_URL


def is_desktop_sqlite_runtime() -> bool:
    config = app_config.get_app_config()
    return not config.is_deployed_env and config.database_engine.strip().lower() == "sqlite"


def read_desktop_cloud_sync_settings(cursor: sqlite3.Cursor, organization_id: int) -> dict[str, str]:
    cursor.execute(
        """
        SELECT key, value
        FROM app_settings
        WHERE organization_id = ?
          AND key IN (
              'cloud_api_base_url',
              'cloud_organization_id',
              'cloud_organization_public_id',
              'desktop_cloud_access_token'
          )
        """,
        (organization_id,),
    )
    return {row["key"]: row["value"] for row in cursor.fetchall()}


def desktop_cloud_sync_is_ready(settings: dict[str, str]) -> bool:
    return bool(
        settings.get("cloud_api_base_url")
        and settings.get("cloud_organization_id")
        and settings.get("desktop_cloud_access_token")
    )


def is_desktop_invitation_request(request: Request) -> bool:
    hostname = request.url.hostname or ""
    return getattr(sys, "frozen", False) or hostname in {"127.0.0.1", "localhost", "::1"}


def get_cloud_request_timeout_seconds() -> float:
    try:
        return max(5.0, float(os.environ.get("SCHEDULE_APP_CLOUD_REQUEST_TIMEOUT_SECONDS", "45")))
    except ValueError:
        return 45.0


def get_cloud_request_max_attempts() -> int:
    try:
        return min(5, max(1, int(os.environ.get("SCHEDULE_APP_CLOUD_REQUEST_MAX_ATTEMPTS", "3"))))
    except ValueError:
        return 3


def parse_retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, min(30.0, float(value)))
    except ValueError:
        return None


def get_cloud_retry_delay_seconds(attempt: int, retry_after: str | None = None) -> float:
    parsed_retry_after = parse_retry_after_seconds(retry_after)
    if parsed_retry_after is not None:
        return parsed_retry_after
    return min(8.0, 1.0 * (2 ** attempt))


def request_cloud_json(
    base_url: str,
    path: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    token: str = "",
    extra_headers: dict[str, str] | None = None,
) -> dict:
    normalized_base = services_runtime.normalize_public_app_base_url(base_url)
    if not normalized_base:
        raise HTTPException(status_code=500, detail="Cloud login base URL is not configured")
    url = f"{normalized_base}{path if path.startswith('/') else f'/{path}'}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    headers.update(extra_headers or {})
    raw = ""
    last_network_error: Exception | None = None
    max_attempts = get_cloud_request_max_attempts()
    timeout_seconds = get_cloud_request_timeout_seconds()
    for attempt in range(max_attempts):
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read().decode("utf-8")
            break
        except urllib.error.HTTPError as exc:
            try:
                error_payload = json.loads(exc.read().decode("utf-8") or "{}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                error_payload = {}
            detail = error_payload.get("detail") or f"Cloud request failed with {exc.code}"
            if exc.code in app_constants.RETRYABLE_CLOUD_STATUS_CODES and attempt < max_attempts - 1:
                sleep(get_cloud_retry_delay_seconds(attempt, exc.headers.get("Retry-After")))
                continue
            raise HTTPException(status_code=exc.code, detail=detail) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_network_error = exc
            if attempt < max_attempts - 1:
                sleep(get_cloud_retry_delay_seconds(attempt))
                continue
            raise HTTPException(status_code=503, detail=f"Cloud is not reachable: {exc}") from exc
    if last_network_error and not raw:
        raise HTTPException(status_code=503, detail=f"Cloud is not reachable: {last_network_error}")
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Cloud returned an invalid JSON response") from exc


def select_desktop_cloud_membership(cloud_user: dict) -> dict:
    memberships = [
        membership
        for membership in cloud_user.get("memberships") or []
        if membership.get("status") == "active" and membership.get("role") in {"owner", "admin"}
    ]
    if not memberships:
        raise HTTPException(
            status_code=403,
            detail="Desktop synchronization of a complete organization requires an owner or administrator account. Scheduler and manager accounts can continue using the portal.",
        )
    return memberships[0]


def upsert_desktop_cloud_user(cursor: sqlite3.Cursor, cloud_user: dict, cloud_membership: dict, organization_id: int) -> int:
    now = services_common.current_utc_timestamp()
    email = str(cloud_user.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=502, detail="Cloud user response is missing email")
    cursor.execute("SELECT id FROM users WHERE lower(email) = ?", (email,))
    row = cursor.fetchone()
    if row:
        user_id = int(row["id"])
        cursor.execute(
            """
            UPDATE users
            SET full_name = ?, status = 'active', email_verified = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                cloud_user.get("full_name") or email,
                int(bool(cloud_user.get("email_verified"))),
                now,
                user_id,
            ),
        )
    else:
        cursor.execute(
            """
            INSERT INTO users (email, full_name, password_hash, status, email_verified, created_at, updated_at)
            VALUES (?, ?, NULL, 'active', ?, ?, ?)
            """,
            (
                email,
                cloud_user.get("full_name") or email,
                int(bool(cloud_user.get("email_verified"))),
                now,
                now,
            ),
        )
        user_id = int(cursor.lastrowid)
    cursor.execute(
        """
        INSERT INTO organization_memberships (organization_id, user_id, role, status, employee_id, created_at, updated_at)
        VALUES (?, ?, ?, 'active', NULL, ?, ?)
        ON CONFLICT(organization_id, user_id)
        DO UPDATE SET role = excluded.role,
                      status = excluded.status,
                      employee_id = NULL,
                      updated_at = excluded.updated_at
        """,
        (organization_id, user_id, cloud_membership.get("role") or "scheduler", now, now),
    )
    return user_id
