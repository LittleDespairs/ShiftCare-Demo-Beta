"""Services: sync pull for ShiftCare."""
from __future__ import annotations

from fastapi import HTTPException
from shiftcare.services import bundles as services_bundles
from shiftcare.services import cloud_client as services_cloud_client
from shiftcare.services import common as services_common
from shiftcare.services import sync_worker as services_sync_worker
from sync_policy import SyncConflict
from sync_policy import bundle_from_snapshot
from sync_policy import canonical_snapshot
import json

def sync_cloud_preferences_to_desktop(connection, settings: dict[str, str]) -> bool:
    captured_identity = services_bundles.capture_desktop_sync_identity(connection)
    # A caller may have read its settings before another request relinked the
    # desktop. Use the same identity for both HTTP routing and the final guard.
    request_settings = captured_identity
    cloud_base_url = request_settings.get("cloud_api_base_url") or services_cloud_client.get_desktop_cloud_login_base_url()
    cloud_organization_id = request_settings.get("cloud_organization_id")
    cloud_token = request_settings.get("desktop_cloud_access_token")
    if not cloud_organization_id or not cloud_token:
        return False
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, entity_type, entity_public_id FROM desktop_sync_outbox "
        "WHERE organization_id = 1 AND operation = 'upsert' AND status IN ('pending', 'failed')"
    )
    captured_upserts = [dict(row) for row in cursor.fetchall()]
    cloud_bundle = services_cloud_client.request_cloud_json(
        cloud_base_url, f"/api/organizations/{int(cloud_organization_id)}/cloud-export", token=cloud_token,
    )
    if cloud_bundle.get("sync_protocol") != 2:
        raise HTTPException(status_code=409, detail="Update the cloud service before synchronizing")
    expected_public_id = captured_identity.get("cloud_organization_public_id")
    if expected_public_id and str((cloud_bundle.get("organization") or {}).get("public_id")) != expected_public_id:
        raise HTTPException(status_code=409, detail="Cloud organization identity changed; local data was preserved")
    services_bundles.lock_organization_sync_snapshot(connection, 1)
    cursor = connection.cursor()
    try:
        services_bundles.ensure_desktop_sync_identity(connection, captured_identity)
        baseline = json.loads(captured_identity["desktop_cloud_sync_baseline"]) if captured_identity.get("desktop_cloud_sync_baseline") else None
        local_bundle = services_bundles.build_organization_export_bundle(connection, 1)
        evidence = services_sync_worker.capture_legacy_sync_evidence(connection) if baseline is None else None
        merged = services_sync_worker.merge_desktop_snapshots(baseline, local_bundle, cloud_bundle, evidence)
    except SyncConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    merged_bundle = bundle_from_snapshot(merged, local_bundle)
    with services_sync_worker.suspend_desktop_sync_triggers(cursor, 1):
        services_bundles.import_organization_bundle(connection, 1, merged_bundle, True, None)
    services_bundles.save_desktop_sync_baseline(cursor, cloud_bundle)
    local_snapshot, remote_snapshot = canonical_snapshot(local_bundle), canonical_snapshot(cloud_bundle)
    redundant_ids = [row["id"] for row in captured_upserts
                     if row["entity_public_id"] in local_snapshot["records"].get(row["entity_type"], {})
                     and local_snapshot["records"][row["entity_type"]][row["entity_public_id"]]
                     == remote_snapshot["records"].get(row["entity_type"], {}).get(row["entity_public_id"])]
    if redundant_ids:
        placeholders = ",".join("?" for _ in redundant_ids)
        cursor.execute(
            f"UPDATE desktop_sync_outbox SET status = 'synced', synced_at = ?, updated_at = ?, last_error = NULL "
            f"WHERE id IN ({placeholders}) AND status IN ('pending', 'failed') AND operation = 'upsert'",
            (services_common.current_utc_timestamp(), services_common.current_utc_timestamp(), *redundant_ids),
        )
        cursor.execute(
            "DELETE FROM app_settings WHERE organization_id = 1 AND key = 'desktop_cloud_last_push_error' "
            "AND NOT EXISTS (SELECT 1 FROM desktop_sync_outbox WHERE organization_id = 1 AND status = 'failed')"
        )
    cursor.execute(
        "INSERT INTO app_settings (organization_id, key, value) VALUES (1, 'desktop_cloud_last_pull_at', ?) "
        "ON CONFLICT(organization_id, key) DO UPDATE SET value = excluded.value",
        (services_common.current_utc_timestamp(),),
    )
    if merged != canonical_snapshot(cloud_bundle):
        cursor.execute(
            "SELECT COUNT(*) FROM desktop_sync_outbox "
            "WHERE organization_id = 1 AND status IN ('pending', 'failed', 'syncing')"
        )
        if not int(cursor.fetchone()[0]):
            cursor.execute(
                "INSERT INTO desktop_sync_outbox (organization_id, entity_type, entity_public_id, operation) "
                "VALUES (1, 'organization', 'local-settings', 'replace')"
            )
    return True


def pull_cloud_preferences_for_desktop_generation(connection) -> None:
    if not services_cloud_client.is_desktop_sqlite_runtime():
        return
    cursor = connection.cursor()
    # The agreed snapshot preserves local edits during the merge. Blocking all
    # incoming requests while any local preference is queued can leave portal
    # submissions invisible indefinitely after a failed outgoing operation.
    cursor.execute(
        """
        SELECT key, value
        FROM app_settings
        WHERE organization_id = 1
          AND key IN ('cloud_api_base_url', 'cloud_organization_id', 'desktop_cloud_access_token')
        """
    )
    settings = {row["key"]: row["value"] for row in cursor.fetchall()}
    if services_cloud_client.desktop_cloud_sync_is_ready(settings):
        sync_cloud_preferences_to_desktop(connection, settings)
