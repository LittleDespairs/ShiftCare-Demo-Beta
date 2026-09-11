"""Routes: schedule for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from schemas import ClearAllWeekScheduleRequest
from schemas import ClearWeekScheduleRequest
from schemas import ScheduleEntryCreate
from schemas import ScheduleEntryStatusUpdate
from schemas import ScheduleEntryTimeUpdate
from shiftcare.scheduling import data as scheduling_data
from shiftcare.scheduling import rules as scheduling_rules
from shiftcare.services import access as services_access
from shiftcare.services import backups as services_backups
from shiftcare.services import common as services_common
from shiftcare.services import day_status as services_day_status
from shiftcare.services import licensing as services_licensing
from shiftcare.services import memberships as services_memberships
from shiftcare.services import schedule as services_schedule
import database
import schedule_time

router = APIRouter()


@router.get("/api/schedule", tags=["Schedule"])
def get_schedule(
    position_id: int | None = None,
    access_context: dict | None = Depends(services_access.require_schedule_view_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        organization_id = access_context["membership"]["organization_id"] if access_context else None
        employee_id = services_memberships.employee_scope_from_access(access_context)
        if employee_id is not None and position_id is not None:
            services_memberships.require_employee_position_scope(cursor, employee_id, position_id)
            return services_schedule.get_schedule_entries(connection, position_id=position_id, organization_id=organization_id)
        if employee_id is None and position_id is not None:
            services_memberships.ensure_department_access_for_position(cursor, access_context, position_id)
        allowed_department_ids = None if employee_id is not None else services_memberships.get_allowed_department_ids(cursor, access_context)
        return services_schedule.get_schedule_entries(
            connection,
            position_id=position_id,
            employee_id=employee_id,
            organization_id=organization_id,
            department_ids=allowed_department_ids,
        )
    finally:
        connection.close()


@router.post("/api/schedule", tags=["Schedule"])
def add_schedule_entry(entry: ScheduleEntryCreate, _access: dict | None = Depends(services_access.require_schedule_edit_if_auth_initialized)):
    connection = database.get_connection()
    try:
        scheduling_rules.validate_manual_schedule_entry_basics(connection, entry)
        cursor = connection.cursor()
        organization_id = _access["membership"]["organization_id"] if _access else 1
        services_common.fetch_one_or_404(
            cursor,
            "SELECT id FROM positions WHERE id = ? AND organization_id = ?",
            (entry.position_id, organization_id),
            "Position not found",
        )
        services_common.fetch_one_or_404(
            cursor,
            "SELECT id FROM employees WHERE id = ? AND organization_id = ?",
            (entry.employee_id, organization_id),
            "Employee not found",
        )
        services_memberships.ensure_department_access_for_position(cursor, _access, entry.position_id)
        services_licensing.require_license_capability(cursor, "can_create_shift", organization_id)
        services_licensing.require_demo_schedule_entry_slot(cursor)
        cursor.execute(
            """
            INSERT INTO schedule_entries (organization_id, employee_id, position_id, date, shift_template_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (organization_id, entry.employee_id, entry.position_id, entry.date, entry.shift_template_id),
        )
        services_day_status.sync_employee_day_off_status_for_date(connection, cursor, entry.employee_id, entry.date)
        connection.commit()
        return {"message": "Schedule entry added successfully", "schedule_entry": {**entry.model_dump(), "id": cursor.lastrowid}}
    finally:
        connection.close()


