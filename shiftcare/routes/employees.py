"""Routes: employees for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from schemas import EmployeeCreate
from schemas import EmployeePositionCreate
from shiftcare.services import access as services_access
from shiftcare.services import backups as services_backups
from shiftcare.services import common as services_common
from shiftcare.services import licensing as services_licensing
from shiftcare.services import memberships as services_memberships
import database
import row_serializers
import sqlite3

router = APIRouter()


@router.get("/api/employees", tags=["Employees"])
def get_employees(
    position_id: int | None = None,
    access_context: dict | None = Depends(services_access.require_preference_access_if_auth_initialized),
):
    organization_filter = access_context["membership"]["organization_id"] if access_context else None
    employee_filter = None
    if access_context and access_context["scope"] == "own":
        employee_filter = access_context["membership"]["employee_id"]
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        if employee_filter and position_id is not None:
            services_memberships.require_employee_position_scope(cursor, int(employee_filter), position_id)
            cursor.execute(
                """
                SELECT DISTINCT e.*
                FROM employees e
                JOIN employee_positions ep ON ep.employee_id = e.id
                WHERE ep.position_id = ?
                ORDER BY e.id
                """,
                (position_id,),
            )
        elif employee_filter:
            cursor.execute("SELECT * FROM employees WHERE id = ? ORDER BY id", (employee_filter,))
        elif organization_filter and position_id is not None:
            services_memberships.ensure_department_access_for_position(cursor, access_context, position_id)
            cursor.execute(
                """
                SELECT DISTINCT e.*
                FROM employees e
                JOIN employee_positions ep ON ep.employee_id = e.id
                WHERE e.organization_id = ? AND ep.position_id = ?
                ORDER BY e.id
                """,
                (organization_filter, position_id),
            )
        elif organization_filter:
            allowed_department_ids = services_memberships.get_allowed_department_ids(cursor, access_context)
            if allowed_department_ids is None:
                cursor.execute("SELECT * FROM employees WHERE organization_id = ? ORDER BY id", (organization_filter,))
            elif not allowed_department_ids:
                cursor.execute("SELECT * FROM employees WHERE 1 = 0")
            else:
                placeholders = ",".join(["?"] * len(allowed_department_ids))
                cursor.execute(
                    f"""
                    SELECT DISTINCT e.*
                    FROM employees e
                    JOIN employee_positions ep ON ep.employee_id = e.id
                    JOIN positions p ON p.id = ep.position_id
                    WHERE e.organization_id = ?
                      AND p.department_id IN ({placeholders})
                    ORDER BY e.id
                    """,
                    (organization_filter, *sorted(allowed_department_ids)),
                )
        elif position_id is not None:
            cursor.execute(
                """
                SELECT DISTINCT e.*
                FROM employees e
                JOIN employee_positions ep ON ep.employee_id = e.id
                WHERE ep.position_id = ?
                ORDER BY e.id
                """,
                (position_id,),
            )
        else:
            cursor.execute("SELECT * FROM employees ORDER BY id")
        return [row_serializers.row_to_employee_dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@router.post("/api/employees", tags=["Employees"])
def add_employee(employee: EmployeeCreate, _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized)):
    organization_id = _access["membership"]["organization_id"] if _access else 1
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        services_licensing.require_license_capability(cursor, "can_add_employee", organization_id)
        cursor.execute(
            """
            INSERT INTO employees (
                organization_id, id_card, full_name, sex, min_shifts_per_week, target_shifts_per_week, max_shifts_per_week,
                can_work_night, can_work_weekends, can_work_evenings_after_night, can_work_mornings_and_evenings
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                employee.id_card,
                employee.full_name,
                employee.sex,
                employee.min_shifts_per_week,
                employee.target_shifts_per_week,
                employee.max_shifts_per_week,
                int(employee.can_work_night),
                int(employee.can_work_weekends),
                int(employee.can_work_evenings_after_night),
                int(employee.can_work_mornings_and_evenings),
            ),
        )
        connection.commit()
        return {"message": "Employee added successfully", "employee": {"id": cursor.lastrowid, **employee.model_dump()}}
    finally:
        connection.close()


