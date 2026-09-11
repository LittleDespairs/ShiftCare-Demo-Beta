"""Routes: exports for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi.responses import StreamingResponse
from shiftcare.scheduling import data as scheduling_data
from shiftcare.services import access as services_access
from shiftcare.services import audit as services_audit
from shiftcare.services import authentication as services_authentication
from shiftcare.services import common as services_common
from shiftcare.services import day_status as services_day_status
from shiftcare.services import licensing as services_licensing
from shiftcare.services import memberships as services_memberships
from shiftcare.services import schedule as services_schedule
import database
import excel_export
import row_serializers
import schedule_time
import word_export

router = APIRouter()


@router.get("/api/schedule/export-excel", tags=["Schedule"])
def export_schedule_excel(
    week_start_date: str,
    position_id: int,
    lang: str = "en",
    access_context: dict | None = Depends(services_access.require_schedule_view_if_auth_initialized),
    current_user: dict | None = Depends(services_authentication.get_optional_current_user),
):
    connection = database.get_connection()
    try:
        if lang not in {"en", "ru", "he"}:
            lang = "en"
        week_dates = schedule_time.build_week_dates(week_start_date)
        cursor = connection.cursor()
        position_row = services_common.fetch_one_or_404(
            cursor,
            """
            SELECT p.*, d.public_id AS department_public_id, d.name AS department_name
            FROM positions p
            LEFT JOIN departments d ON d.id = p.department_id
            WHERE p.id = ?
              AND (? IS NULL OR p.organization_id = ?)
            """,
            (
                position_id,
                access_context["membership"]["organization_id"] if access_context else None,
                access_context["membership"]["organization_id"] if access_context else None,
            ),
            "Position not found",
        )
        position = row_serializers.row_to_position_dict(position_row)
        employee_scope = services_memberships.employee_scope_from_access(access_context)
        employees = [
            employee for employee in scheduling_data.load_position_employees(connection, position_id)
            if employee_scope is None or employee["id"] == employee_scope
        ]
        employee_ids = {employee["id"] for employee in employees}
        entries = [
            entry
            for entry in services_schedule.get_schedule_entries(
                connection,
                dates=week_dates,
                employee_id=employee_scope,
                organization_id=access_context["membership"]["organization_id"] if access_context else None,
            )
            if entry["employee_id"] in employee_ids
        ]
        day_status_map = services_day_status.get_employee_day_status_map(connection, [employee["id"] for employee in employees], week_dates)
        output = excel_export.build_schedule_export_workbook(
            position=position,
            week_start_date=week_start_date,
            week_dates=week_dates,
            employees=employees,
            entries=entries,
            day_status_map=day_status_map,
            lang=lang,
        )
        safe_position_name = position["name"].replace(" ", "_")
        filename = f"schedule_{safe_position_name}_{week_start_date}.xlsx"
        user_id, organization_id = services_licensing.audit_context_from_user(current_user)
        services_audit.write_auth_audit_event_record(
            "schedule_exported",
            user_id=user_id,
            organization_id=organization_id,
            metadata={
                "format": "excel",
                "scope": "position",
                "week_start_date": week_start_date,
                "position_id": position_id,
                "lang": lang,
                "filename": filename,
            },
        )
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        connection.close()


@router.get("/api/schedule/export-excel-all", tags=["Schedule"])
def export_all_schedules_excel(
    week_start_date: str,
    lang: str = "en",
    access_context: dict | None = Depends(services_access.require_schedule_view_if_auth_initialized),
    current_user: dict | None = Depends(services_authentication.get_optional_current_user),
):
    connection = database.get_connection()
    try:
        if lang not in {"en", "ru", "he"}:
            lang = "en"
        week_dates = schedule_time.build_week_dates(week_start_date)
        cursor = connection.cursor()
        employee_scope = services_memberships.employee_scope_from_access(access_context)
        if employee_scope is not None:
            cursor.execute(
                """
                SELECT p.*, d.public_id AS department_public_id, d.name AS department_name,
                       ep.is_primary, ep.priority_score, ep.is_fallback_only
                FROM positions p
                LEFT JOIN departments d ON d.id = p.department_id
                JOIN employee_positions ep ON ep.position_id = p.id
                WHERE ep.employee_id = ?
                ORDER BY d.display_order, d.id, ep.is_primary DESC, ep.is_fallback_only ASC, ep.priority_score DESC, p.id
                """,
                (employee_scope,),
            )
        else:
            conditions = []
            params: list = []
            if access_context:
                conditions.append("p.organization_id = ?")
                params.append(access_context["membership"]["organization_id"])
            services_memberships.append_department_access_condition(cursor, access_context, conditions, params)
            where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            cursor.execute(
                f"""
                SELECT p.*, d.public_id AS department_public_id, d.name AS department_name
                FROM positions p
                LEFT JOIN departments d ON d.id = p.department_id
                {where_sql}
                ORDER BY d.display_order, d.id, p.id
                """,
                params,
            )
        positions = [row_serializers.row_to_position_dict(row) for row in cursor.fetchall()]
        employees_by_position = {
            position["id"]: [
                employee for employee in scheduling_data.load_position_employees(connection, position["id"])
                if employee_scope is None or employee["id"] == employee_scope
            ]
            for position in positions
        }
        employee_ids = sorted({
            employee["id"]
            for employees in employees_by_position.values()
            for employee in employees
        })
        entries = services_schedule.get_schedule_entries(
            connection,
            dates=week_dates,
            employee_id=employee_scope,
            organization_id=access_context["membership"]["organization_id"] if access_context else None,
            department_ids=None if employee_scope is not None else services_memberships.get_allowed_department_ids(cursor, access_context),
        )
        day_status_map = services_day_status.get_employee_day_status_map(connection, employee_ids, week_dates) if employee_ids else {}
        output = excel_export.build_all_schedule_export_workbook(
            positions=positions,
            week_start_date=week_start_date,
            week_dates=week_dates,
            employees_by_position=employees_by_position,
            entries=entries,
            day_status_map=day_status_map,
            lang=lang,
        )
        filename = f"schedule_all_{week_start_date}.xlsx"
        user_id, organization_id = services_licensing.audit_context_from_user(current_user)
        services_audit.write_auth_audit_event_record(
            "schedule_exported",
            user_id=user_id,
            organization_id=organization_id,
            metadata={
                "format": "excel",
                "scope": "all",
                "week_start_date": week_start_date,
                "lang": lang,
                "filename": filename,
            },
        )
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        connection.close()


@router.get("/api/schedule/export-word", tags=["Schedule"])
def export_schedule_word(
    week_start_date: str,
    position_id: int,
    lang: str = "en",
    access_context: dict | None = Depends(services_access.require_schedule_view_if_auth_initialized),
    current_user: dict | None = Depends(services_authentication.get_optional_current_user),
):
    connection = database.get_connection()
    try:
        if lang not in {"en", "ru", "he"}:
            lang = "en"
        week_dates = schedule_time.build_week_dates(week_start_date)
        cursor = connection.cursor()
        services_memberships.ensure_department_access_for_position(cursor, access_context, position_id)
        position_row = services_common.fetch_one_or_404(
            cursor,
            """
            SELECT p.*, d.public_id AS department_public_id, d.name AS department_name
            FROM positions p
            LEFT JOIN departments d ON d.id = p.department_id
            WHERE p.id = ?
              AND (? IS NULL OR p.organization_id = ?)
            """,
            (
                position_id,
                access_context["membership"]["organization_id"] if access_context else None,
                access_context["membership"]["organization_id"] if access_context else None,
            ),
            "Position not found",
        )
        position = row_serializers.row_to_position_dict(position_row)
        employee_scope = services_memberships.employee_scope_from_access(access_context)
        employees = [
            employee for employee in scheduling_data.load_position_employees(connection, position_id)
            if employee_scope is None or employee["id"] == employee_scope
        ]
        employee_ids = {employee["id"] for employee in employees}
        entries = [
            entry
            for entry in services_schedule.get_schedule_entries(
                connection,
                dates=week_dates,
                employee_id=employee_scope,
                organization_id=access_context["membership"]["organization_id"] if access_context else None,
            )
            if entry["employee_id"] in employee_ids
        ]
        day_status_map = services_day_status.get_employee_day_status_map(connection, [employee["id"] for employee in employees], week_dates)
        output = word_export.build_schedule_export_document(
            position=position,
            week_start_date=week_start_date,
            week_dates=week_dates,
            employees=employees,
            entries=entries,
            day_status_map=day_status_map,
            lang=lang,
        )
        safe_position_name = position["name"].replace(" ", "_")
        filename = f"schedule_{safe_position_name}_{week_start_date}.docx"
        user_id, organization_id = services_licensing.audit_context_from_user(current_user)
        services_audit.write_auth_audit_event_record(
            "schedule_exported",
            user_id=user_id,
            organization_id=organization_id,
            metadata={
                "format": "word",
                "scope": "position",
                "week_start_date": week_start_date,
                "position_id": position_id,
                "lang": lang,
                "filename": filename,
            },
        )
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        connection.close()


@router.get("/api/schedule/export-word-all", tags=["Schedule"])
def export_all_schedules_word(
    week_start_date: str,
    lang: str = "en",
    access_context: dict | None = Depends(services_access.require_schedule_view_if_auth_initialized),
    current_user: dict | None = Depends(services_authentication.get_optional_current_user),
):
    connection = database.get_connection()
    try:
        if lang not in {"en", "ru", "he"}:
            lang = "en"
        week_dates = schedule_time.build_week_dates(week_start_date)
        cursor = connection.cursor()
        employee_scope = services_memberships.employee_scope_from_access(access_context)
        if employee_scope is not None:
            cursor.execute(
                """
                SELECT p.*, d.public_id AS department_public_id, d.name AS department_name,
                       ep.is_primary, ep.priority_score, ep.is_fallback_only
                FROM positions p
                LEFT JOIN departments d ON d.id = p.department_id
                JOIN employee_positions ep ON ep.position_id = p.id
                WHERE ep.employee_id = ?
                ORDER BY d.display_order, d.id, ep.is_primary DESC, ep.is_fallback_only ASC, ep.priority_score DESC, p.id
                """,
                (employee_scope,),
            )
        else:
            conditions = []
            params: list = []
            if access_context:
                conditions.append("p.organization_id = ?")
                params.append(access_context["membership"]["organization_id"])
            services_memberships.append_department_access_condition(cursor, access_context, conditions, params)
            where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            cursor.execute(
                f"""
                SELECT p.*, d.public_id AS department_public_id, d.name AS department_name
                FROM positions p
                LEFT JOIN departments d ON d.id = p.department_id
                {where_sql}
                ORDER BY d.display_order, d.id, p.id
                """,
                params,
            )
        positions = [row_serializers.row_to_position_dict(row) for row in cursor.fetchall()]
        employees_by_position = {
            position["id"]: [
                employee for employee in scheduling_data.load_position_employees(connection, position["id"])
                if employee_scope is None or employee["id"] == employee_scope
            ]
            for position in positions
        }
        employee_ids = sorted({
            employee["id"]
            for employees in employees_by_position.values()
            for employee in employees
        })
        entries = services_schedule.get_schedule_entries(
            connection,
            dates=week_dates,
            employee_id=employee_scope,
            organization_id=access_context["membership"]["organization_id"] if access_context else None,
            department_ids=None if employee_scope is not None else services_memberships.get_allowed_department_ids(cursor, access_context),
        )
        day_status_map = services_day_status.get_employee_day_status_map(connection, employee_ids, week_dates) if employee_ids else {}
        output = word_export.build_all_schedule_export_document(
            positions=positions,
            week_start_date=week_start_date,
            week_dates=week_dates,
            employees_by_position=employees_by_position,
            entries=entries,
            day_status_map=day_status_map,
            lang=lang,
        )
        filename = f"schedule_all_{week_start_date}.docx"
        user_id, organization_id = services_licensing.audit_context_from_user(current_user)
        services_audit.write_auth_audit_event_record(
            "schedule_exported",
            user_id=user_id,
            organization_id=organization_id,
            metadata={
                "format": "word",
                "scope": "all",
                "week_start_date": week_start_date,
                "lang": lang,
                "filename": filename,
            },
        )
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        connection.close()
