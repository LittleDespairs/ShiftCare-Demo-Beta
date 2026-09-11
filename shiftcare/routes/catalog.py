"""Routes: catalog for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from schemas import DepartmentCreate
from schemas import PositionCreate
from shiftcare.services import access as services_access
from shiftcare.services import backups as services_backups
from shiftcare.services import bundle_rows as services_bundle_rows
from shiftcare.services import common as services_common
from shiftcare.services import memberships as services_memberships
import database
import row_serializers
import sqlite3

router = APIRouter()


@router.get("/api/departments", tags=["Departments"])
def get_departments(access_context: dict | None = Depends(services_access.require_schedule_view_if_auth_initialized)):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        organization_id = access_context["membership"]["organization_id"] if access_context else None
        if organization_id is not None:
            conditions = ["organization_id = ?"]
            params: list = [organization_id]
            services_memberships.append_department_access_condition(cursor, access_context, conditions, params, "id")
            cursor.execute(
                f"""
                SELECT *
                FROM departments
                WHERE {" AND ".join(conditions)}
                ORDER BY display_order, id
                """,
                params,
            )
        else:
            cursor.execute("SELECT * FROM departments ORDER BY organization_id, display_order, id")
        return [row_serializers.row_to_department_dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@router.post("/api/departments", tags=["Departments"])
def add_department(
    department: DepartmentCreate,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    organization_id = _access["membership"]["organization_id"] if _access else 1
    now = services_common.current_utc_timestamp()
    user_id = _access["user"]["id"] if _access else None
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        if services_memberships.get_allowed_department_ids(cursor, _access) is not None:
            raise HTTPException(status_code=403, detail="Only users with access to all departments can create departments")
        try:
            cursor.execute(
                """
                INSERT INTO departments (
                    organization_id, name, description, display_order, is_active, created_at, updated_at, updated_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    organization_id,
                    department.name,
                    department.description,
                    department.display_order,
                    int(department.is_active),
                    now,
                    now,
                    user_id,
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Department already exists")
        connection.commit()
        return {"message": "Department added successfully", "department": {"id": cursor.lastrowid, **department.model_dump()}}
    finally:
        connection.close()


@router.put("/api/departments/{department_id}", tags=["Departments"])
def update_department(
    department_id: int,
    department: DepartmentCreate,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    organization_id = _access["membership"]["organization_id"] if _access else 1
    now = services_common.current_utc_timestamp()
    user_id = _access["user"]["id"] if _access else None
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        services_common.fetch_one_or_404(
            cursor,
            "SELECT id FROM departments WHERE id = ? AND organization_id = ?",
            (department_id, organization_id),
            "Department not found",
        )
        services_memberships.ensure_department_access_for_department(cursor, _access, department_id)
        try:
            cursor.execute(
                """
                UPDATE departments
                SET name = ?, description = ?, display_order = ?, is_active = ?, updated_at = ?, updated_by = ?
                WHERE id = ? AND organization_id = ?
                """,
                (
                    department.name,
                    department.description,
                    department.display_order,
                    int(department.is_active),
                    now,
                    user_id,
                    department_id,
                    organization_id,
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Department already exists")
        connection.commit()
        return {"message": "Department updated successfully", "department": {"id": department_id, **department.model_dump()}}
    finally:
        connection.close()


@router.delete("/api/departments/{department_id}", tags=["Departments"])
def delete_department(
    department_id: int,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    organization_id = _access["membership"]["organization_id"] if _access else 1
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        department_row = services_common.fetch_one_or_404(
            cursor,
            "SELECT id, name FROM departments WHERE id = ? AND organization_id = ?",
            (department_id, organization_id),
            "Department not found",
        )
        services_memberships.ensure_department_access_for_department(cursor, _access, department_id)
        department_count = services_common.fetch_count(
            cursor,
            "SELECT COUNT(*) FROM departments WHERE organization_id = ?",
            (organization_id,),
        )
        if department_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last department")
        linked_position_count = services_common.fetch_count(
            cursor,
            "SELECT COUNT(*) FROM positions WHERE department_id = ? AND organization_id = ?",
            (department_id, organization_id),
        )
        if linked_position_count:
            raise HTTPException(status_code=400, detail="Cannot delete department with positions")
        backup_name = services_backups.create_recovery_backup("delete_department")
        cursor.execute(
            "DELETE FROM departments WHERE id = ? AND organization_id = ?",
            (department_row["id"], organization_id),
        )
        connection.commit()
        return {"message": "Department deleted successfully", "backup_name": backup_name}
    finally:
        connection.close()


@router.get("/api/departments/{department_id}/delete-impact", tags=["Departments"])
def get_department_delete_impact(
    department_id: int,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    organization_id = _access["membership"]["organization_id"] if _access else 1
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        department_row = services_common.fetch_one_or_404(
            cursor,
            "SELECT id, name FROM departments WHERE id = ? AND organization_id = ?",
            (department_id, organization_id),
            "Department not found",
        )
        services_memberships.ensure_department_access_for_department(cursor, _access, department_id)
        return {
            "department_id": department_row["id"],
            "department_name": department_row["name"],
            "positions": services_common.fetch_count(
                cursor,
                "SELECT COUNT(*) FROM positions WHERE department_id = ? AND organization_id = ?",
                (department_id, organization_id),
            ),
            "is_last_department": services_common.fetch_count(
                cursor,
                "SELECT COUNT(*) FROM departments WHERE organization_id = ?",
                (organization_id,),
            ) <= 1,
        }
    finally:
        connection.close()


@router.get("/api/positions", tags=["Positions"])
def get_positions(access_context: dict | None = Depends(services_access.require_schedule_view_if_auth_initialized)):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        employee_id = services_memberships.employee_scope_from_access(access_context)
        organization_id = access_context["membership"]["organization_id"] if access_context else None
        if employee_id is not None:
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
                (employee_id,),
            )
        elif organization_id is not None:
            conditions = ["p.organization_id = ?"]
            params: list = [organization_id]
            services_memberships.append_department_access_condition(cursor, access_context, conditions, params)
            cursor.execute(
                f"""
                SELECT p.*, d.public_id AS department_public_id, d.name AS department_name
                FROM positions p
                LEFT JOIN departments d ON d.id = p.department_id
                WHERE {" AND ".join(conditions)}
                ORDER BY d.display_order, d.id, p.id
                """,
                params,
            )
        else:
            cursor.execute(
                """
                SELECT p.*, d.public_id AS department_public_id, d.name AS department_name
                FROM positions p
                LEFT JOIN departments d ON d.id = p.department_id
                ORDER BY p.organization_id, d.display_order, d.id, p.id
                """
            )
        return [row_serializers.row_to_position_dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@router.post("/api/positions", tags=["Positions"])
def add_position(position: PositionCreate, _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized)):
    organization_id = _access["membership"]["organization_id"] if _access else 1
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        department_id = position.department_id or services_bundle_rows.get_default_department_id(cursor, organization_id)
        services_common.fetch_one_or_404(
            cursor,
            "SELECT id FROM departments WHERE id = ? AND organization_id = ?",
            (department_id, organization_id),
            "Department not found",
        )
        services_memberships.ensure_department_access_for_department(cursor, _access, department_id)
        try:
            cursor.execute(
                """
                INSERT INTO positions (
                    organization_id, department_id, name, color, requires_continuous_coverage, minimum_staff_presence,
                    allow_same_day_other_positions,
                    max_consecutive_nights, emergency_max_consecutive_nights,
                    max_consecutive_split_days, emergency_max_consecutive_split_days
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    organization_id,
                    department_id,
                    position.name,
                    position.color,
                    int(position.requires_continuous_coverage),
                    position.minimum_staff_presence,
                    int(position.allow_same_day_other_positions),
                    position.max_consecutive_nights,
                    position.emergency_max_consecutive_nights,
                    position.max_consecutive_split_days,
                    position.emergency_max_consecutive_split_days,
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Position already exists in this department")
        connection.commit()
        return {
            "message": "Position added successfully",
            "position": {"id": cursor.lastrowid, **position.model_dump(), "department_id": department_id},
        }
    finally:
        connection.close()


@router.put("/api/positions/{position_id}", tags=["Positions"])
def update_position(
    position_id: int,
    position: PositionCreate,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    organization_id = _access["membership"]["organization_id"] if _access else 1
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        services_memberships.ensure_department_access_for_position(cursor, _access, position_id)
        position_row = services_common.fetch_one_or_404(
            cursor,
            "SELECT id, organization_id FROM positions WHERE id = ?",
            (position_id,),
            "Position not found",
        )
        if _access and int(position_row["organization_id"]) != int(organization_id):
            raise HTTPException(status_code=404, detail="Position not found")
        department_id = position.department_id or services_bundle_rows.get_default_department_id(cursor, organization_id)
        services_common.fetch_one_or_404(
            cursor,
            "SELECT id FROM departments WHERE id = ? AND organization_id = ?",
            (department_id, organization_id),
            "Department not found",
        )
        services_memberships.ensure_department_access_for_position(cursor, _access, position_id)
        services_memberships.ensure_department_access_for_department(cursor, _access, department_id)
        try:
            cursor.execute(
                """
                UPDATE positions
                SET department_id = ?, name = ?, color = ?, requires_continuous_coverage = ?, minimum_staff_presence = ?,
                    allow_same_day_other_positions = ?,
                    max_consecutive_nights = ?, emergency_max_consecutive_nights = ?,
                    max_consecutive_split_days = ?, emergency_max_consecutive_split_days = ?
                WHERE id = ?
                """,
                (
                    department_id,
                    position.name,
                    position.color,
                    int(position.requires_continuous_coverage),
                    position.minimum_staff_presence,
                    int(position.allow_same_day_other_positions),
                    position.max_consecutive_nights,
                    position.emergency_max_consecutive_nights,
                    position.max_consecutive_split_days,
                    position.emergency_max_consecutive_split_days,
                    position_id,
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Position already exists in this department")
        connection.commit()
        return {
            "message": "Position updated successfully",
            "position": {"id": position_id, **position.model_dump(), "department_id": department_id},
        }
    finally:
        connection.close()


@router.delete("/api/positions/{position_id}", tags=["Positions"])
def delete_position(position_id: int, _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized)):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        position_row = services_common.fetch_one_or_404(
            cursor,
            "SELECT id, organization_id FROM positions WHERE id = ?",
            (position_id,),
            "Position not found",
        )
        if _access and int(position_row["organization_id"]) != int(_access["membership"]["organization_id"]):
            raise HTTPException(status_code=404, detail="Position not found")
        services_memberships.ensure_department_access_for_position(cursor, _access, position_id)
        backup_name = services_backups.create_recovery_backup("delete_position")
        cursor.execute("DELETE FROM positions WHERE id = ?", (position_id,))
        connection.commit()
        return {"message": "Position deleted successfully", "backup_name": backup_name}
    finally:
        connection.close()


@router.get("/api/positions/{position_id}/delete-impact", tags=["Positions"])
def get_position_delete_impact(
    position_id: int,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        position_row = services_common.fetch_one_or_404(
            cursor,
            """
            SELECT p.id, p.name, p.organization_id, d.name AS department_name
            FROM positions p
            LEFT JOIN departments d ON d.id = p.department_id
            WHERE p.id = ?
            """,
            (position_id,),
            "Position not found",
        )
        if _access and int(position_row["organization_id"]) != int(_access["membership"]["organization_id"]):
            raise HTTPException(status_code=404, detail="Position not found")
        services_memberships.ensure_department_access_for_position(cursor, _access, position_id)
        return {
            "position_id": position_row["id"],
            "position_name": position_row["name"],
            "department_name": position_row["department_name"],
            "assignments": services_common.fetch_count(cursor, "SELECT COUNT(*) FROM employee_positions WHERE position_id = ?", (position_id,)),
            "schedule_entries": services_common.fetch_count(cursor, "SELECT COUNT(*) FROM schedule_entries WHERE position_id = ?", (position_id,)),
            "shift_requirements": services_common.fetch_count(cursor, "SELECT COUNT(*) FROM shift_requirements WHERE position_id = ?", (position_id,)),
            "coverage_requirements": services_common.fetch_count(
                cursor,
                "SELECT COUNT(*) FROM coverage_requirements WHERE position_id = ?",
                (position_id,),
            ),
        }
    finally:
        connection.close()
