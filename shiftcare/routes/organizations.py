"""Routes: organizations for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from schemas import CloudOrganizationImportRequest
from schemas import CloudOrganizationLinkRequest
from shiftcare import config as app_constants
from shiftcare.services import audit as services_audit
from shiftcare.services import authentication as services_authentication
from shiftcare.services import backups as services_backups
from shiftcare.services import bundles as services_bundles
from shiftcare.services import common as services_common
from shiftcare.services import cloud_client as services_cloud_client
from shiftcare.services import desktop_session as services_desktop_session
from shiftcare.services import licensing as services_licensing
from shiftcare.services import memberships as services_memberships
from shiftcare.services import runtime as services_runtime
import database
import sqlite3
from sync_policy import canonical_snapshot

router = APIRouter()


@router.get("/api/organizations", tags=["Auth"])
def get_user_organizations(current_user: dict = Depends(services_authentication.get_current_user)):
    return {"organizations": current_user["memberships"]}


@router.get("/api/organizations/{organization_id}/cloud-export", tags=["Auth"])
def export_organization_for_cloud(organization_id: int, current_user: dict = Depends(services_authentication.get_current_user)):
    services_licensing.require_not_demo("Cloud export")
    membership = services_authentication.require_organization_role(current_user, organization_id, app_constants.DESKTOP_CLOUD_SYNC_ROLES)
    connection = database.get_connection()
    try:
        services_bundles.begin_organization_export_snapshot(connection)
        if services_memberships.get_allowed_department_ids(connection.cursor(), {"user": current_user, "membership": membership}) is not None:
            raise HTTPException(status_code=403, detail="Organization synchronization requires access to all departments")
        return services_bundles.build_organization_export_bundle(connection, organization_id, exported_by_user_id=current_user["id"])
    finally:
        connection.close()


@router.post("/api/organizations/{organization_id}/cloud-import", tags=["Auth"])
def import_organization_from_cloud_bundle(
    organization_id: int,
    request_data: CloudOrganizationImportRequest,
    current_user: dict = Depends(services_authentication.get_current_user),
):
    services_licensing.require_not_demo("Cloud import")
    membership = services_authentication.require_organization_role(current_user, organization_id, {"owner", "admin"})
    connection = database.get_connection()
    try:
        services_bundles.lock_organization_sync_snapshot(connection, organization_id)
        if services_memberships.get_allowed_department_ids(connection.cursor(), {"user": current_user, "membership": membership}) is not None:
            raise HTTPException(status_code=403, detail="Organization synchronization requires access to all departments")
        current_bundle = services_bundles.build_organization_export_bundle(connection, organization_id)
        if (request_data.bundle.get("sync") or {}).get("initial_link"):
            if not services_bundles.organization_bundle_is_pristine(connection, current_bundle) and canonical_snapshot(request_data.bundle) != canonical_snapshot(current_bundle):
                raise HTTPException(status_code=409, detail="This cloud organization already contains different data. Initial linking cannot replace it; review both copies first.")
        expected_revision = (request_data.bundle.get("sync") or {}).get("base_revision") or request_data.bundle.get("sync_revision")
        if expected_revision != current_bundle["sync_revision"]:
            raise HTTPException(
                status_code=409,
                detail="The organization changed or this desktop uses an unsafe sync protocol. Refresh and merge before retrying.",
            )
        backup_name = services_backups.create_recovery_backup("cloud_import")
        result = services_bundles.import_organization_bundle(
            connection,
            organization_id,
            request_data.bundle,
            request_data.replace_existing,
            imported_by_user_id=current_user["id"],
        )
        accepted_bundle = services_bundles.build_organization_export_bundle(connection, organization_id)
        connection.commit()
        return {"message": "Organization imported successfully", "backup_name": backup_name, **result, "sync_bundle": accepted_bundle}
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise HTTPException(status_code=409, detail=f"Organization import conflict: {exc}") from exc
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.post("/api/organizations/{organization_id}/cloud-link", tags=["Auth"])
def save_organization_cloud_link(
    organization_id: int,
    request_data: CloudOrganizationLinkRequest,
    current_user: dict = Depends(services_authentication.get_current_user),
):
    services_licensing.require_not_demo("Cloud link")
    services_authentication.require_organization_role(current_user, organization_id, {"owner", "admin"})
    cloud_base_url = services_runtime.normalize_public_app_base_url(request_data.cloud_api_base_url)
    if not cloud_base_url:
        raise HTTPException(status_code=400, detail="Invalid Cloud API base URL")
    if request_data.cloud_access_token and request_data.sync_bundle:
        if not services_cloud_client.is_desktop_sqlite_runtime() or organization_id != 1:
            raise HTTPException(status_code=409, detail="Desktop synchronization links must be saved in the local workspace")
        return services_desktop_session.finalize_initial_cloud_link(request_data, current_user)
    linked_at = request_data.linked_at or services_common.current_utc_timestamp()
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        services_common.fetch_one_or_404(cursor, "SELECT id FROM organizations WHERE id = ?", (organization_id,), "Organization not found")
        for key, value in {
            "cloud_api_base_url": cloud_base_url,
            "cloud_organization_id": str(request_data.cloud_organization_id),
            "cloud_organization_public_id": request_data.cloud_organization_public_id,
            "cloud_linked_at": linked_at,
        }.items():
            cursor.execute(
                """
                INSERT INTO app_settings (organization_id, key, value)
                VALUES (?, ?, ?)
                ON CONFLICT(organization_id, key) DO UPDATE SET value = excluded.value
                """,
                (organization_id, key, value),
            )
        services_audit.write_auth_audit_event(
            cursor,
            "organization_cloud_linked",
            user_id=current_user["id"],
            organization_id=organization_id,
            metadata={
                "cloud_api_base_url": cloud_base_url,
                "cloud_organization_id": request_data.cloud_organization_id,
                "cloud_organization_public_id": request_data.cloud_organization_public_id,
            },
        )
        connection.commit()
        return {
            "message": "Cloud link saved",
            "cloud_api_base_url": cloud_base_url,
            "cloud_organization_id": request_data.cloud_organization_id,
            "cloud_organization_public_id": request_data.cloud_organization_public_id,
            "linked_at": linked_at,
        }
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.get("/api/organizations/{organization_id}/cloud-link", tags=["Auth"])
def get_organization_cloud_link(organization_id: int, current_user: dict = Depends(services_authentication.get_current_user)):
    services_authentication.require_organization_role(current_user, organization_id, {"owner", "admin", "scheduler", "manager"})
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        services_common.fetch_one_or_404(cursor, "SELECT id FROM organizations WHERE id = ?", (organization_id,), "Organization not found")
        settings = services_runtime.read_organization_cloud_link_settings(cursor, organization_id)
        cloud_organization_id = settings.get("cloud_organization_id")
        return {
            "linked": services_runtime.organization_has_cloud_link(settings),
            "cloud_api_base_url": settings.get("cloud_api_base_url") or "",
            "cloud_organization_id": int(cloud_organization_id) if cloud_organization_id else None,
            "cloud_organization_public_id": settings.get("cloud_organization_public_id") or "",
            "linked_at": settings.get("cloud_linked_at") or "",
        }
    finally:
        connection.close()


@router.delete("/api/organizations/{organization_id}/cloud-link", tags=["Auth"])
def delete_organization_cloud_link(organization_id: int, current_user: dict = Depends(services_authentication.get_current_user)):
    services_licensing.require_not_demo("Cloud link")
    services_authentication.require_organization_role(current_user, organization_id, {"owner", "admin"})
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        services_common.fetch_one_or_404(cursor, "SELECT id FROM organizations WHERE id = ?", (organization_id,), "Organization not found")
        cursor.execute(
            """
            DELETE FROM app_settings
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
        services_audit.write_auth_audit_event(
            cursor,
            "organization_cloud_unlinked",
            user_id=current_user["id"],
            organization_id=organization_id,
        )
        connection.commit()
        return {"message": "Cloud link removed"}
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()
