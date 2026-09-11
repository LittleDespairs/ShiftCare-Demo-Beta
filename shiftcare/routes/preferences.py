"""Routes: preferences for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from schemas import EmployeeDayStatusCreate
from schemas import EmployeePreferenceCreate
from schemas import EmployeeRecurringPreferencesUpdate
from schemas import EmployeeWeekPreferenceCreate
from schemas import EmployeeWeekPreferenceRequestDecision
from shiftcare import config as app_constants
from shiftcare.services import access as services_access
from shiftcare.services import audit as services_audit
from shiftcare.services import common as services_common
from shiftcare.services import memberships as services_memberships
from shiftcare.services import preference_requests as services_preference_requests
from shiftcare.services import sync_pull as services_sync_pull
import database

router = APIRouter()


@router.get("/api/employee-preferences", tags=["Preferences"])
def get_employee_preferences(preference_context: dict | None = Depends(services_access.require_preference_access_if_auth_initialized)):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        params = ()
        scope_filter = ""
        if preference_context and preference_context["scope"] == "own":
            scope_filter = "WHERE ep.employee_id = ?"
            params = (preference_context["membership"]["employee_id"],)
        cursor.execute(
            f"""
            SELECT ep.*, e.full_name AS employee_name
            FROM employee_preferences ep
            JOIN employees e ON e.id = ep.employee_id
            {scope_filter}
            ORDER BY ep.employee_id
            """,
            params,
        )
        items = [dict(row) for row in cursor.fetchall()]
        for item in items:
            for key in ("allow_morning", "allow_evening", "allow_night", "allow_morning_evening_combo"):
                item[key] = bool(item[key])
        return items
    finally:
        connection.close()


@router.post("/api/employee-preferences", tags=["Preferences"])
def save_employee_preference(
    preference: EmployeePreferenceCreate,
    preference_context: dict | None = Depends(services_access.require_preference_access_if_auth_initialized),
):
    services_memberships.require_employee_preference_scope(preference_context, preference.employee_id)
    organization_id = preference_context["membership"]["organization_id"] if preference_context else 1
    user_id = preference_context["user"]["id"] if preference_context else None
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        services_common.fetch_one_or_404(
            cursor,
            "SELECT id FROM employees WHERE id = ? AND organization_id = ?",
            (preference.employee_id, organization_id),
            "Employee not found",
        )
        now = services_common.current_utc_timestamp()
        cursor.execute(
            """
            INSERT INTO employee_preferences
                (organization_id, employee_id, allow_morning, allow_evening, allow_night,
                 allow_morning_evening_combo, updated_at, updated_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(employee_id)
            DO UPDATE SET allow_morning = excluded.allow_morning,
                          allow_evening = excluded.allow_evening,
                          allow_night = excluded.allow_night,
                          allow_morning_evening_combo = excluded.allow_morning_evening_combo,
                          updated_at = excluded.updated_at,
                          updated_by = excluded.updated_by
            """,
            (
                organization_id,
                preference.employee_id,
                int(preference.allow_morning),
                int(preference.allow_evening),
                int(preference.allow_night),
                int(preference.allow_morning_evening_combo),
                now,
                user_id,
            ),
        )
        services_audit.write_auth_audit_event(
            cursor,
            "employee_preference_saved",
            user_id=user_id,
            organization_id=organization_id,
            metadata={"employee_id": preference.employee_id},
        )
        connection.commit()
        return {"message": "Employee preference saved successfully", "preference": preference.model_dump()}
    finally:
        connection.close()


@router.get("/api/employee-week-preferences", tags=["Weekly Preferences"])
def get_employee_week_preferences(
    week_start_date: str,
    preference_context: dict | None = Depends(services_access.require_preference_access_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        services_sync_pull.pull_cloud_preferences_for_desktop_generation(connection)
        connection.commit()
        cursor = connection.cursor()
        filters = ["ewp.week_start_date = ?"]
        params: list = [week_start_date]
        if preference_context:
            filters.append("ewp.organization_id = ?")
            params.append(preference_context["membership"]["organization_id"])
        if preference_context and preference_context["scope"] == "own":
            filters.append("ewp.employee_id = ?")
            params.append(preference_context["membership"]["employee_id"])
        cursor.execute(
            f"""
            SELECT ewp.*, e.full_name AS employee_name
            FROM employee_week_preferences ewp
            JOIN employees e ON e.id = ewp.employee_id
            WHERE {" AND ".join(filters)}
            ORDER BY ewp.employee_id, ewp.preference_date
            """,
            tuple(params),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@router.get("/api/employee-week-preference-requests", tags=["Weekly Preferences"])
def get_employee_week_preference_requests(
    week_start_date: str | None = None,
    status: str | None = None,
    skip_cloud_pull: bool = False,
    preference_context: dict | None = Depends(services_access.require_preference_access_if_auth_initialized),
):
    if status and status not in {"pending", "approved", "rejected"}:
        raise HTTPException(status_code=400, detail="Unsupported request status")
    organization_id = preference_context["membership"]["organization_id"] if preference_context else 1
    connection = database.get_connection()
    try:
        if not skip_cloud_pull:
            services_sync_pull.pull_cloud_preferences_for_desktop_generation(connection)
            connection.commit()
        cursor = connection.cursor()
        filters = ["ewpr.organization_id = ?"]
        params: list = [organization_id]
        if week_start_date:
            filters.append("ewpr.week_start_date = ?")
            params.append(week_start_date)
        if status:
            filters.append("ewpr.status = ?")
            params.append(status)
        if preference_context and preference_context["scope"] == "own":
            filters.append("ewpr.employee_id = ?")
            params.append(preference_context["membership"]["employee_id"])
        else:
            allowed_department_ids = services_memberships.get_allowed_department_ids(cursor, preference_context)
            if allowed_department_ids is not None:
                if not allowed_department_ids:
                    filters.append("1 = 0")
                else:
                    placeholders = ",".join(["?"] * len(allowed_department_ids))
                    filters.append(
                        f"""
                        EXISTS (
                            SELECT 1
                            FROM employee_positions ep
                            JOIN positions p ON p.id = ep.position_id
                            WHERE ep.employee_id = ewpr.employee_id
                              AND p.department_id IN ({placeholders})
                        )
                        """
                    )
                    params.extend(sorted(allowed_department_ids))
        cursor.execute(
            f"""
            SELECT ewpr.*, e.full_name AS employee_name
            FROM employee_week_preference_requests ewpr
            JOIN employees e ON e.id = ewpr.employee_id
            WHERE {" AND ".join(filters)}
            ORDER BY
                CASE ewpr.status WHEN 'pending' THEN 0 WHEN 'rejected' THEN 1 ELSE 2 END,
                ewpr.preference_date,
                e.full_name,
                ewpr.created_at DESC,
                ewpr.id DESC
            """,
            tuple(params),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@router.patch("/api/employee-week-preference-requests/{request_id}", tags=["Weekly Preferences"])
def decide_employee_week_preference_request(
    request_id: int,
    decision: EmployeeWeekPreferenceRequestDecision,
    approval_context: dict | None = Depends(services_access.require_week_preference_approval_if_auth_initialized),
):
    organization_id = approval_context["membership"]["organization_id"] if approval_context else 1
    user_id = approval_context["user"]["id"] if approval_context else None
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        request_row = services_common.fetch_one_or_404(
            cursor,
            """
            SELECT *
            FROM employee_week_preference_requests
            WHERE id = ? AND organization_id = ?
            """,
            (request_id, organization_id),
            "Preference request not found",
        )
        services_memberships.ensure_department_access_for_employee(cursor, approval_context, int(request_row["employee_id"]))
        if request_row["status"] != "pending":
            raise HTTPException(status_code=409, detail="Preference request has already been reviewed")

        now = services_common.current_utc_timestamp()
        approved_preference_id = None
        if decision.status == "approved":
            preference = EmployeeWeekPreferenceCreate(
                employee_id=int(request_row["employee_id"]),
                week_start_date=str(request_row["week_start_date"]),
                preference_date=str(request_row["preference_date"]),
                preference_type=str(request_row["preference_type"]),
                request_type=str(request_row["request_type"]),
                target_category=request_row["target_category"],
            )
            approved_preference_id = services_preference_requests.save_confirmed_week_preference(
                cursor,
                preference,
                organization_id,
                user_id,
                now,
                cleanup_pending=False,
            )

        cursor.execute(
            """
            UPDATE employee_week_preference_requests
            SET status = ?,
                reviewed_at = ?,
                reviewed_by = ?,
                updated_at = ?,
                updated_by = ?
            WHERE id = ? AND organization_id = ?
            """,
            (decision.status, now, user_id, now, user_id, request_id, organization_id),
        )
        services_audit.write_auth_audit_event(
            cursor,
            "employee_week_preference_request_reviewed",
            user_id=user_id,
            organization_id=organization_id,
            metadata={
                "request_id": request_id,
                "employee_id": int(request_row["employee_id"]),
                "status": decision.status,
                "approved_preference_id": approved_preference_id,
            },
        )
        connection.commit()
        return {
            "message": "Weekly preference request reviewed successfully",
            "request_id": request_id,
            "status": decision.status,
            "approved_preference_id": approved_preference_id,
        }
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.delete("/api/employee-week-preference-requests/{request_id}", tags=["Weekly Preferences"])
def delete_employee_week_preference_request(
    request_id: int,
    preference_context: dict | None = Depends(services_access.require_preference_access_if_auth_initialized),
):
    organization_id = preference_context["membership"]["organization_id"] if preference_context else 1
    user_id = preference_context["user"]["id"] if preference_context else None
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        request_row = services_common.fetch_one_or_404(
            cursor,
            """
            SELECT *
            FROM employee_week_preference_requests
            WHERE id = ? AND organization_id = ?
            """,
            (request_id, organization_id),
            "Preference request not found",
        )
        if preference_context and preference_context.get("scope") == "own":
            services_memberships.require_employee_preference_scope(preference_context, int(request_row["employee_id"]))
        else:
            services_memberships.ensure_department_access_for_employee(cursor, preference_context, int(request_row["employee_id"]))

        cursor.execute(
            """
            DELETE FROM employee_week_preference_requests
            WHERE id = ? AND organization_id = ?
            """,
            (request_id, organization_id),
        )
        deleted_count = cursor.rowcount
        services_audit.write_auth_audit_event(
            cursor,
            "employee_week_preference_request_deleted",
            user_id=user_id,
            organization_id=organization_id,
            metadata={
                "request_id": request_id,
                "employee_id": int(request_row["employee_id"]),
                "week_start_date": request_row["week_start_date"],
                "preference_date": request_row["preference_date"],
                "status": request_row["status"],
            },
        )
        connection.commit()
        return {
            "message": "Weekly preference request deleted successfully",
            "request_id": request_id,
            "deleted_count": deleted_count,
        }
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.post("/api/employee-week-preferences", tags=["Weekly Preferences"])
def save_employee_week_preference(
    preference: EmployeeWeekPreferenceCreate,
    preference_context: dict | None = Depends(services_access.require_preference_access_if_auth_initialized),
):
    services_memberships.require_employee_preference_scope(preference_context, preference.employee_id)
    organization_id = preference_context["membership"]["organization_id"] if preference_context else 1
    user_id = preference_context["user"]["id"] if preference_context else None
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        services_common.fetch_one_or_404(
            cursor,
            "SELECT id FROM employees WHERE id = ? AND organization_id = ?",
            (preference.employee_id, organization_id),
            "Employee not found",
        )
        now = services_common.current_utc_timestamp()
        if services_preference_requests.should_queue_week_preference_for_approval(cursor, preference_context, organization_id, preference):
            request_id = services_preference_requests.queue_week_preference_request(cursor, preference, organization_id, user_id, now)
            services_audit.write_auth_audit_event(
                cursor,
                "employee_week_preference_request_queued",
                user_id=user_id,
                organization_id=organization_id,
                metadata={
                    "employee_id": preference.employee_id,
                    "week_start_date": preference.week_start_date,
                    "preference_date": preference.preference_date,
                    "preference_type": preference.preference_type,
                    "request_type": preference.request_type,
                    "target_category": preference.target_category,
                    "direct_day_limit": app_constants.EMPLOYEE_DIRECT_WEEKLY_PREFERENCE_DAY_LIMIT,
                },
            )
            connection.commit()
            return {
                "message": "Weekly preference request queued for administrator approval",
                "status": "pending_approval",
                "request": {**preference.model_dump(), "id": request_id, "status": "pending"},
            }
        preference_id = services_preference_requests.save_confirmed_week_preference(cursor, preference, organization_id, user_id, now)
        services_audit.write_auth_audit_event(
            cursor,
            "employee_week_preference_saved",
            user_id=user_id,
            organization_id=organization_id,
            metadata={
                "employee_id": preference.employee_id,
                "week_start_date": preference.week_start_date,
                "preference_date": preference.preference_date,
                "preference_type": preference.preference_type,
                "request_type": preference.request_type,
                "target_category": preference.target_category,
            },
        )
        connection.commit()
        return {
            "message": "Weekly preference saved successfully",
            "status": "saved",
            "preference": {**preference.model_dump(), "id": preference_id},
        }
    finally:
        connection.close()


@router.delete("/api/employee-week-preferences", tags=["Weekly Preferences"])
def delete_employee_week_preference(
    employee_id: int,
    preference_date: str,
    preference_id: int | None = None,
    preference_context: dict | None = Depends(services_access.require_preference_access_if_auth_initialized),
):
    services_memberships.require_employee_preference_scope(preference_context, employee_id)
    organization_id = preference_context["membership"]["organization_id"] if preference_context else 1
    user_id = preference_context["user"]["id"] if preference_context else None
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        if preference_id is not None:
            cursor.execute(
                """
                DELETE FROM employee_week_preferences
                WHERE organization_id = ? AND employee_id = ? AND preference_date = ? AND id = ?
                """,
                (organization_id, employee_id, preference_date, preference_id),
            )
        else:
            cursor.execute(
                """
                DELETE FROM employee_week_preferences
                WHERE organization_id = ? AND employee_id = ? AND preference_date = ?
                """,
                (organization_id, employee_id, preference_date),
            )
        services_audit.write_auth_audit_event(
            cursor,
            "employee_week_preference_deleted",
            user_id=user_id,
            organization_id=organization_id,
            metadata={"employee_id": employee_id, "preference_date": preference_date},
        )
        connection.commit()
        return {"message": "Weekly preference deleted successfully", "deleted_count": cursor.rowcount}
    finally:
        connection.close()


@router.get("/api/employee-recurring-preferences", tags=["Permanent Preferences"])
def get_employee_recurring_preferences(
    employee_id: int | None = None,
    admin_context: dict | None = Depends(services_access.require_permanent_preference_admin_if_auth_initialized),
):
    organization_id = admin_context["membership"]["organization_id"] if admin_context else 1
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        filters = ["erp.organization_id = ?"]
        params: list = [organization_id]
        if employee_id is not None:
            services_common.fetch_one_or_404(
                cursor,
                "SELECT id FROM employees WHERE id = ? AND organization_id = ?",
                (employee_id, organization_id),
                "Employee not found",
            )
            filters.append("erp.employee_id = ?")
            params.append(employee_id)
        cursor.execute(
            f"""
            SELECT erp.*, e.full_name AS employee_name
            FROM employee_recurring_preferences erp
            JOIN employees e ON e.id = erp.employee_id
            WHERE {" AND ".join(filters)}
            ORDER BY erp.employee_id, erp.preference_kind, erp.day_of_week
            """,
            tuple(params),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@router.post("/api/employee-recurring-preferences", tags=["Permanent Preferences"])
def save_employee_recurring_preferences(
    request_data: EmployeeRecurringPreferencesUpdate,
    admin_context: dict | None = Depends(services_access.require_permanent_preference_admin_if_auth_initialized),
):
    organization_id = admin_context["membership"]["organization_id"] if admin_context else 1
    user_id = admin_context["user"]["id"] if admin_context else None
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        services_common.fetch_one_or_404(
            cursor,
            "SELECT id FROM employees WHERE id = ? AND organization_id = ?",
            (request_data.employee_id, organization_id),
            "Employee not found",
        )
        now = services_common.current_utc_timestamp()
        cursor.execute(
            """
            DELETE FROM employee_recurring_preferences
            WHERE organization_id = ? AND employee_id = ?
            """,
            (organization_id, request_data.employee_id),
        )
        saved_rules = []
        for rule in request_data.rules:
            if rule.preference_type == "no_preference":
                continue
            if rule.preference_type not in app_constants.PERSISTED_RECURRING_PREFERENCE_TYPES:
                raise HTTPException(status_code=400, detail="Unsupported permanent preference type")
            cursor.execute(
                """
                INSERT INTO employee_recurring_preferences (
                    organization_id, employee_id, preference_kind, day_of_week,
                    preference_type, request_type, target_category, created_at, updated_at, updated_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    organization_id,
                    request_data.employee_id,
                    rule.preference_kind,
                    rule.day_of_week,
                    rule.preference_type,
                    rule.request_type,
                    rule.target_category,
                    now,
                    now,
                    user_id,
                ),
            )
            saved_rules.append(rule.model_dump())
        services_audit.write_auth_audit_event(
            cursor,
            "employee_recurring_preferences_saved",
            user_id=user_id,
            organization_id=organization_id,
            metadata={"employee_id": request_data.employee_id, "rule_count": len(saved_rules)},
        )
        connection.commit()
        return {
            "message": "Permanent preferences saved successfully",
            "employee_id": request_data.employee_id,
            "rules": saved_rules,
        }
    except HTTPException:
        connection.rollback()
        raise
    finally:
        connection.close()


