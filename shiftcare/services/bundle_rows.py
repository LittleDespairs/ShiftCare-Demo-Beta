"""Services: bundle rows for ShiftCare."""
from __future__ import annotations

from fastapi import HTTPException
from shiftcare import config as app_constants
from shiftcare.services import authentication as services_authentication
from shiftcare.services import common as services_common
import app_settings_service
import database as database_module
import license_runtime
import sqlite3

def fetch_table_rows(cursor: sqlite3.Cursor, table_name: str, organization_id: int) -> list[dict]:
    order_column = "key" if table_name == "app_settings" else "id"
    if table_name == "app_settings":
        placeholders = ",".join(["?"] * len(app_constants.LOCAL_ONLY_APP_SETTING_KEYS))
        cursor.execute(
            f"""
            SELECT *
            FROM app_settings
            WHERE organization_id = ?
              AND key NOT IN ({placeholders})
            ORDER BY {order_column}
            """,
            (organization_id, *sorted(app_constants.LOCAL_ONLY_APP_SETTING_KEYS)),
        )
    else:
        cursor.execute(f"SELECT * FROM {table_name} WHERE organization_id = ? ORDER BY {order_column}", (organization_id,))
    return [dict(row) for row in cursor.fetchall()]


def _source_rows_by_public_id(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("public_id")): row for row in rows if row.get("public_id")}