@router.put("/api/employees/{employee_id}", tags=["Employees"])
def update_employee(
    employee_id: int,
    employee: EmployeeCreate,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    organization_id = _access["membership"]["organization_id"] if _access else None
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        if organization_id:
            services_common.fetch_one_or_404(
                cursor,
                "SELECT id FROM employees WHERE id = ? AND organization_id = ?",
                (employee_id, organization_id),
                "Employee not found",
            )
        else:
            services_common.fetch_one_or_404(cursor, "SELECT id FROM employees WHERE id = ?", (employee_id,), "Employee not found")
        cursor.execute(
            """
            UPDATE employees
            SET id_card = ?, full_name = ?, sex = ?, min_shifts_per_week = ?, target_shifts_per_week = ?,
                max_shifts_per_week = ?, can_work_night = ?, can_work_weekends = ?,
                can_work_evenings_after_night = ?, can_work_mornings_and_evenings = ?
            WHERE id = ?
            """,
            (
                employee.id_card,
                employee.full_name,
                employee.sex,
                employee.min_shifts_per_week,
                employee.target_shifts_per_week,
                employee.max_shifts_per_week,
                int(employee.can_work_night),
                int(employee.can_work_weekends),
                int(employee.can_work_evenings_after_night),
                int(employee.can_work_mornings_and_evenings),
                employee_id,
            ),
        )
        connection.commit()
        return {"message": "Employee updated successfully", "employee": {"id": employee_id, **employee.model_dump()}}
    finally:
        connection.close()


@router.delete("/api/employees/{employee_id}", tags=["Employees"])
def delete_employee(employee_id: int, _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized)):
    organization_id = _access["membership"]["organization_id"] if _access else None
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        if organization_id:
            services_common.fetch_one_or_404(
                cursor,
                "SELECT id FROM employees WHERE id = ? AND organization_id = ?",
                (employee_id, organization_id),
                "Employee not found",
            )
        else:
            services_common.fetch_one_or_404(cursor, "SELECT id FROM employees WHERE id = ?", (employee_id,), "Employee not found")
        backup_name = services_backups.create_recovery_backup("delete_employee")
        cursor.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        connection.commit()
        return {"message": "Employee deleted successfully", "backup_name": backup_name}
    finally:
        connection.close()


@router.get("/api/employees/{employee_id}/delete-impact", tags=["Employees"])
def get_employee_delete_impact(employee_id: int, _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized)):
    organization_id = _access["membership"]["organization_id"] if _access else None
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        if organization_id:
            employee_row = services_common.fetch_one_or_404(
                cursor,
                "SELECT id, full_name FROM employees WHERE id = ? AND organization_id = ?",
                (employee_id, organization_id),
                "Employee not found",
            )
        else:
            employee_row = services_common.fetch_one_or_404(
                cursor,
                "SELECT id, full_name FROM employees WHERE id = ?",
                (employee_id,),
                "Employee not found",
            )
        return {
            "employee_id": employee_row["id"],
            "employee_name": employee_row["full_name"],
            "assignments": services_common.fetch_count(cursor, "SELECT COUNT(*) FROM employee_positions WHERE employee_id = ?", (employee_id,)),
            "schedule_entries": services_common.fetch_count(cursor, "SELECT COUNT(*) FROM schedule_entries WHERE employee_id = ?", (employee_id,)),
            "general_preferences": services_common.fetch_count(
                cursor,
                "SELECT COUNT(*) FROM employee_preferences WHERE employee_id = ?",
                (employee_id,),
            ),
            "weekly_preferences": services_common.fetch_count(
                cursor,
                "SELECT COUNT(*) FROM employee_week_preferences WHERE employee_id = ?",
                (employee_id,),
            ),
            "recurring_preferences": services_common.fetch_count(
                cursor,
                "SELECT COUNT(*) FROM employee_recurring_preferences WHERE employee_id = ?",
                (employee_id,),
            ),
            "day_statuses": services_common.fetch_count(
                cursor,
                "SELECT COUNT(*) FROM employee_day_statuses WHERE employee_id = ?",
                (employee_id,),
            ),
        }
    finally:
        connection.close()


