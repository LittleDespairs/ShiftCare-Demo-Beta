"""Services: bundles for ShiftCare."""
from __future__ import annotations

from fastapi import HTTPException
from shiftcare import config as app_constants
from shiftcare.services import audit as services_audit
from shiftcare.services import bundle_rows as services_bundle_rows
from shiftcare.services import common as services_common
from shiftcare.services import memberships as services_memberships
from shiftcare.services import preferences as services_preferences
from sync_policy import StableIdentityImportCursor
from sync_policy import canonical_snapshot
from sync_policy import snapshot_revision
from sync_policy import SyncConflict
import json
from app_settings_service import get_app_settings


DESKTOP_SYNC_IDENTITY_KEYS = (
    "cloud_api_base_url", "cloud_organization_id", "cloud_organization_public_id",
    "cloud_linked_at", "desktop_cloud_access_token", "desktop_cloud_sync_baseline",
)


def capture_desktop_sync_identity(connection) -> dict:
    cursor = connection.cursor()
    placeholders = ",".join("?" for _ in DESKTOP_SYNC_IDENTITY_KEYS)
    cursor.execute(
        f"SELECT key, value FROM app_settings WHERE organization_id = 1 AND key IN ({placeholders})",
        DESKTOP_SYNC_IDENTITY_KEYS,
    )
    return {row["key"]: row["value"] for row in cursor.fetchall()}


def ensure_desktop_sync_identity(connection, captured: dict) -> None:
    if capture_desktop_sync_identity(connection) != captured:
        raise SyncConflict("Cloud connection or agreed snapshot changed during the request; local data was preserved. Retry synchronization.")


def organization_bundle_is_pristine(connection, bundle: dict) -> bool:
    """Only untouched setup defaults may be replaced without a shared baseline."""
    records = bundle.get("records") or {}
    if any(rows for table, rows in records.items() if table not in {"departments", "app_settings"}):
        return False
    departments = records.get("departments") or []
    if len(departments) > 1 or any(
        row.get("name") != "Main department" or row.get("description") or int(row.get("display_order") or 0) != 0
        or not row.get("is_active", True)
        for row in departments
    ):
        return False
    defaults = get_app_settings(connection, organization_id=-1)
    for row in records.get("app_settings") or []:
        default = defaults.get(row["key"])
        value = str(row.get("value", "")).strip()
        if isinstance(default, bool):
            if value.lower() not in ({"1", "true"} if default else {"0", "false"}):
                return False
        elif default is None or value != str(default):
            return False
    return True

def build_organization_export_bundle(connection, organization_id: int, exported_by_user_id: int | None = None) -> dict:
    cursor = connection.cursor()
    organization = services_common.fetch_one_or_404(
        cursor,
        "SELECT id, public_id, name, status FROM organizations WHERE id = ?",
        (organization_id,),
        "Organization not found",
    )
    records = {table_name: services_bundle_rows.fetch_table_rows(cursor, table_name, organization_id) for table_name in app_constants.ORGANIZATION_EXPORT_TABLES}
    cursor.execute(
        """
        SELECT ep.employee_id, e.public_id AS employee_public_id,
               ep.position_id, p.public_id AS position_public_id,
               ep.is_primary, ep.priority_score, ep.is_fallback_only
        FROM employee_positions ep
        JOIN employees e ON e.id = ep.employee_id
        JOIN positions p ON p.id = ep.position_id
        WHERE e.organization_id = ? AND p.organization_id = ?
        ORDER BY ep.employee_id, ep.position_id
        """,
        (organization_id, organization_id),
    )
    records["employee_positions"] = [dict(row) for row in cursor.fetchall()]
    bundle = {
        "format": "shiftcare.organization.v1",
        "app_version": app_constants.APP_VERSION,
        "exported_at": services_common.current_utc_timestamp(),
        "exported_by_user_id": exported_by_user_id,
        "organization": dict(organization),
        "records": records,
    }
    bundle["sync_protocol"] = 2
    bundle["sync_revision"] = snapshot_revision(canonical_snapshot(bundle))
    return bundle


