"""Routes: swaps for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from schemas import ShiftSwapAdminDecision
from schemas import ShiftSwapRequestCreate
from schemas import ShiftSwapTargetDecision
from shiftcare.services import access as services_access
from shiftcare.services import audit as services_audit
from shiftcare.services import common as services_common
from shiftcare.services import day_status as services_day_status
from shiftcare.services import memberships as services_memberships
from shiftcare.services import swaps as services_swaps
from shiftcare.services import sync_pull as services_sync_pull
import app_settings_service
import database
import database as database_module
import schedule_time

router = APIRouter()


@router.get("/api/shift-swap-requests", tags=["Schedule"])
def get_shift_swap_requests(
    week_start_date: str | None = None,
    position_id: int | None = None,
    access_context: dict | None = Depends(services_access.require_schedule_view_if_auth_initialized),
):
    if access_context is None:
        raise HTTPException(status_code=403, detail="Shift swap requests require an authenticated account")
    connection = database.get_connection()
    try:
        if database_module.is_sqlite_runtime():
            services_sync_pull.pull_cloud_preferences_for_desktop_generation(connection)
            connection.commit()
        cursor = connection.cursor()
        organization_id = int(access_context["membership"]["organization_id"])
        role = access_context["membership"]["role"]
        clauses = ["ssr.organization_id = ?"]
        params: list = [organization_id]
        if week_start_date:
            schedule_time.parse_date_string(week_start_date)
            week_end_date = schedule_time.get_week_end_date(week_start_date)
            clauses.append(
                "((rse.date >= ? AND rse.date <= ?) OR (tse.date >= ? AND tse.date <= ?))"
            )
            params.extend([week_start_date, week_end_date, week_start_date, week_end_date])
        if position_id is not None:
            clauses.append("(rse.position_id = ? OR tse.position_id = ?)")
            params.extend([position_id, position_id])
            services_memberships.ensure_department_access_for_position(cursor, access_context, position_id)
        if role == "employee":
            employee_id = services_memberships.employee_scope_from_access(access_context)
            clauses.append("(ssr.requester_employee_id = ? OR ssr.target_employee_id = ?)")
            params.extend([employee_id, employee_id])
        else:
            allowed_department_ids = services_memberships.get_allowed_department_ids(cursor, access_context)
            if allowed_department_ids is not None:
                if not allowed_department_ids:
                    clauses.append("1 = 0")
                else:
                    placeholders = ",".join(["?"] * len(allowed_department_ids))
                    clauses.append(f"(rp.department_id IN ({placeholders}) OR tp.department_id IN ({placeholders}))")
                    params.extend(sorted(allowed_department_ids))
                    params.extend(sorted(allowed_department_ids))
        cursor.execute(services_swaps.shift_swap_select_sql(" AND ".join(clauses)), params)
        return [services_swaps.shift_swap_row_to_dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@router.post("/api/shift-swap-requests", tags=["Schedule"])
def create_shift_swap_request(
    request_data: ShiftSwapRequestCreate,
    access_context: dict | None = Depends(services_access.require_schedule_view_if_auth_initialized),
):
    if access_context is None or access_context["membership"]["role"] != "employee":
        raise HTTPException(status_code=403, detail="Only linked employees can request shift swaps")
    requester_employee_id = services_memberships.employee_scope_from_access(access_context)
    organization_id = int(access_context["membership"]["organization_id"])
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        if not app_settings_service.get_app_settings(connection, organization_id=organization_id).get("employee_shift_swap_requests_enabled", True):
            raise HTTPException(status_code=403, detail="Shift swap requests are disabled for employees")
        requester_entry = services_swaps.fetch_schedule_entry_for_swap(cursor, request_data.requester_schedule_entry_id, organization_id)
        target_entry = services_swaps.fetch_schedule_entry_for_swap(cursor, request_data.target_schedule_entry_id, organization_id)
        if int(requester_entry["employee_id"]) != requester_employee_id:
            raise HTTPException(status_code=403, detail="Employees can request swaps only for their own shifts")
        if int(target_entry["employee_id"]) == requester_employee_id:
            raise HTTPException(status_code=400, detail="Target shift must belong to another employee")
        if schedule_time.get_week_start_for_date(requester_entry["date"]) != schedule_time.get_week_start_for_date(target_entry["date"]):
            raise HTTPException(status_code=400, detail="Shift swaps must stay inside one week")

        candidate = {
            "organization_id": organization_id,
            "requester_employee_id": requester_employee_id,
            "target_employee_id": int(target_entry["employee_id"]),
            "requester_schedule_entry_id": int(requester_entry["id"]),
            "target_schedule_entry_id": int(target_entry["id"]),
        }
        services_swaps.validate_shift_swap_request_rows(connection, candidate)

        cursor.execute(
            """
            SELECT id
            FROM shift_swap_requests
            WHERE organization_id = ?
              AND requester_schedule_entry_id = ?
              AND target_schedule_entry_id = ?
              AND status IN ('pending_target', 'pending_admin')
            LIMIT 1
            """,
            (organization_id, requester_entry["id"], target_entry["id"]),
        )
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="This shift swap request is already pending")

        now = services_common.current_utc_timestamp()
        cursor.execute(
            """
            INSERT INTO shift_swap_requests (
                organization_id, requester_employee_id, target_employee_id,
                requester_schedule_entry_id, target_schedule_entry_id,
                status, requester_note, created_at, updated_at, updated_by
            )
            VALUES (?, ?, ?, ?, ?, 'pending_target', ?, ?, ?, ?)
            """,
            (
                organization_id,
                requester_employee_id,
                int(target_entry["employee_id"]),
                int(requester_entry["id"]),
                int(target_entry["id"]),
                request_data.requester_note,
                now,
                now,
                access_context["user"]["id"],
            ),
        )
        swap_request_id = int(cursor.lastrowid)
        services_audit.write_auth_audit_event(
            cursor,
            "shift_swap_requested",
            user_id=access_context["user"]["id"],
            organization_id=organization_id,
            metadata={
                "requester_schedule_entry_id": requester_entry["id"],
                "target_schedule_entry_id": target_entry["id"],
                "target_employee_id": target_entry["employee_id"],
            },
        )
        connection.commit()
        return {
            "message": "Shift swap request created",
            "request": services_swaps.shift_swap_row_to_dict(services_swaps.fetch_shift_swap_request(cursor, swap_request_id, organization_id)),
        }
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.patch("/api/shift-swap-requests/{swap_request_id}/target", tags=["Schedule"])
def answer_shift_swap_request_as_target(
    swap_request_id: int,
    decision: ShiftSwapTargetDecision,
    access_context: dict | None = Depends(services_access.require_schedule_view_if_auth_initialized),
):
    if access_context is None or access_context["membership"]["role"] != "employee":
        raise HTTPException(status_code=403, detail="Only the target employee can answer this request")
    employee_id = services_memberships.employee_scope_from_access(access_context)
    organization_id = int(access_context["membership"]["organization_id"])
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        swap_request = services_swaps.fetch_shift_swap_request(cursor, swap_request_id, organization_id)
        if int(swap_request["target_employee_id"]) != int(employee_id):
            raise HTTPException(status_code=403, detail="Only the target employee can answer this request")
        if swap_request["status"] != "pending_target":
            raise HTTPException(status_code=409, detail="Shift swap request is not waiting for employee approval")
        now = services_common.current_utc_timestamp()
        next_status = "pending_admin" if decision.status == "accepted" else "rejected"
        if next_status == "pending_admin":
            services_swaps.validate_shift_swap_request_rows(connection, swap_request)
        cursor.execute(
            """
            UPDATE shift_swap_requests
            SET status = ?,
                target_note = ?,
                target_responded_at = ?,
                updated_at = ?,
                updated_by = ?
            WHERE id = ? AND organization_id = ?
            """,
            (next_status, decision.note, now, now, access_context["user"]["id"], swap_request_id, organization_id),
        )
        services_audit.write_auth_audit_event(
            cursor,
            "shift_swap_target_answered",
            user_id=access_context["user"]["id"],
            organization_id=organization_id,
            metadata={"shift_swap_request_id": swap_request_id, "status": next_status},
        )
        connection.commit()
        return {
            "message": "Shift swap request updated",
            "request": services_swaps.shift_swap_row_to_dict(services_swaps.fetch_shift_swap_request(cursor, swap_request_id, organization_id)),
        }
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.patch("/api/shift-swap-requests/{swap_request_id}/cancel", tags=["Schedule"])
def cancel_shift_swap_request(
    swap_request_id: int,
    access_context: dict | None = Depends(services_access.require_schedule_view_if_auth_initialized),
):
    if access_context is None or access_context["membership"]["role"] != "employee":
        raise HTTPException(status_code=403, detail="Only the requester can cancel this request")
    employee_id = services_memberships.employee_scope_from_access(access_context)
    organization_id = int(access_context["membership"]["organization_id"])
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        swap_request = services_swaps.fetch_shift_swap_request(cursor, swap_request_id, organization_id)
        if int(swap_request["requester_employee_id"]) != int(employee_id):
            raise HTTPException(status_code=403, detail="Only the requester can cancel this request")
        if swap_request["status"] not in {"pending_target", "pending_admin"}:
            raise HTTPException(status_code=409, detail="Only pending shift swap requests can be cancelled")
        now = services_common.current_utc_timestamp()
        cursor.execute(
            """
            UPDATE shift_swap_requests
            SET status = 'cancelled',
                updated_at = ?,
                updated_by = ?
            WHERE id = ? AND organization_id = ?
            """,
            (now, access_context["user"]["id"], swap_request_id, organization_id),
        )
        connection.commit()
        return {
            "message": "Shift swap request cancelled",
            "request": services_swaps.shift_swap_row_to_dict(services_swaps.fetch_shift_swap_request(cursor, swap_request_id, organization_id)),
        }
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.patch("/api/shift-swap-requests/{swap_request_id}/review", tags=["Schedule"])
def review_shift_swap_request(
    swap_request_id: int,
    decision: ShiftSwapAdminDecision,
    access_context: dict | None = Depends(services_access.require_schedule_edit_if_auth_initialized),
):
    if access_context is None:
        raise HTTPException(status_code=403, detail="Schedule editing permissions are required")
    organization_id = int(access_context["membership"]["organization_id"])
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        swap_request = services_swaps.fetch_shift_swap_request(cursor, swap_request_id, organization_id)
        if swap_request["status"] != "pending_admin":
            raise HTTPException(status_code=409, detail="Shift swap request is not waiting for administrator approval")
        services_memberships.ensure_department_access_for_position(cursor, access_context, int(swap_request["requester_position_id"]))
        services_memberships.ensure_department_access_for_position(cursor, access_context, int(swap_request["target_position_id"]))
        now = services_common.current_utc_timestamp()
        if decision.status == "rejected":
            cursor.execute(
                """
                UPDATE shift_swap_requests
                SET status = 'rejected',
                    admin_note = ?,
                    reviewed_at = ?,
                    reviewed_by = ?,
                    updated_at = ?,
                    updated_by = ?
                WHERE id = ? AND organization_id = ?
                """,
                (decision.note, now, access_context["user"]["id"], now, access_context["user"]["id"], swap_request_id, organization_id),
            )
        else:
            requester_entry, target_entry = services_swaps.validate_shift_swap_request_rows(connection, swap_request)
            cursor.execute(
                """
                UPDATE schedule_entries
                SET employee_id = ?,
                    updated_at = ?,
                    updated_by = ?
                WHERE id = ? AND organization_id = ?
                """,
                (
                    int(swap_request["target_employee_id"]),
                    now,
                    access_context["user"]["id"],
                    int(swap_request["requester_schedule_entry_id"]),
                    organization_id,
                ),
            )
            cursor.execute(
                """
                UPDATE schedule_entries
                SET employee_id = ?,
                    updated_at = ?,
                    updated_by = ?
                WHERE id = ? AND organization_id = ?
                """,
                (
                    int(swap_request["requester_employee_id"]),
                    now,
                    access_context["user"]["id"],
                    int(swap_request["target_schedule_entry_id"]),
                    organization_id,
                ),
            )
            for employee_id, date_string in {
                (int(swap_request["requester_employee_id"]), requester_entry["date"]),
                (int(swap_request["requester_employee_id"]), target_entry["date"]),
                (int(swap_request["target_employee_id"]), requester_entry["date"]),
                (int(swap_request["target_employee_id"]), target_entry["date"]),
            }:
                services_day_status.sync_employee_day_off_status_for_date(connection, cursor, employee_id, date_string)
            cursor.execute(
                """
                UPDATE shift_swap_requests
                SET status = 'approved',
                    admin_note = ?,
                    reviewed_at = ?,
                    reviewed_by = ?,
                    updated_at = ?,
                    updated_by = ?
                WHERE id = ? AND organization_id = ?
                """,
                (decision.note, now, access_context["user"]["id"], now, access_context["user"]["id"], swap_request_id, organization_id),
            )
        services_audit.write_auth_audit_event(
            cursor,
            "shift_swap_reviewed",
            user_id=access_context["user"]["id"],
            organization_id=organization_id,
            metadata={"shift_swap_request_id": swap_request_id, "status": decision.status},
        )
        connection.commit()
        return {
            "message": "Shift swap request reviewed",
            "request": services_swaps.shift_swap_row_to_dict(services_swaps.fetch_shift_swap_request(cursor, swap_request_id, organization_id)),
        }
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()