@router.delete("/api/schedule/{schedule_entry_id}", tags=["Schedule"])
def delete_schedule_entry(
    schedule_entry_id: int,
    _access: dict | None = Depends(services_access.require_schedule_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        entry_row = services_common.fetch_one_or_404(
            cursor,
            "SELECT employee_id, position_id, date, organization_id FROM schedule_entries WHERE id = ?",
            (schedule_entry_id,),
            "Schedule entry not found",
        )
        if _access and int(entry_row["organization_id"]) != int(_access["membership"]["organization_id"]):
            raise HTTPException(status_code=404, detail="Schedule entry not found")
        services_memberships.ensure_department_access_for_position(cursor, _access, entry_row["position_id"])
        cursor.execute("DELETE FROM schedule_entries WHERE id = ?", (schedule_entry_id,))
        services_day_status.sync_employee_day_off_status_for_date(connection, cursor, entry_row["employee_id"], entry_row["date"])
        connection.commit()
        return {"message": "Schedule entry deleted successfully", "deleted_count": cursor.rowcount}
    finally:
        connection.close()


@router.patch("/api/schedule/{schedule_entry_id}/status", tags=["Schedule"])
def update_schedule_entry_status(
    schedule_entry_id: int,
    status: ScheduleEntryStatusUpdate,
    _access: dict | None = Depends(services_access.require_schedule_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        entry_row = services_common.fetch_one_or_404(
            cursor,
            "SELECT position_id, organization_id FROM schedule_entries WHERE id = ?",
            (schedule_entry_id,),
            "Schedule entry not found",
        )
        if _access and int(entry_row["organization_id"]) != int(_access["membership"]["organization_id"]):
            raise HTTPException(status_code=404, detail="Schedule entry not found")
        services_memberships.ensure_department_access_for_position(cursor, _access, entry_row["position_id"])
        cursor.execute(
            "UPDATE schedule_entries SET no_show = ? WHERE id = ?",
            (int(status.no_show), schedule_entry_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Schedule entry not found")
        connection.commit()
        return {"message": "Schedule entry status updated successfully", "id": schedule_entry_id, "no_show": status.no_show}
    finally:
        connection.close()


@router.patch("/api/schedule/{schedule_entry_id}/time", tags=["Schedule"])
def update_schedule_entry_time(
    schedule_entry_id: int,
    time_update: ScheduleEntryTimeUpdate,
    _access: dict | None = Depends(services_access.require_schedule_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        entry_row = services_common.fetch_one_or_404(
            cursor,
            "SELECT employee_id, position_id, date, organization_id FROM schedule_entries WHERE id = ?",
            (schedule_entry_id,),
            "Schedule entry not found",
        )
        if _access and int(entry_row["organization_id"]) != int(_access["membership"]["organization_id"]):
            raise HTTPException(status_code=404, detail="Schedule entry not found")
        services_memberships.ensure_department_access_for_position(cursor, _access, entry_row["position_id"])

        now = services_common.current_utc_timestamp()
        user_id = _access["user"]["id"] if _access else None
        if time_update.reset:
            cursor.execute(
                """
                UPDATE schedule_entries
                SET start_time_override = NULL,
                    end_time_override = NULL,
                    is_overnight_override = NULL,
                    updated_at = ?,
                    updated_by = ?
                WHERE id = ?
                """,
                (now, user_id, schedule_entry_id),
            )
        else:
            start_time = time_update.start_time
            end_time = time_update.end_time
            is_overnight = bool(time_update.is_overnight) if time_update.is_overnight is not None else False
            if schedule_time.time_to_minutes(end_time) <= schedule_time.time_to_minutes(start_time):
                is_overnight = True
            cursor.execute(
                """
                UPDATE schedule_entries
                SET start_time_override = ?,
                    end_time_override = ?,
                    is_overnight_override = ?,
                    updated_at = ?,
                    updated_by = ?
                WHERE id = ?
                """,
                (start_time, end_time, int(is_overnight), now, user_id, schedule_entry_id),
            )

        connection.commit()
        updated_entries = services_schedule.get_schedule_entries(
            connection,
            dates=[entry_row["date"]],
            employee_id=entry_row["employee_id"],
            organization_id=entry_row["organization_id"],
        )
        updated_entry = next((entry for entry in updated_entries if entry["id"] == schedule_entry_id), None)
        return {
            "message": "Schedule entry time updated successfully",
            "schedule_entry": updated_entry,
        }
    finally:
        connection.close()


@router.post("/api/schedule/clear-week", tags=["Schedule"])
def clear_week_schedule(
    request_data: ClearWeekScheduleRequest,
    _access: dict | None = Depends(services_access.require_schedule_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        week_dates = schedule_time.build_week_dates(request_data.week_start_date)
        cursor = connection.cursor()
        organization_id = _access["membership"]["organization_id"] if _access else None
        services_memberships.ensure_department_access_for_position(cursor, _access, request_data.position_id)
        backup_name = services_backups.create_recovery_backup("clear_week")
        employees = scheduling_data.load_position_employees(connection, request_data.position_id)
        employee_ids = [employee["id"] for employee in employees]
        deleted_count, day_off_deleted_count = services_schedule.clear_week_schedule_records(
            cursor,
            week_dates,
            position_id=request_data.position_id,
            employee_ids=employee_ids,
            organization_id=organization_id,
        )
        connection.commit()
        return {
            "message": "Week schedule cleared successfully",
            "deleted_count": deleted_count,
            "day_off_deleted_count": day_off_deleted_count,
            "backup_name": backup_name,
        }
    finally:
        connection.close()


@router.get("/api/schedule/clear-week-preview", tags=["Schedule"])
def get_clear_week_schedule_preview(
    position_id: int,
    week_start_date: str,
    _access: dict | None = Depends(services_access.require_schedule_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        week_dates = schedule_time.build_week_dates(week_start_date)
        cursor = connection.cursor()
        position_row = services_common.fetch_one_or_404(
            cursor,
            "SELECT id, name, organization_id FROM positions WHERE id = ?",
            (position_id,),
            "Position not found",
        )
        if _access and int(position_row["organization_id"]) != int(_access["membership"]["organization_id"]):
            raise HTTPException(status_code=404, detail="Position not found")
        services_memberships.ensure_department_access_for_position(cursor, _access, position_id)
        employees = scheduling_data.load_position_employees(connection, position_id)
        employee_ids = [employee["id"] for employee in employees]
        day_status_count = 0

        if employee_ids:
            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM employee_day_statuses
                WHERE status_type = 'day_off'
                  AND employee_id IN ({','.join(['?'] * len(employee_ids))})
                  AND date IN ({','.join(['?'] * len(week_dates))})
                """,
                [*employee_ids, *week_dates],
            )
            day_status_count = int(cursor.fetchone()[0])

        return {
            "position_id": position_row["id"],
            "position_name": position_row["name"],
            "week_start_date": week_start_date,
            "assigned_employees": len(employee_ids),
            "schedule_entries": services_common.fetch_count(
                cursor,
                f"""
                SELECT COUNT(*)
                FROM schedule_entries
                WHERE position_id = ? AND date IN ({','.join(['?'] * len(week_dates))})
                """,
                (position_id, *week_dates),
            ),
            "day_off_statuses": day_status_count,
        }
    finally:
        connection.close()


@router.post("/api/schedule/clear-week-all", tags=["Schedule"])
def clear_all_week_schedules(
    request_data: ClearAllWeekScheduleRequest,
    _access: dict | None = Depends(services_access.require_schedule_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        week_dates = schedule_time.build_week_dates(request_data.week_start_date)
        cursor = connection.cursor()
        organization_id = _access["membership"]["organization_id"] if _access else None
        allowed_department_ids = services_memberships.get_allowed_department_ids(cursor, _access)
        backup_name = services_backups.create_recovery_backup("clear_week_all")
        deleted_count, day_off_deleted_count = services_schedule.clear_week_schedule_records(
            cursor,
            week_dates,
            organization_id=organization_id,
            department_ids=allowed_department_ids,
        )
        connection.commit()
        return {
            "message": "All week schedules cleared successfully",
            "deleted_count": deleted_count,
            "day_off_deleted_count": day_off_deleted_count,
            "backup_name": backup_name,
        }
    finally:
        connection.close()


@router.get("/api/schedule/clear-week-all-preview", tags=["Schedule"])
def get_clear_all_week_schedules_preview(
    week_start_date: str,
    _access: dict | None = Depends(services_access.require_schedule_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        week_dates = schedule_time.build_week_dates(week_start_date)
        cursor = connection.cursor()
        organization_id = _access["membership"]["organization_id"] if _access else None
        allowed_department_ids = services_memberships.get_allowed_department_ids(cursor, _access)
        position_conditions = []
        position_params: list = []
        schedule_conditions = [f"date IN ({','.join(['?'] * len(week_dates))})"]
        schedule_params: list = [*week_dates]
        day_status_conditions = ["status_type = 'day_off'", f"date IN ({','.join(['?'] * len(week_dates))})"]
        day_status_params: list = [*week_dates]
        if organization_id is not None:
            position_conditions.append("organization_id = ?")
            position_params.append(organization_id)
            schedule_conditions.append("organization_id = ?")
            schedule_params.append(organization_id)
            day_status_conditions.append("organization_id = ?")
            day_status_params.append(organization_id)
        if allowed_department_ids is not None:
            if not allowed_department_ids:
                position_conditions.append("1 = 0")
                schedule_conditions.append("1 = 0")
                day_status_conditions.append("1 = 0")
            else:
                placeholders = ",".join(["?"] * len(allowed_department_ids))
                position_conditions.append(f"department_id IN ({placeholders})")
                position_params.extend(sorted(allowed_department_ids))
                schedule_conditions.append(
                    f"position_id IN (SELECT id FROM positions WHERE department_id IN ({placeholders}))"
                )
                schedule_params.extend(sorted(allowed_department_ids))
                day_status_conditions.append(
                    f"""
                    employee_id IN (
                        SELECT DISTINCT ep.employee_id
                        FROM employee_positions ep
                        JOIN positions p ON p.id = ep.position_id
                        WHERE p.department_id IN ({placeholders})
                    )
                    """
                )
                day_status_params.extend(sorted(allowed_department_ids))
        position_where = f"WHERE {' AND '.join(position_conditions)}" if position_conditions else ""
        return {
            "week_start_date": week_start_date,
            "positions": services_common.fetch_count(cursor, f"SELECT COUNT(*) FROM positions {position_where}", tuple(position_params)),
            "schedule_entries": services_common.fetch_count(
                cursor,
                f"""
                SELECT COUNT(*)
                FROM schedule_entries
                WHERE {" AND ".join(schedule_conditions)}
                """,
                tuple(schedule_params),
            ),
            "day_off_statuses": services_common.fetch_count(
                cursor,
                f"""
                SELECT COUNT(*)
                FROM employee_day_statuses
                WHERE {" AND ".join(day_status_conditions)}
                """,
                tuple(day_status_params),
            ),
        }
    finally:
        connection.close()