@router.get("/api/employee-positions", tags=["Assignments"])
def get_employee_positions(
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
            where_sql = "WHERE ep.position_id = ?"
            params = (position_id,)
        elif employee_id is not None:
            where_sql = "WHERE ep.employee_id = ?"
            params = (employee_id,)
        elif position_id is not None:
            services_memberships.ensure_department_access_for_position(cursor, access_context, position_id)
            where_sql = "WHERE ep.position_id = ?"
            params = (position_id,)
        else:
            conditions = []
            params_list: list = []
            services_memberships.append_department_access_condition(cursor, access_context, conditions, params_list)
            if conditions:
                where_sql = f"WHERE {' AND '.join(conditions)}"
                params = tuple(params_list)
        cursor.execute(
            f"""
            SELECT ep.*, e.full_name AS employee_name, p.name AS position_name,
                   p.department_id, d.name AS department_name
            FROM employee_positions ep
            JOIN employees e ON e.id = ep.employee_id
            JOIN positions p ON p.id = ep.position_id
            LEFT JOIN departments d ON d.id = p.department_id
            {where_sql}
            ORDER BY ep.employee_id, d.display_order, d.id, ep.is_primary DESC, ep.is_fallback_only ASC, ep.priority_score DESC, ep.position_id
            """,
            params,
        )
        items = [dict(row) for row in cursor.fetchall()]
        for item in items:
            item["is_primary"] = bool(item["is_primary"])
            item["is_fallback_only"] = bool(item["is_fallback_only"])
        return items
    finally:
        connection.close()


@router.post("/api/employee-positions", tags=["Assignments"])
def assign_employee_to_position(
    assignment: EmployeePositionCreate,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        organization_id = _access["membership"]["organization_id"] if _access else None
        if organization_id:
            services_common.fetch_one_or_404(
                cursor,
                "SELECT id FROM employees WHERE id = ? AND organization_id = ?",
                (assignment.employee_id, organization_id),
                "Employee not found",
            )
            services_common.fetch_one_or_404(
                cursor,
                "SELECT id FROM positions WHERE id = ? AND organization_id = ?",
                (assignment.position_id, organization_id),
                "Position not found",
            )
        else:
            services_common.fetch_one_or_404(cursor, "SELECT id FROM employees WHERE id = ?", (assignment.employee_id,), "Employee not found")
            services_common.fetch_one_or_404(cursor, "SELECT id FROM positions WHERE id = ?", (assignment.position_id,), "Position not found")
        services_memberships.ensure_department_access_for_position(cursor, _access, assignment.position_id)
        try:
            cursor.execute(
                """
                INSERT INTO employee_positions (employee_id, position_id, is_primary, priority_score, is_fallback_only)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    assignment.employee_id,
                    assignment.position_id,
                    int(assignment.is_primary),
                    assignment.priority_score,
                    int(assignment.is_fallback_only),
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Employee is already assigned to this position")
        connection.commit()
        return {"message": "Employee assigned to position successfully", "assignment": assignment.model_dump()}
    finally:
        connection.close()


@router.put("/api/employee-positions", tags=["Assignments"])
def update_employee_position(
    assignment: EmployeePositionCreate,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        organization_id = _access["membership"]["organization_id"] if _access else None
        if organization_id:
            services_common.fetch_one_or_404(
                cursor,
                "SELECT id FROM employees WHERE id = ? AND organization_id = ?",
                (assignment.employee_id, organization_id),
                "Employee not found",
            )
            services_common.fetch_one_or_404(
                cursor,
                "SELECT id FROM positions WHERE id = ? AND organization_id = ?",
                (assignment.position_id, organization_id),
                "Position not found",
            )
        else:
            services_common.fetch_one_or_404(cursor, "SELECT id FROM employees WHERE id = ?", (assignment.employee_id,), "Employee not found")
            services_common.fetch_one_or_404(cursor, "SELECT id FROM positions WHERE id = ?", (assignment.position_id,), "Position not found")
        services_memberships.ensure_department_access_for_position(cursor, _access, assignment.position_id)
        cursor.execute(
            """
            UPDATE employee_positions
            SET is_primary = ?, priority_score = ?, is_fallback_only = ?
            WHERE employee_id = ? AND position_id = ?
            """,
            (
                int(assignment.is_primary),
                assignment.priority_score,
                int(assignment.is_fallback_only),
                assignment.employee_id,
                assignment.position_id,
            ),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Assignment not found")
        connection.commit()
        return {"message": "Employee assignment updated successfully", "assignment": assignment.model_dump()}
    finally:
        connection.close()


@router.delete("/api/employee-positions", tags=["Assignments"])
def delete_employee_position(
    employee_id: int,
    position_id: int,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        services_memberships.ensure_department_access_for_position(cursor, _access, position_id)
        backup_name = services_backups.create_recovery_backup("delete_assignment")
        cursor.execute("DELETE FROM employee_positions WHERE employee_id = ? AND position_id = ?", (employee_id, position_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Assignment not found")
        connection.commit()
        return {"message": "Employee assignment deleted successfully", "backup_name": backup_name}
    finally:
        connection.close()


@router.get("/api/employee-positions/delete-impact", tags=["Assignments"])
def get_employee_position_delete_impact(
    employee_id: int,
    position_id: int,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        assignment_row = services_common.fetch_one_or_404(
            cursor,
            """
            SELECT ep.employee_id, ep.position_id, e.full_name AS employee_name,
                   p.name AS position_name, p.organization_id, d.name AS department_name
            FROM employee_positions ep
            JOIN employees e ON e.id = ep.employee_id
            JOIN positions p ON p.id = ep.position_id
            LEFT JOIN departments d ON d.id = p.department_id
            WHERE ep.employee_id = ? AND ep.position_id = ?
            """,
            (employee_id, position_id),
            "Assignment not found",
        )
        if _access and int(assignment_row["organization_id"]) != int(_access["membership"]["organization_id"]):
            raise HTTPException(status_code=404, detail="Assignment not found")
        services_memberships.ensure_department_access_for_position(cursor, _access, position_id)
        return {
            "employee_id": assignment_row["employee_id"],
            "position_id": assignment_row["position_id"],
            "employee_name": assignment_row["employee_name"],
            "position_name": assignment_row["position_name"],
            "department_name": assignment_row["department_name"],
            "schedule_entries": services_common.fetch_count(
                cursor,
                "SELECT COUNT(*) FROM schedule_entries WHERE employee_id = ? AND position_id = ?",
                (employee_id, position_id),
            ),
        }
    finally:
        connection.close()
