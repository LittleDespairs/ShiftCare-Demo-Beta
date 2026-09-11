"""Routes: desktop sync for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from schemas import AuthOrganizationCreateRequest
from schemas import DesktopCloudLoginRequest
from shiftcare import config as app_constants
from shiftcare.services import authentication as services_authentication
from shiftcare.services import cloud_client as services_cloud_client
from shiftcare.services import desktop_session as services_desktop_session
from shiftcare.services import licensing as services_licensing
from shiftcare.services import runtime as services_runtime
import database

router = APIRouter()


@router.post("/api/desktop/cloud-login", tags=["Auth"])
def desktop_cloud_login(request_data: DesktopCloudLoginRequest):
    services_licensing.require_not_demo("Cloud login")
    if not services_cloud_client.is_desktop_sqlite_runtime():
        raise HTTPException(status_code=404, detail="Desktop cloud login is available only in the installed SQLite app")

    cloud_base_url = services_cloud_client.get_desktop_cloud_login_base_url()
    cloud_session = services_cloud_client.request_cloud_json(
        cloud_base_url,
        "/api/auth/login",
        method="POST",
        payload={"email": str(request_data.email), "password": request_data.password},
    )
    return services_desktop_session.import_cloud_session_to_desktop(cloud_base_url, cloud_session)


@router.post("/api/desktop/cloud-create-organization", tags=["Auth"])
def desktop_cloud_create_organization(request_data: AuthOrganizationCreateRequest):
    services_licensing.require_not_demo("Cloud organization setup")
    if not services_cloud_client.is_desktop_sqlite_runtime():
        raise HTTPException(status_code=404, detail="Desktop organization setup is available only in the installed SQLite app")
    cloud_base_url = services_cloud_client.get_desktop_cloud_login_base_url()
    cloud_session = services_cloud_client.request_cloud_json(
        cloud_base_url,
        "/api/auth/create-organization",
        method="POST",
        payload=request_data.model_dump(mode="json"),
        extra_headers={"X-ShiftCare-Desktop-Client": "1"},
    )
    return services_desktop_session.import_cloud_session_to_desktop(cloud_base_url, cloud_session)


@router.get("/api/desktop/sync/status", tags=["Auth"])
def desktop_sync_status(current_user: dict = Depends(services_authentication.get_current_user)):
    if not services_cloud_client.is_desktop_sqlite_runtime():
        raise HTTPException(status_code=404, detail="Desktop sync status is available only in the installed SQLite app")
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        membership = services_authentication.find_any_membership_with_role(current_user, app_constants.DESKTOP_CLOUD_SYNC_ROLES)
        if not membership:
            raise HTTPException(status_code=403, detail="Desktop scheduling permissions are required")
        organization_id = int(membership["organization_id"])
        settings = services_runtime.read_organization_cloud_link_settings(cursor, organization_id)
        cursor.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM desktop_sync_outbox
            WHERE organization_id = ?
            GROUP BY status
            """,
            (organization_id,),
        )
        queue_counts = {row["status"]: row["count"] for row in cursor.fetchall()}
        cursor.execute(
            """
            SELECT value
            FROM app_settings
            WHERE organization_id = ? AND key = 'desktop_cloud_last_pull_at'
            """,
            (organization_id,),
        )
        last_pull_row = cursor.fetchone()
        return {
            "linked": services_runtime.organization_has_cloud_link(settings),
            "cloud_api_base_url": settings.get("cloud_api_base_url") or "",
            "cloud_organization_id": int(settings["cloud_organization_id"]) if settings.get("cloud_organization_id") else None,
            "cloud_organization_public_id": settings.get("cloud_organization_public_id") or "",
            "last_pull_at": last_pull_row["value"] if last_pull_row else "",
            "queue": {
                "pending": int(queue_counts.get("pending", 0)),
                "syncing": int(queue_counts.get("syncing", 0)),
                "failed": int(queue_counts.get("failed", 0)),
                "synced": int(queue_counts.get("synced", 0)),
            },
        }
    finally:
        connection.close()
