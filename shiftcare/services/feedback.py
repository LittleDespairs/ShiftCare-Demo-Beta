"""Services: feedback for ShiftCare."""
from __future__ import annotations

from fastapi import HTTPException
from fastapi import Request
from schemas import FeedbackReportCreate
from shiftcare import config as app_constants
from shiftcare.services import authentication as services_authentication
from shiftcare.services import cloud_client as services_cloud_client
from shiftcare.services import common as services_common
from shiftcare.services import runtime as services_runtime
from typing import Any
import app_config
import json
import secrets

def feedback_membership_for_user(current_user: dict, organization_id: int | None) -> dict:
    active_memberships = [
        membership
        for membership in current_user.get("memberships", [])
        if membership.get("status") == "active"
    ]
    if organization_id:
        membership = next(
            (item for item in active_memberships if int(item.get("organization_id") or 0) == organization_id),
            None,
        )
        if not membership:
            raise HTTPException(status_code=403, detail="Active organization access is required")
        return membership
    if not active_memberships:
        raise HTTPException(status_code=403, detail="Active organization access is required")
    return active_memberships[0]


def serialize_feedback_context(value: Any, max_chars: int = 12000) -> str:
    payload = value if isinstance(value, dict) else {"value": value}
    try:
        serialized = json.dumps(payload, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        serialized = json.dumps({"unserializable": True}, ensure_ascii=False)
    if len(serialized) <= max_chars:
        return serialized
    return json.dumps(
        {
            "truncated": True,
            "original_length": len(serialized),
            "preview": serialized[: max_chars - 120],
        },
        ensure_ascii=False,
    )


def feedback_runtime_environment() -> str:
    config = app_config.get_app_config()
    if services_runtime.is_demo_mode_enabled():
        return "demo"
    if services_cloud_client.is_desktop_sqlite_runtime():
        return "desktop"
    if config.is_cloud_run:
        return "cloud_run"
    return config.app_env or "development"


def insert_feedback_report(
    cursor,
    request_data: FeedbackReportCreate,
    request: Request,
    current_user: dict,
    membership: dict,
) -> dict:
    now = services_common.current_utc_timestamp()
    public_id = f"fbr_{secrets.token_hex(16)}"
    user_id = int(current_user["id"]) if int(current_user.get("id") or 0) > 0 else None
    organization_id = int(membership["organization_id"])
    contact_email = str(request_data.contact_email or current_user.get("email") or "").strip() or None
    server_context = {
        "request_ip": services_authentication.get_request_ip(request),
        "user_agent": request.headers.get("user-agent", ""),
        "source_public_id": request_data.source_public_id,
        "database_engine": app_config.get_app_config().database_engine,
        "is_desktop_sqlite_runtime": services_cloud_client.is_desktop_sqlite_runtime(),
        "is_cloud_run": app_config.get_app_config().is_cloud_run,
        "demo_mode": services_runtime.is_demo_mode_enabled(),
    }
    client_context_json = serialize_feedback_context(request_data.client_context)
    server_context_json = serialize_feedback_context(server_context)
    cursor.execute(
        """
        INSERT INTO feedback_reports (
            public_id, organization_id, user_id, report_type, status, severity, area,
            title, description, steps_to_reproduce, expected_result, actual_result,
            contact_email, page_url, app_version, runtime_environment,
            client_context_json, server_context_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            public_id,
            organization_id,
            user_id,
            request_data.report_type,
            request_data.severity,
            request_data.area,
            request_data.title,
            request_data.description,
            request_data.steps_to_reproduce,
            request_data.expected_result,
            request_data.actual_result,
            contact_email,
            request_data.page_url,
            app_constants.APP_VERSION,
            feedback_runtime_environment(),
            client_context_json,
            server_context_json,
            now,
            now,
        ),
    )
    return {
        "id": cursor.lastrowid,
        "public_id": public_id,
        "organization_id": organization_id,
        "user_id": user_id,
        "report_type": request_data.report_type,
        "status": "new",
        "severity": request_data.severity,
        "area": request_data.area,
        "title": request_data.title,
        "description": request_data.description,
        "steps_to_reproduce": request_data.steps_to_reproduce,
        "expected_result": request_data.expected_result,
        "actual_result": request_data.actual_result,
        "contact_email": contact_email,
        "page_url": request_data.page_url,
        "app_version": app_constants.APP_VERSION,
        "runtime_environment": feedback_runtime_environment(),
        "client_context_json": client_context_json,
        "server_context_json": server_context_json,
        "created_at": now,
        "updated_at": now,
        "user_name": current_user.get("full_name") or "",
        "user_email": current_user.get("email") or "",
        "organization_name": membership.get("organization_name") or "",
        "role": membership.get("role") or "",
    }


def update_feedback_notification_status(
    cursor,
    public_id: str,
    status: str,
    detail: str = "",
    *,
    forwarded: bool = False,
) -> None:
    now = services_common.current_utc_timestamp()
    if forwarded:
        cursor.execute(
            """
            UPDATE feedback_reports
            SET notification_status = ?,
                notification_detail = ?,
                forwarded_at = ?,
                updated_at = ?
            WHERE public_id = ?
            """,
            (status, detail[:500] if detail else None, now, now, public_id),
        )
        return
    cursor.execute(
        """
        UPDATE feedback_reports
        SET notification_status = ?,
            notification_detail = ?,
            updated_at = ?
        WHERE public_id = ?
        """,
        (status, detail[:500] if detail else None, now, public_id),
    )


def forward_desktop_feedback_to_cloud(
    cursor,
    report: dict,
    request_data: FeedbackReportCreate,
    membership: dict,
) -> dict[str, Any] | None:
    if not services_cloud_client.is_desktop_sqlite_runtime():
        return None
    settings = services_cloud_client.read_desktop_cloud_sync_settings(cursor, int(membership["organization_id"]))
    if not services_cloud_client.desktop_cloud_sync_is_ready(settings):
        return None
    payload = request_data.model_dump(mode="json")
    payload["organization_id"] = int(settings["cloud_organization_id"])
    payload["source_public_id"] = report["public_id"]
    return services_cloud_client.request_cloud_json(
        settings["cloud_api_base_url"],
        "/api/feedback/reports",
        method="POST",
        payload=payload,
        token=settings["desktop_cloud_access_token"],
    )