def _insert_employee_bundle_rows(cursor: sqlite3.Cursor, rows: list[dict], organization_id: int, now: str) -> dict[int, int]:
    id_map = {}
    for row in rows:
        cursor.execute(
            """
            INSERT INTO employees (
                organization_id, public_id, id_card, full_name, sex, min_shifts_per_week, target_shifts_per_week,
                max_shifts_per_week, can_work_night, can_work_weekends,
                can_work_evenings_after_night, can_work_mornings_and_evenings, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                row.get("public_id"),
                services_authentication.normalize_id_card(row.get("id_card")) or None,
                row.get("full_name"),
                row.get("sex"),
                row.get("min_shifts_per_week"),
                row.get("target_shifts_per_week"),
                row.get("max_shifts_per_week"),
                int(row.get("can_work_night") or 0),
                int(row.get("can_work_weekends") or 0),
                int(row.get("can_work_evenings_after_night") or 0),
                int(row.get("can_work_mornings_and_evenings") or 0),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )
        id_map[int(row["id"])] = int(cursor.lastrowid)
    return id_map


def get_default_department_id(cursor: sqlite3.Cursor, organization_id: int) -> int:
    cursor.execute(
        """
        SELECT id
        FROM departments
        WHERE organization_id = ?
        ORDER BY display_order, id
        LIMIT 1
        """,
        (organization_id,),
    )
    row = cursor.fetchone()
    if row:
        return int(row["id"])
    cursor.execute(
        """
        INSERT INTO departments (organization_id, name, description, display_order, is_active, created_at, updated_at)
        VALUES (?, ?, NULL, 0, 1, ?, ?)
        """,
        (organization_id, database_module.DEFAULT_DEPARTMENT_NAME, now_iso := services_common.current_utc_timestamp(), now_iso),
    )
    return int(cursor.lastrowid)


def _insert_department_bundle_rows(cursor: sqlite3.Cursor, rows: list[dict], organization_id: int, now: str) -> dict[int, int]:
    id_map = {}
    if not rows:
        default_id = get_default_department_id(cursor, organization_id)
        id_map[1] = default_id
        return id_map
    for row in rows:
        cursor.execute(
            """
            INSERT INTO departments (
                organization_id, public_id, name, description, display_order, is_active, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(organization_id, name)
            DO UPDATE SET description = excluded.description,
                          display_order = excluded.display_order,
                          is_active = excluded.is_active,
                          updated_at = excluded.updated_at,
                          updated_by = excluded.updated_by
            """,
            (
                organization_id,
                row.get("public_id"),
                row.get("name") or database_module.DEFAULT_DEPARTMENT_NAME,
                row.get("description"),
                int(row.get("display_order") or 0),
                int(row.get("is_active") if row.get("is_active") is not None else 1),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )
        cursor.execute(
            "SELECT id FROM departments WHERE organization_id = ? AND name = ?",
            (organization_id, row.get("name") or database_module.DEFAULT_DEPARTMENT_NAME),
        )
        department_id = int(cursor.fetchone()["id"])
        id_map[int(row["id"])] = department_id
    return id_map


def _insert_position_bundle_rows(
    cursor: sqlite3.Cursor,
    rows: list[dict],
    organization_id: int,
    now: str,
    department_id_map: dict[int, int] | None = None,
) -> dict[int, int]:
    id_map = {}
    default_department_id = get_default_department_id(cursor, organization_id)
    for row in rows:
        source_department_id = row.get("department_id")
        department_id = (
            department_id_map.get(int(source_department_id))
            if source_department_id is not None and department_id_map
            else default_department_id
        )
        cursor.execute(
            """
            INSERT INTO positions (
                organization_id, department_id, public_id, name, color, requires_continuous_coverage, minimum_staff_presence,
                allow_same_day_other_positions,
                max_consecutive_nights, emergency_max_consecutive_nights,
                max_consecutive_split_days, emergency_max_consecutive_split_days, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                department_id,
                row.get("public_id"),
                row.get("name"),
                row.get("color") or app_settings_service.DEFAULT_POSITION_COLOR,
                int(row.get("requires_continuous_coverage") or 0),
                int(row.get("minimum_staff_presence") or 0),
                int(row.get("allow_same_day_other_positions") or 0),
                row.get("max_consecutive_nights"),
                row.get("emergency_max_consecutive_nights"),
                row.get("max_consecutive_split_days"),
                row.get("emergency_max_consecutive_split_days"),
                row.get("created_at") or now,
                row.get("updated_at") or now,
                row.get("updated_by"),
            ),
        )
        id_map[int(row["id"])] = int(cursor.lastrowid)
    return id_map


def _insert_license_bundle_rows(cursor: sqlite3.Cursor, rows: list[dict], organization_id: int, now: str) -> int:
    imported_count = 0
    for row in rows:
        certificate_json = row.get("certificate_json")
        if not certificate_json:
            continue
        cursor.execute(
            """
            INSERT INTO licenses (
                organization_id, license_id, status, plan_code, employee_limit,
                support_cloud_expires_at, grace_ends_at, certificate_json, signature,
                key_id, source, imported_at, last_verified_at, revoked_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(license_id)
            DO UPDATE SET status = excluded.status,
                          plan_code = excluded.plan_code,
                          employee_limit = excluded.employee_limit,
                          support_cloud_expires_at = excluded.support_cloud_expires_at,
                          grace_ends_at = excluded.grace_ends_at,
                          certificate_json = excluded.certificate_json,
                          signature = excluded.signature,
                          key_id = excluded.key_id,
                          source = excluded.source,
                          imported_at = excluded.imported_at,
                          last_verified_at = excluded.last_verified_at,
                          revoked_at = excluded.revoked_at
            WHERE licenses.organization_id = excluded.organization_id
            """,
            (
                organization_id,
                row.get("license_id"),
                row.get("status") or "active",
                row.get("plan_code"),
                int(row.get("employee_limit") or license_runtime.TRIAL_EMPLOYEE_LIMIT),
                row.get("support_cloud_expires_at"),
                row.get("grace_ends_at"),
                certificate_json,
                row.get("signature") or "",
                row.get("key_id"),
                row.get("source") or "imported",
                row.get("imported_at") or now,
                row.get("last_verified_at") or now,
                row.get("revoked_at"),
            ),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=409, detail="License already belongs to a different organization")
        imported_count += 1
    return imported_count