def begin_organization_export_snapshot(connection) -> None:
    """Read all exported tables from one database snapshot."""
    if getattr(connection, "engine", "sqlite") == "postgresql":
        connection.cursor().execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    elif not connection.in_transaction:
        connection.execute("BEGIN")


def lock_organization_sync_snapshot(connection, organization_id: int) -> None:
    """Serialize the CAS check and import against every ordinary data writer."""
    cursor = connection.cursor()
    if getattr(connection, "engine", "sqlite") == "postgresql":
        tables = sorted({*app_constants.ORGANIZATION_EXPORT_TABLES, "employee_positions", "organizations",
                         "organization_memberships", "organization_invitations", "user_department_access"})
        cursor.execute("LOCK TABLE " + ", ".join(tables) + " IN SHARE ROW EXCLUSIVE MODE")
        cursor.execute("SELECT id FROM organizations WHERE id = ? FOR UPDATE", (organization_id,))
    elif not connection.in_transaction:
        cursor.execute("BEGIN IMMEDIATE")


def save_desktop_sync_baseline(cursor, bundle: dict) -> None:
    cursor.execute(
        """
        INSERT INTO app_settings (organization_id, key, value)
        VALUES (1, 'desktop_cloud_sync_baseline', ?)
        ON CONFLICT(organization_id, key) DO UPDATE SET value = excluded.value
        """,
        (json.dumps(canonical_snapshot(bundle), ensure_ascii=False, separators=(",", ":")),),
    )


