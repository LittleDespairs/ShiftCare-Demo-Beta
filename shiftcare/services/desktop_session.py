"""Services: desktop session for ShiftCare."""
from __future__ import annotations

from fastapi import HTTPException
from shiftcare.services import authentication as services_authentication
from shiftcare.services import bundles as services_bundles
from shiftcare.services import cloud_client as services_cloud_client
from shiftcare.services import common as services_common
from shiftcare.services import backups as services_backups
from shiftcare.services import memberships as services_memberships
from shiftcare.services import sync_worker as services_sync_worker
from sync_policy import SyncConflict, bundle_from_snapshot, canonical_snapshot, merge_snapshots, snapshot_revision
import database
import json
import sqlite3

def import_cloud_session_to_desktop(cloud_base_url: str, cloud_session: dict) -> dict:
    cloud_token = cloud_session.get("access_token")
    cloud_user = cloud_session.get("user") or {}
    if not cloud_token or not cloud_user:
        raise HTTPException(status_code=502, detail="Cloud login response is incomplete")
    cloud_membership = services_cloud_client.select_desktop_cloud_membership(cloud_user)
    cloud_organization_id = int(cloud_membership["organization_id"])
    with database.get_connection() as identity_connection:
        captured_identity = services_bundles.capture_desktop_sync_identity(identity_connection)
    cloud_bundle = services_cloud_client.request_cloud_json(
        cloud_base_url,
        f"/api/organizations/{cloud_organization_id}/cloud-export",
        token=cloud_token,
    )

    connection = database.get_connection()
    try:
        services_bundles.lock_organization_sync_snapshot(connection, 1)
        services_bundles.ensure_desktop_sync_identity(connection, captured_identity)
        cursor = connection.cursor()
        cursor.execute("SELECT key, value FROM app_settings WHERE organization_id = 1")
        settings = {row["key"]: row["value"] for row in cursor.fetchall()}
        local_bundle = services_bundles.build_organization_export_bundle(connection, 1)
        same_link = (
            str(settings.get("cloud_organization_id") or "") == str(cloud_organization_id)
            and str(settings.get("cloud_api_base_url") or "").rstrip("/") == cloud_base_url.rstrip("/")
        )
        if same_link:
            baseline = json.loads(settings["desktop_cloud_sync_baseline"]) if settings.get("desktop_cloud_sync_baseline") else None
            merged = merge_snapshots(baseline, canonical_snapshot(local_bundle), canonical_snapshot(cloud_bundle))
        elif services_bundles.organization_bundle_is_pristine(connection, local_bundle):
            merged = canonical_snapshot(cloud_bundle)
        else:
            raise HTTPException(status_code=409, detail="This local workspace contains data from another or unlinked organization. It was preserved; review it before changing the cloud account.")
        services_backups.create_recovery_backup("cloud_login")
        user_id = services_cloud_client.upsert_desktop_cloud_user(cursor, cloud_user, cloud_membership, 1)
        with services_sync_worker.suspend_desktop_sync_triggers(cursor, 1):
            import_result = services_bundles.import_organization_bundle(
                connection, 1, bundle_from_snapshot(merged, cloud_bundle), True, user_id,
            )
        services_bundles.save_desktop_sync_baseline(cursor, cloud_bundle)
        now = services_common.current_utc_timestamp()
        for key, value in {
            "cloud_api_base_url": cloud_base_url,
            "cloud_organization_id": str(cloud_organization_id),
            "cloud_organization_public_id": str(cloud_membership.get("organization_public_id") or cloud_bundle.get("organization", {}).get("public_id") or ""),
            "cloud_linked_at": now,
            "desktop_cloud_access_token": str(cloud_token),
            "desktop_cloud_last_pull_at": now,
            "desktop_cloud_last_pull_app_version": str(cloud_bundle.get("app_version") or ""),
        }.items():
            cursor.execute(
                """
                INSERT INTO app_settings (organization_id, key, value)
                VALUES (1, ?, ?)
                ON CONFLICT(organization_id, key)
                DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
        cursor.execute("DELETE FROM desktop_sync_outbox WHERE organization_id = 1")
        sync_pending = merged != canonical_snapshot(cloud_bundle)
        if sync_pending:
            cursor.execute("INSERT INTO desktop_sync_outbox (organization_id, entity_type, entity_public_id, operation) VALUES (1, 'organization', 'login-merge', 'replace')")
        auth_response = services_authentication.build_auth_response(connection, user_id)
        connection.commit()
        return {
            **auth_response,
            "desktop_sync": {
                "cloud_api_base_url": cloud_base_url,
                "cloud_organization_id": cloud_organization_id,
                "cloud_organization_public_id": cloud_membership.get("organization_public_id") or cloud_bundle.get("organization", {}).get("public_id") or "",
                "last_pull_at": now,
                "imported": import_result.get("imported", {}),
                "sync_pending": sync_pending,
            },
        }
    except (sqlite3.IntegrityError, SyncConflict) as exc:
        connection.rollback()
        raise HTTPException(status_code=409, detail=f"Desktop import conflict: {exc}") from exc
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


def finalize_initial_cloud_link(request_data, current_user: dict) -> dict:
    """Finalize a browser upload without adopting newer cloud edits as deletions."""
    accepted = request_data.sync_bundle
    if accepted.get("sync_protocol") != 2 or accepted.get("sync_revision") != snapshot_revision(canonical_snapshot(accepted)):
        raise HTTPException(status_code=409, detail="Cloud did not return a valid accepted sync snapshot")
    if str((accepted.get("organization") or {}).get("public_id")) != request_data.cloud_organization_public_id:
        raise HTTPException(status_code=409, detail="Accepted snapshot belongs to a different cloud organization")
    with database.get_connection() as identity_connection:
        captured_identity = services_bundles.capture_desktop_sync_identity(identity_connection)
    cloud_base_url = request_data.cloud_api_base_url.rstrip("/")
    remote = services_cloud_client.request_cloud_json(
        cloud_base_url, f"/api/organizations/{request_data.cloud_organization_id}/cloud-export", token=request_data.cloud_access_token,
    )
    if str((remote.get("organization") or {}).get("public_id")) != request_data.cloud_organization_public_id:
        raise HTTPException(status_code=409, detail="Cloud organization identity changed while connecting")
    connection = database.get_connection()
    try:
        services_bundles.lock_organization_sync_snapshot(connection, 1)
        services_bundles.ensure_desktop_sync_identity(connection, captured_identity)
        cursor = connection.cursor()
        membership = services_authentication.require_organization_role(current_user, 1, {"owner", "admin"})
        if services_memberships.get_allowed_department_ids(cursor, {"user": current_user, "membership": membership}) is not None:
            raise HTTPException(status_code=403, detail="Organization synchronization requires access to all departments")
        local = services_bundles.build_organization_export_bundle(connection, 1)
        merged = merge_snapshots(canonical_snapshot(accepted), canonical_snapshot(local), canonical_snapshot(remote))
        services_backups.create_recovery_backup("cloud_link")
        with services_sync_worker.suspend_desktop_sync_triggers(cursor, 1):
            services_bundles.import_organization_bundle(connection, 1, bundle_from_snapshot(merged, local), True, current_user["id"])
        services_bundles.save_desktop_sync_baseline(cursor, remote)
        linked_at = request_data.linked_at or services_common.current_utc_timestamp()
        for key, value in {
            "cloud_api_base_url": cloud_base_url,
            "cloud_organization_id": str(request_data.cloud_organization_id),
            "cloud_organization_public_id": request_data.cloud_organization_public_id,
            "cloud_linked_at": linked_at,
            "desktop_cloud_access_token": request_data.cloud_access_token,
        }.items():
            cursor.execute(
                "INSERT INTO app_settings (organization_id, key, value) VALUES (1, ?, ?) ON CONFLICT(organization_id, key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
        cursor.execute("DELETE FROM desktop_sync_outbox WHERE organization_id = 1")
        pending = merged != canonical_snapshot(remote)
        if pending:
            cursor.execute("INSERT INTO desktop_sync_outbox (organization_id, entity_type, entity_public_id, operation) VALUES (1, 'organization', 'initial-link', 'replace')")
        connection.commit()
        return {
            "message": "Cloud link saved", "cloud_api_base_url": cloud_base_url,
            "cloud_organization_id": request_data.cloud_organization_id,
            "cloud_organization_public_id": request_data.cloud_organization_public_id,
            "linked_at": linked_at, "sync_pending": pending,
        }
    except SyncConflict as exc:
        connection.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        connection.close()
