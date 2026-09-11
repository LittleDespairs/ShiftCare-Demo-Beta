"""Services: sync worker for ShiftCare."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from shiftcare import config as app_constants
from shiftcare.services import bundles as services_bundles
from shiftcare.services import cloud_client as services_cloud_client
from shiftcare.services import common as services_common
from shiftcare.services import runtime as services_runtime
from sync_policy import SyncConflict
from sync_policy import bundle_from_snapshot
from sync_policy import canonical_snapshot
from sync_policy import merge_snapshots
import database
import json
import os
import sqlite3
import sys
import threading

def should_start_desktop_sync_worker() -> bool:
    if os.environ.get("SCHEDULE_APP_DISABLE_BACKGROUND_SYNC", "").strip().lower() in app_constants.TRUTHY_ENV_VALUES:
        return False
    return services_cloud_client.is_desktop_sqlite_runtime() and (
        getattr(sys, "frozen", False)
        or os.environ.get("SCHEDULE_APP_ENABLE_BACKGROUND_SYNC", "").strip().lower() in app_constants.TRUTHY_ENV_VALUES
    )


_DESKTOP_SYNC_RUN_LOCK = threading.Lock()


def run_desktop_sync_once() -> bool:
    if not services_cloud_client.is_desktop_sqlite_runtime():
        return False

    connection = database.get_connection()
    if not _DESKTOP_SYNC_RUN_LOCK.acquire(blocking=False):
        connection.close()
        return False
    claimed_ids: list[int] = []
    try:
        cursor = connection.cursor()
        services_bundles.lock_organization_sync_snapshot(connection, 1)
        stale_before = (datetime.now(UTC) - timedelta(minutes=10)).replace(tzinfo=None).isoformat(timespec="seconds")
        cursor.execute(
            """
            UPDATE desktop_sync_outbox SET status = 'failed', next_attempt_at = NULL,
                last_error = 'Interrupted synchronization will be retried'
            WHERE organization_id = 1 AND status = 'syncing' AND updated_at < ?
            """,
            (stale_before,),
        )
        cursor.execute("SELECT COUNT(*) AS count FROM desktop_sync_outbox WHERE organization_id = 1 AND status = 'syncing'")
        if int(cursor.fetchone()["count"]):
            connection.commit()
            return False
        cursor.execute(
            """
            SELECT id
            FROM desktop_sync_outbox
            WHERE organization_id = 1 AND status IN ('pending', 'failed')
              AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
            ORDER BY id
            """,
            (services_common.current_utc_timestamp(),),
        )
        claimed_ids = [int(row["id"]) for row in cursor.fetchall()]

        settings = services_bundles.capture_desktop_sync_identity(connection)
        cloud_base_url = settings.get("cloud_api_base_url") or services_cloud_client.get_desktop_cloud_login_base_url()
        cloud_organization_id = settings.get("cloud_organization_id")
        cloud_token = settings.get("desktop_cloud_access_token")
        if not cloud_organization_id or not cloud_token:
            connection.commit()
            return False

        local_bundle = services_bundles.build_organization_export_bundle(connection, 1)
        local_snapshot = canonical_snapshot(local_bundle)
        baseline = json.loads(settings["desktop_cloud_sync_baseline"]) if settings.get("desktop_cloud_sync_baseline") else None
        if not claimed_ids:
            if baseline is None or local_snapshot == baseline:
                connection.commit()
                return False
            # Settings and employee-position links have no per-row outbox
            # trigger. Detect their edits against the agreed snapshot too.
            cursor.execute(
                "INSERT INTO desktop_sync_outbox (organization_id, entity_type, entity_public_id, operation) VALUES (1, 'organization', 'snapshot', 'replace')"
            )
            claimed_ids = [int(cursor.lastrowid)]
        placeholders = ",".join("?" for _ in claimed_ids)
        cursor.execute(
            f"""
            UPDATE desktop_sync_outbox
            SET status = 'syncing', attempts = attempts + 1, updated_at = ?
            WHERE id IN ({placeholders})
            """,
            (services_common.current_utc_timestamp(), *claimed_ids),
        )
        connection.commit()

        remote_bundle = services_cloud_client.request_cloud_json(
            cloud_base_url, f"/api/organizations/{int(cloud_organization_id)}/cloud-export", token=cloud_token,
        )
        if remote_bundle.get("sync_protocol") != 2 or not remote_bundle.get("sync_revision"):
            raise SyncConflict("The cloud service must be updated before safe synchronization is available")
        expected_public_id = settings.get("cloud_organization_public_id")
        if expected_public_id and str((remote_bundle.get("organization") or {}).get("public_id")) != expected_public_id:
            raise SyncConflict("Cloud organization identity changed; local data was preserved")
        merged = merge_snapshots(baseline, local_snapshot, canonical_snapshot(remote_bundle))
        bundle = bundle_from_snapshot(merged, remote_bundle)
        bundle["sync"] = {"protocol": 2, "base_revision": remote_bundle["sync_revision"]}
        response = services_cloud_client.request_cloud_json(
            cloud_base_url,
            f"/api/organizations/{int(cloud_organization_id)}/cloud-import",
            method="POST",
            payload={"bundle": bundle, "replace_existing": True},
            token=cloud_token,
        )
        accepted_bundle = response.get("sync_bundle")
        if not accepted_bundle:
            raise SyncConflict("Cloud did not acknowledge the synchronized snapshot; local changes were preserved")

        services_bundles.lock_organization_sync_snapshot(connection, 1)
        current_bundle = services_bundles.build_organization_export_bundle(connection, 1)
        services_bundles.ensure_desktop_sync_identity(connection, settings)
        # Edits made while the HTTP request was in flight stay local and pending.
        local_merged = merge_snapshots(local_snapshot, canonical_snapshot(current_bundle), canonical_snapshot(accepted_bundle))
        local_result = bundle_from_snapshot(local_merged, current_bundle)
        with suspend_desktop_sync_triggers(cursor, 1):
            services_bundles.import_organization_bundle(connection, 1, local_result, True, None)
        services_bundles.save_desktop_sync_baseline(cursor, accepted_bundle)

        now = services_common.current_utc_timestamp()
        cursor.execute(
            f"""
            UPDATE desktop_sync_outbox
            SET status = 'synced', updated_at = ?, synced_at = ?, last_error = NULL
            WHERE id IN ({placeholders}) AND status = 'syncing'
            """,
            (now, now, *claimed_ids),
        )
        cursor.execute(
            """
            INSERT INTO app_settings (organization_id, key, value)
            VALUES (1, 'desktop_cloud_last_push_at', ?)
            ON CONFLICT(organization_id, key)
            DO UPDATE SET value = excluded.value
            """,
            (now,),
        )
        cursor.execute(
            """
            DELETE FROM app_settings
            WHERE organization_id = 1 AND key = 'desktop_cloud_last_push_error'
            """
        )
        connection.commit()
        return True
    except Exception as exc:
        connection.rollback()
        try:
            cursor = connection.cursor()
            now = services_common.current_utc_timestamp()
            next_attempt = (datetime.now(UTC) + timedelta(minutes=2)).replace(tzinfo=None).isoformat(timespec="seconds")
            placeholders = ",".join("?" for _ in claimed_ids) or "NULL"
            cursor.execute(
                f"""
                UPDATE desktop_sync_outbox
                SET status = 'failed', updated_at = ?, last_error = ?, next_attempt_at = ?
                WHERE id IN ({placeholders}) AND status = 'syncing'
                """,
                (now, str(exc)[:500], next_attempt, *claimed_ids),
            )
            cursor.execute(
                """
                INSERT INTO app_settings (organization_id, key, value)
                VALUES (1, 'desktop_cloud_last_push_error', ?)
                ON CONFLICT(organization_id, key)
                DO UPDATE SET value = excluded.value
                """,
                (str(exc)[:500],),
            )
            connection.commit()
        except Exception:
            connection.rollback()
        return False
    finally:
        connection.close()
        _DESKTOP_SYNC_RUN_LOCK.release()


@contextmanager
def suspend_desktop_sync_triggers(cursor: sqlite3.Cursor, organization_id: int = 1):
    cursor.execute(
        """
        SELECT value
        FROM app_settings
        WHERE organization_id = ? AND key = 'desktop_sync_suspended'
        """,
        (organization_id,),
    )
    previous_row = cursor.fetchone()
    previous_value = previous_row["value"] if previous_row else None
    cursor.execute(
        """
        INSERT INTO app_settings (organization_id, key, value)
        VALUES (?, 'desktop_sync_suspended', '1')
        ON CONFLICT(organization_id, key)
        DO UPDATE SET value = excluded.value
        """,
        (organization_id,),
    )
    try:
        yield
    finally:
        if previous_value is None:
            cursor.execute(
                """
                DELETE FROM app_settings
                WHERE organization_id = ? AND key = 'desktop_sync_suspended'
                """,
                (organization_id,),
            )
        else:
            cursor.execute(
                """
                INSERT INTO app_settings (organization_id, key, value)
                VALUES (?, 'desktop_sync_suspended', ?)
                ON CONFLICT(organization_id, key)
                DO UPDATE SET value = excluded.value
                """,
                (organization_id, previous_value),
            )


def desktop_sync_worker_loop(stop_event: threading.Event) -> None:
    while not stop_event.wait(20):
        run_desktop_sync_once()


_DESKTOP_SYNC_LIFECYCLE_LOCK = threading.Lock()
_DESKTOP_SYNC_THREAD: threading.Thread | None = None
_DESKTOP_SYNC_STOP_EVENT: threading.Event | None = None


def start_desktop_sync_worker() -> threading.Thread | None:
    """Return ownership of a newly started worker to the application lifespan."""
    global _DESKTOP_SYNC_THREAD, _DESKTOP_SYNC_STOP_EVENT
    if services_runtime.is_demo_mode_enabled() or not should_start_desktop_sync_worker():
        return None
    with _DESKTOP_SYNC_LIFECYCLE_LOCK:
        if _DESKTOP_SYNC_THREAD is not None and _DESKTOP_SYNC_THREAD.is_alive():
            return None
        _DESKTOP_SYNC_STOP_EVENT = threading.Event()
        _DESKTOP_SYNC_THREAD = threading.Thread(
            target=desktop_sync_worker_loop,
            args=(_DESKTOP_SYNC_STOP_EVENT,),
            name="shiftcare-desktop-sync",
            daemon=True,
        )
        _DESKTOP_SYNC_THREAD.start()
        return _DESKTOP_SYNC_THREAD


def stop_desktop_sync_worker(worker: threading.Thread | None) -> None:
    """Stop only the worker owned by this lifespan, allowing repeated app creation."""
    if worker is None:
        return
    with _DESKTOP_SYNC_LIFECYCLE_LOCK:
        if worker is not _DESKTOP_SYNC_THREAD:
            return
        _DESKTOP_SYNC_STOP_EVENT.set()
    worker.join(timeout=3)