@router.get("/api/employee-day-statuses", tags=["Schedule"])
def get_employee_day_statuses(
    position_id: int | None = None,
    access_context: dict | None = Depends(services_access.require_schedule_view_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        employee_id = services_memberships.employee_scope_from_access(access_context)
        params: tuple = ()
        where_sql = ""
        if employee_id is not None and position_id is not None:
            services_memberships.require_employee_position_scope(cursor, employee_id, position_id)
            where_sql = """
            WHERE eds.employee_id IN (
                SELECT ep.employee_id
                FROM employee_positions ep
                WHERE ep.position_id = ?
            )
            """
            params = (position_id,)
        elif employee_id is not None:
            where_sql = "WHERE eds.employee_id = ?"
            params = (employee_id,)
        elif position_id is not None:
            services_memberships.ensure_department_access_for_position(cursor, access_context, position_id)
            where_sql = """
            WHERE eds.employee_id IN (
                SELECT ep.employee_id
                FROM employee_positions ep
                WHERE ep.position_id = ?
            )
            """
            params = (position_id,)
        else:
            conditions = []
            params_list: list = []
            allowed_department_ids = services_memberships.get_allowed_department_ids(cursor, access_context)
            if allowed_department_ids is not None:
                if not allowed_department_ids:
                    conditions.append("1 = 0")
                else:
                    placeholders = ",".join(["?"] * len(allowed_department_ids))
                    conditions.append(
                        f"""
                        eds.employee_id IN (
                            SELECT DISTINCT ep.employee_id
                            FROM employee_positions ep
                            JOIN positions p ON p.id = ep.position_id
                            WHERE p.department_id IN ({placeholders})
                        )
                        """
                    )
                    params_list.extend(sorted(allowed_department_ids))
            if access_context:
                conditions.append("eds.organization_id = ?")
                params_list.append(access_context["membership"]["organization_id"])
            if conditions:
                where_sql = f"WHERE {' AND '.join(conditions)}"
                params = tuple(params_list)
        cursor.execute(
            f"""
            SELECT eds.*, e.full_name AS employee_name
            FROM employee_day_statuses eds
            JOIN employees e ON e.id = eds.employee_id
            {where_sql}
            ORDER BY eds.date, eds.employee_id
            """,
            params,
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@router.post("/api/employee-day-statuses", tags=["Schedule"])
def save_employee_day_status(
    status: EmployeeDayStatusCreate,
    _access: dict | None = Depends(services_access.require_schedule_edit_if_auth_initialized),
):
    organization_id = _access["membership"]["organization_id"] if _access else 1
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        services_common.fetch_one_or_404(
            cursor,
            "SELECT id FROM employees WHERE id = ? AND organization_id = ?",
            (status.employee_id, organization_id),
            "Employee not found",
        )
        services_memberships.ensure_department_access_for_employee(cursor, _access, status.employee_id)
        cursor.execute(
            """
            INSERT INTO employee_day_statuses (organization_id, employee_id, date, status_type)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(employee_id, date)
            DO UPDATE SET organization_id = excluded.organization_id,
                          status_type = excluded.status_type
            """,
            (organization_id, status.employee_id, status.date, status.status_type),
        )
        connection.commit()
        return {"message": "Employee day status saved successfully", "status": status.model_dump()}
    finally:
        connection.close()


@router.delete("/api/employee-day-statuses", tags=["Schedule"])
def delete_employee_day_status(
    employee_id: int,
    date: str,
    _access: dict | None = Depends(services_access.require_schedule_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        services_memberships.ensure_department_access_for_employee(cursor, _access, employee_id)
        cursor.execute("DELETE FROM employee_day_statuses WHERE employee_id = ? AND date = ?", (employee_id, date))
        connection.commit()
        return {"message": "Employee day status deleted successfully"}
    finally:
        connection.close()