def import_organization_bundle(connection, organization_id: int, bundle: dict, replace_existing: bool, imported_by_user_id: int) -> dict:
    if bundle.get("format") != "shiftcare.organization.v1":
        raise HTTPException(status_code=400, detail="Unsupported organization bundle format")
    records = bundle.get("records") or {}
    organization = bundle.get("organization") or {}
    now = services_common.current_utc_timestamp()
    cursor = connection.cursor()

    target_organization = services_common.fetch_one_or_404(
        cursor,
        "SELECT id, public_id FROM organizations WHERE id = ?",
        (organization_id,),
        "Organization not found",
    )
    existing_counts = {
        table_name: services_common.fetch_count(cursor, f"SELECT COUNT(*) FROM {table_name} WHERE organization_id = ?", (organization_id,))
        for table_name in ("employees", "positions", "shift_templates", "schedule_entries")
    }
    if any(existing_counts.values()) and not replace_existing:
        raise HTTPException(status_code=409, detail="Target organization already has scheduling data")

    preserved_employee_links = services_memberships.collect_employee_link_public_ids(cursor, organization_id) if replace_existing else {"memberships": [], "invitations": []}
    preserved_access = services_memberships.preserve_department_access(cursor, organization_id) if replace_existing else []
    existing_rows = {}
    if replace_existing:
        for table_name in app_constants.ORGANIZATION_EXPORT_TABLES:
            if table_name != "app_settings":
                identity = "license_id" if table_name == "licenses" else "public_id"
                existing_rows[table_name] = {
                    row[identity]: row for row in services_bundle_rows.fetch_table_rows(cursor, table_name, organization_id) if row.get(identity)
                }
        cursor = StableIdentityImportCursor(cursor, existing_rows)
    cursor.execute("SELECT key, value FROM app_settings WHERE organization_id = ?", (organization_id,))
    local_settings = {row["key"]: row["value"] for row in cursor.fetchall() if row["key"] in app_constants.LOCAL_ONLY_APP_SETTING_KEYS}

    if replace_existing:
        for table_name in app_constants.ORGANIZATION_IMPORT_DELETE_ORDER:
            if table_name == "app_settings":
                placeholders = ",".join("?" for _ in app_constants.LOCAL_ONLY_APP_SETTING_KEYS)
                cursor.execute(
                    f"DELETE FROM app_settings WHERE organization_id = ? AND key NOT IN ({placeholders})",
                    (organization_id, *sorted(app_constants.LOCAL_ONLY_APP_SETTING_KEYS)),
                )
            elif table_name == "employee_positions":
                cursor.execute(
                    """
                    DELETE FROM employee_positions
                    WHERE employee_id IN (SELECT id FROM employees WHERE organization_id = ?)
                       OR position_id IN (SELECT id FROM positions WHERE organization_id = ?)
                    """,
                    (organization_id, organization_id),
                )
            else:
                cursor.execute(f"DELETE FROM {table_name} WHERE organization_id = ?", (organization_id,))

    cursor.execute(
        "UPDATE organizations SET name = ?, status = 'active', updated_at = ? WHERE id = ?",
        (organization.get("name") or "Imported Organization", now, organization_id),
    )

    department_id_map = services_bundle_rows._insert_department_bundle_rows(cursor, records.get("departments") or [], organization_id, now)
    services_memberships.restore_department_access(cursor, organization_id, preserved_access)
    employee_id_map = services_bundle_rows._insert_employee_bundle_rows(cursor, records.get("employees") or [], organization_id, now)
    employee_id_by_public_id = {
        str(row.get("public_id")): employee_id_map[int(row["id"])]
        for row in records.get("employees") or []
        if row.get("public_id") and int(row["id"]) in employee_id_map
    }
    position_id_map = services_bundle_rows._insert_position_bundle_rows(
        cursor,
        records.get("positions") or [],
        organization_id,
        now,
        department_id_map,
    )
    license_count = services_bundle_rows._insert_license_bundle_rows(cursor, records.get("licenses") or [], organization_id, now)
    employees_by_public_id = services_bundle_rows._source_rows_by_public_id(records.get("employees") or [])
    positions_by_public_id = services_bundle_rows._source_rows_by_public_id(records.get("positions") or [])
    restored_employee_links = services_memberships.restore_employee_links_from_public_ids(
        cursor,
        organization_id,
        preserved_employee_links,
        employee_id_by_public_id,
        now,
    )

    shift_template_id_map = {}
    for row in records.get("shift_templates") or []:
        new_position_id = position_id_map.get(int(row["position_id"])) if row.get("position_id") is not None else None
        cursor.execute(
            """
            INSERT INTO shift_templates (
                organization_id, public_id, position_id, category, name, start_time, end_time,
                is_overnight, is_active, is_split_only, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                new_position_id,
                row.get("category"),
                row.get("name"),
                row.get("start_time"),
                row.get("end_time"),
                int(row.get("is_overnight") or 0),
                int(row.get("is_active") if row.get("is_active") is not None else 1),
                int(row.get("is_split_only") or 0),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )
        shift_template_id_map[int(row["id"])] = int(cursor.lastrowid)

    for row in records.get("employee_positions") or []:
        source_employee = employees_by_public_id.get(str(row.get("employee_public_id")))
        source_position = positions_by_public_id.get(str(row.get("position_public_id")))
        if not source_employee or not source_position:
            continue
        new_employee_id = employee_id_map.get(int(source_employee["id"]))
        new_position_id = position_id_map.get(int(source_position["id"]))
        if not new_employee_id or not new_position_id:
            continue
        cursor.execute(
            """
            INSERT INTO employee_positions (
                employee_id, position_id, is_primary, priority_score, is_fallback_only
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(employee_id, position_id)
            DO UPDATE SET is_primary = excluded.is_primary,
                          priority_score = excluded.priority_score,
                          is_fallback_only = excluded.is_fallback_only
            """,
            (
                new_employee_id,
                new_position_id,
                int(row.get("is_primary") or 0),
                int(row.get("priority_score") or 50),
                int(row.get("is_fallback_only") or 0),
            ),
        )

    for row in records.get("shift_requirements") or []:
        new_position_id = position_id_map.get(int(row["position_id"]))
        if not new_position_id:
            continue
        cursor.execute(
            """
            INSERT INTO shift_requirements (
                organization_id, public_id, position_id, shift_category, required_total,
                required_female_min, required_male_min, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                new_position_id,
                row.get("shift_category"),
                int(row.get("required_total") or 0),
                int(row.get("required_female_min") or 0),
                int(row.get("required_male_min") or 0),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )

    for row in records.get("coverage_requirements") or []:
        new_position_id = position_id_map.get(int(row["position_id"]))
        if not new_position_id:
            continue
        cursor.execute(
            """
            INSERT INTO coverage_requirements (
                organization_id, public_id, position_id, start_time, end_time, required_total,
                required_female_min, required_male_min, is_overnight, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                new_position_id,
                row.get("start_time"),
                row.get("end_time"),
                int(row.get("required_total") or 0),
                int(row.get("required_female_min") or 0),
                int(row.get("required_male_min") or 0),
                int(row.get("is_overnight") or 0),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )

    for row in records.get("employee_preferences") or []:
        new_employee_id = employee_id_map.get(int(row["employee_id"]))
        if not new_employee_id:
            continue
        cursor.execute(
            """
            INSERT INTO employee_preferences (
                organization_id, public_id, employee_id, allow_morning, allow_evening, allow_night,
                allow_morning_evening_combo, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                new_employee_id,
                int(row.get("allow_morning") or 0),
                int(row.get("allow_evening") or 0),
                int(row.get("allow_night") or 0),
                int(row.get("allow_morning_evening_combo") or 0),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )

    for row in records.get("employee_week_preferences") or []:
        new_employee_id = employee_id_map.get(int(row["employee_id"]))
        if not new_employee_id:
            continue
        cursor.execute(
            """
            INSERT INTO employee_week_preferences (
                organization_id, public_id, employee_id, week_start_date, preference_date,
                preference_type, request_type, target_category, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                new_employee_id,
                row.get("week_start_date"),
                row.get("preference_date"),
                row.get("preference_type"),
                row.get("request_type") or "request_shift",
                row.get("target_category"),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )

    for row in records.get("employee_week_preference_requests") or []:
        new_employee_id = employee_id_map.get(int(row["employee_id"]))
        if not new_employee_id:
            continue
        cursor.execute(
            """
            INSERT INTO employee_week_preference_requests (
                organization_id, public_id, employee_id, week_start_date, preference_date,
                preference_type, request_type, target_category, status,
                created_at, updated_at, updated_by, reviewed_at, reviewed_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                new_employee_id,
                row.get("week_start_date"),
                row.get("preference_date"),
                row.get("preference_type"),
                row.get("request_type") or "request_shift",
                row.get("target_category"),
                row.get("status") if row.get("status") in {"pending", "approved", "rejected"} else "pending",
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
                row.get("reviewed_at"),
                row.get("reviewed_by"),
            ),
        )

    for row in records.get("employee_recurring_preferences") or []:
        new_employee_id = employee_id_map.get(int(row["employee_id"]))
        if not new_employee_id:
            continue
        for request_index, normalized_request in enumerate(services_preferences.normalize_preference_request(
            row.get("preference_type"),
            row.get("request_type"),
            row.get("target_category"),
        )):
            cursor.execute(
                """
                INSERT INTO employee_recurring_preferences (
                    organization_id, public_id, employee_id, preference_kind, day_of_week,
                    preference_type, request_type, target_category, created_at, updated_at, updated_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    organization_id,
                    row.get("public_id") if request_index == 0 else None,
                    new_employee_id,
                    row.get("preference_kind"),
                    int(row.get("day_of_week") or 0),
                    normalized_request["preference_type"],
                    normalized_request["request_type"],
                    normalized_request["target_category"],
                    row.get("created_at") or now,
                    row.get("updated_at") or now,
                    row.get("updated_by"),
                ),
            )

    for row in records.get("employee_day_statuses") or []:
        new_employee_id = employee_id_map.get(int(row["employee_id"]))
        if not new_employee_id:
            continue
        cursor.execute(
            """
            INSERT INTO employee_day_statuses (
                organization_id, public_id, employee_id, date, status_type, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                new_employee_id,
                row.get("date"),
                row.get("status_type"),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )

    schedule_entry_id_map = {}
    for row in records.get("schedule_entries") or []:
        new_employee_id = employee_id_map.get(int(row["employee_id"]))
        new_position_id = position_id_map.get(int(row["position_id"]))
        new_template_id = shift_template_id_map.get(int(row["shift_template_id"]))
        if not new_employee_id or not new_position_id or not new_template_id:
            continue
        cursor.execute(
            """
            INSERT INTO schedule_entries (
                organization_id, public_id, employee_id, position_id, date, shift_template_id,
                no_show, start_time_override, end_time_override, is_overnight_override,
                created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                new_employee_id,
                new_position_id,
                row.get("date"),
                new_template_id,
                int(row.get("no_show") or 0),
                row.get("start_time_override"),
                row.get("end_time_override"),
                int(row["is_overnight_override"]) if row.get("is_overnight_override") is not None else None,
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )
        schedule_entry_id_map[int(row["id"])] = int(cursor.lastrowid)

    for row in records.get("shift_swap_requests") or []:
        requester_employee_id = employee_id_map.get(int(row["requester_employee_id"]))
        target_employee_id = employee_id_map.get(int(row["target_employee_id"]))
        requester_entry_id = schedule_entry_id_map.get(int(row["requester_schedule_entry_id"]))
        target_entry_id = schedule_entry_id_map.get(int(row["target_schedule_entry_id"]))
        if not requester_employee_id or not target_employee_id or not requester_entry_id or not target_entry_id:
            continue
        cursor.execute(
            """
            INSERT INTO shift_swap_requests (
                organization_id, public_id, requester_employee_id, target_employee_id,
                requester_schedule_entry_id, target_schedule_entry_id, status,
                requester_note, target_note, admin_note,
                created_at, updated_at, updated_by, target_responded_at, reviewed_at, reviewed_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                requester_employee_id,
                target_employee_id,
                requester_entry_id,
                target_entry_id,
                row.get("status") if row.get("status") in {"pending_target", "pending_admin", "approved", "rejected", "cancelled"} else "pending_target",
                row.get("requester_note"),
                row.get("target_note"),
                row.get("admin_note"),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
                row.get("target_responded_at"),
                row.get("reviewed_at"),
                row.get("reviewed_by"),
            ),
        )

    for row in records.get("app_settings") or []:
        if row.get("key") in app_constants.LOCAL_ONLY_APP_SETTING_KEYS:
            continue
        cursor.execute(
            """
            INSERT INTO app_settings (organization_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(organization_id, key)
            DO UPDATE SET value = excluded.value
            """,
            (organization_id, row.get("key"), row.get("value")),
        )
    for key, value in local_settings.items():
        cursor.execute(
            "INSERT INTO app_settings (organization_id, key, value) VALUES (?, ?, ?) ON CONFLICT(organization_id, key) DO UPDATE SET value = excluded.value",
            (organization_id, key, value),
        )

    services_audit.write_auth_audit_event(
        cursor,
        "organization_cloud_imported",
        user_id=imported_by_user_id,
        organization_id=organization_id,
        metadata={"source_organization_public_id": organization.get("public_id"), "source_app_version": bundle.get("app_version")},
    )
    return {
        "organization_id": organization_id,
        "organization_public_id": target_organization["public_id"],
        "source_organization_public_id": organization.get("public_id"),
        "imported": {
            "employees": len(employee_id_map),
            "departments": len(department_id_map),
            "positions": len(position_id_map),
            "shift_templates": len(shift_template_id_map),
            "schedule_entries": len(records.get("schedule_entries") or []),
            "shift_swap_requests": len(records.get("shift_swap_requests") or []),
            "employee_week_preference_requests": len(records.get("employee_week_preference_requests") or []),
            "licenses": license_count,
        },
        "restored_employee_links": restored_employee_links,
    }
