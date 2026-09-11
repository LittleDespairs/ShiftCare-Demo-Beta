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
from sync_policy import merge_snapshots
import json

def sync_cloud_preferences_to_desktop(connection, settings: dict[str, str]) -> bool:
    cloud_base_url = settings.get("cloud_api_base_url") or services_cloud_client.get_desktop_cloud_login_base_url()
    cloud_organization_id = settings.get("cloud_organization_id")
    cloud_token = settings.get("desktop_cloud_access_token")
    if not cloud_organization_id or not cloud_token:
        return False
    captured_identity = services_bundles.capture_desktop_sync_identity(connection)
    cloud_bundle = services_cloud_client.request_cloud_json(
        cloud_base_url, f"/api/organizations/{int(cloud_organization_id)}/cloud-export", token=cloud_token,
    )
    if cloud_bundle.get("sync_protocol") != 2:
        raise HTTPException(status_code=409, detail="Update the cloud service before synchronizing")
    services_bundles.lock_organization_sync_snapshot(connection, 1)
    cursor = connection.cursor()
    try:
        services_bundles.ensure_desktop_sync_identity(connection, captured_identity)
        baseline = json.loads(captured_identity["desktop_cloud_sync_baseline"]) if captured_identity.get("desktop_cloud_sync_baseline") else None
        local_bundle = services_bundles.build_organization_export_bundle(connection, 1)
        merged = merge_snapshots(baseline, canonical_snapshot(local_bundle), canonical_snapshot(cloud_bundle))
    except SyncConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    merged_bundle = bundle_from_snapshot(merged, local_bundle)
    with services_sync_worker.suspend_desktop_sync_triggers(cursor, 1):
        services_bundles.import_organization_bundle(connection, 1, merged_bundle, True, None)
    services_bundles.save_desktop_sync_baseline(cursor, cloud_bundle)
    cursor.execute(
        "INSERT INTO app_settings (organization_id, key, value) VALUES (1, 'desktop_cloud_last_pull_at', ?) "
        "ON CONFLICT(organization_id, key) DO UPDATE SET value = excluded.value",
        (services_common.current_utc_timestamp(),),
    )
    if merged != canonical_snapshot(cloud_bundle):
        cursor.execute(
            "INSERT INTO desktop_sync_outbox (organization_id, entity_type, entity_public_id, operation) "
            "VALUES (1, 'organization', 'local-settings', 'replace')"
        )
    return True


def pull_cloud_preferences_for_desktop_generation(connection) -> None:
    if not services_cloud_client.is_desktop_sqlite_runtime():
        return
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM desktop_sync_outbox
        WHERE organization_id = 1
              AND entity_type IN (
                  'employee_preferences',
                  'employee_week_preferences',
                  'employee_week_preference_requests',
                  'employee_recurring_preferences',
                  'employee_day_statuses',
                  'shift_swap_requests'
              )
          AND status IN ('pending', 'failed', 'syncing')
        """
    )
    if int(cursor.fetchone()["count"] or 0) > 0:
        return
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
