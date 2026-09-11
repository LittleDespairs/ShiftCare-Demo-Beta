"""Routes: shifts for ShiftCare."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from schemas import CoverageRequirementCreate
from schemas import ShiftRequirementCreate
from schemas import ShiftTemplateCreate
from shiftcare.services import access as services_access
from shiftcare.services import backups as services_backups
from shiftcare.services import common as services_common
from shiftcare.services import memberships as services_memberships
import database
import row_serializers
import schedule_time
import sqlite3

router = APIRouter()


@router.get("/api/shift-templates", tags=["Shift Templates"])
def get_shift_templates(
    active_only: bool = False,
    position_id: int | None = None,
    access_context: dict | None = Depends(services_access.require_schedule_view_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        employee_id = services_memberships.employee_scope_from_access(access_context)
        if employee_id is not None:
            if position_id is not None:
                services_memberships.require_employee_position_scope(cursor, employee_id, position_id)
            else:
                cursor.execute(
                    """
                    SELECT position_id
                    FROM employee_positions
                    WHERE employee_id = ?
                    ORDER BY is_primary DESC, is_fallback_only ASC, priority_score DESC, position_id
                    LIMIT 1
                    """,
                    (employee_id,),
                )
                row = cursor.fetchone()
                position_id = int(row["position_id"]) if row else -1
        base_query = """
            SELECT st.*, p.name AS position_name, p.department_id, d.name AS department_name
            FROM shift_templates st
            LEFT JOIN positions p ON p.id = st.position_id
            LEFT JOIN departments d ON d.id = p.department_id
        """
        conditions = []
        params: list[int] = []
        if access_context:
            conditions.append("st.organization_id = ?")
            params.append(access_context["membership"]["organization_id"])
        if active_only:
            conditions.append("st.is_active = 1")
        if position_id is not None:
            services_memberships.ensure_department_access_for_position(cursor, access_context, position_id)
            conditions.append("st.position_id = ?")
            params.append(position_id)
        elif employee_id is None:
            services_memberships.append_department_access_condition(cursor, access_context, conditions, params)
        where_sql = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"{base_query}{where_sql} ORDER BY d.display_order, COALESCE(st.position_id, 0), st.category, st.start_time, st.end_time"
        cursor.execute(query, params)
        return [row_serializers.row_to_shift_template_dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@router.post("/api/shift-templates", tags=["Shift Templates"])
def add_shift_template(
    template: ShiftTemplateCreate,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    schedule_time.parse_time_string(template.start_time)
    schedule_time.parse_time_string(template.end_time)
    organization_id = _access["membership"]["organization_id"] if _access else 1
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        services_common.fetch_one_or_404(
            cursor,
            "SELECT id FROM positions WHERE id = ? AND organization_id = ?",
            (template.position_id, organization_id),
            "Position not found",
        )
        services_memberships.ensure_department_access_for_position(cursor, _access, template.position_id)
        try:
            cursor.execute(
                """
                INSERT INTO shift_templates (
                    organization_id, position_id, name, category, start_time, end_time, is_overnight, is_active, is_split_only
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    organization_id,
                    template.position_id,
                    template.name,
                    template.category,
                    template.start_time,
                    template.end_time,
                    int(template.is_overnight),
                    int(template.is_active),
                    int(template.is_split_only),
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Shift template already exists for this position")
        connection.commit()
        return {"message": "Shift template added successfully", "shift_template": {"id": cursor.lastrowid, **template.model_dump()}}
    finally:
        connection.close()


@router.put("/api/shift-templates/{template_id}", tags=["Shift Templates"])
def update_shift_template(
    template_id: int,
    template: ShiftTemplateCreate,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    schedule_time.parse_time_string(template.start_time)
    schedule_time.parse_time_string(template.end_time)
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        template_row = services_common.fetch_one_or_404(
            cursor,
            """
            SELECT st.id, st.position_id, st.organization_id
            FROM shift_templates st
            WHERE st.id = ?
            """,
            (template_id,),
            "Shift template not found",
        )
        if _access and int(template_row["organization_id"]) != int(_access["membership"]["organization_id"]):
            raise HTTPException(status_code=404, detail="Shift template not found")
        services_memberships.ensure_department_access_for_position(cursor, _access, template_row["position_id"])
        if _access:
            services_common.fetch_one_or_404(
                cursor,
                "SELECT id FROM positions WHERE id = ? AND organization_id = ?",
                (template.position_id, _access["membership"]["organization_id"]),
                "Position not found",
            )
        else:
            services_common.fetch_one_or_404(cursor, "SELECT id FROM positions WHERE id = ?", (template.position_id,), "Position not found")
        services_memberships.ensure_department_access_for_position(cursor, _access, template.position_id)
        try:
            cursor.execute(
                """
                UPDATE shift_templates
                SET position_id = ?, name = ?, category = ?, start_time = ?, end_time = ?, is_overnight = ?, is_active = ?, is_split_only = ?
                WHERE id = ?
                """,
                (
                    template.position_id,
                    template.name,
                    template.category,
                    template.start_time,
                    template.end_time,
                    int(template.is_overnight),
                    int(template.is_active),
                    int(template.is_split_only),
                    template_id,
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Shift template with this name already exists for this position")
        connection.commit()
        return {"message": "Shift template updated successfully", "shift_template": {"id": template_id, **template.model_dump()}}
    finally:
        connection.close()


@router.delete("/api/shift-templates/{template_id}", tags=["Shift Templates"])
def delete_shift_template(
    template_id: int,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        template_row = services_common.fetch_one_or_404(
            cursor,
            "SELECT position_id, organization_id FROM shift_templates WHERE id = ?",
            (template_id,),
            "Shift template not found",
        )
        if _access and int(template_row["organization_id"]) != int(_access["membership"]["organization_id"]):
            raise HTTPException(status_code=404, detail="Shift template not found")
        services_memberships.ensure_department_access_for_position(cursor, _access, template_row["position_id"])
        backup_name = services_backups.create_recovery_backup("delete_shift_template")
        cursor.execute("DELETE FROM shift_templates WHERE id = ?", (template_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Shift template not found")
        connection.commit()
        return {"message": "Shift template deleted successfully", "backup_name": backup_name}
    except sqlite3.IntegrityError:
        connection.rollback()
        raise HTTPException(status_code=400, detail="Cannot delete shift template because it is used in schedule")
    finally:
        connection.close()


@router.get("/api/shift-templates/{template_id}/delete-impact", tags=["Shift Templates"])
def get_shift_template_delete_impact(
    template_id: int,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        template_row = services_common.fetch_one_or_404(
            cursor,
            """
            SELECT st.id, st.name, st.category, st.position_id,
                   st.organization_id, p.name AS position_name, d.name AS department_name
            FROM shift_templates st
            LEFT JOIN positions p ON p.id = st.position_id
            LEFT JOIN departments d ON d.id = p.department_id
            WHERE st.id = ?
            """,
            (template_id,),
            "Shift template not found",
        )
        if _access and int(template_row["organization_id"]) != int(_access["membership"]["organization_id"]):
            raise HTTPException(status_code=404, detail="Shift template not found")
        services_memberships.ensure_department_access_for_position(cursor, _access, template_row["position_id"])
        return {
            "template_id": template_row["id"],
            "template_name": template_row["name"],
            "category": template_row["category"],
            "position_id": template_row["position_id"],
            "position_name": template_row["position_name"],
            "department_name": template_row["department_name"],
            "schedule_entries": services_common.fetch_count(
                cursor,
                "SELECT COUNT(*) FROM schedule_entries WHERE shift_template_id = ?",
                (template_id,),
            ),
        }
    finally:
        connection.close()


@router.get("/api/shift-requirements", tags=["Requirements"])
def get_shift_requirements(
    position_id: int | None = None,
    access_context: dict | None = Depends(services_access.require_schedule_view_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        employee_id = services_memberships.employee_scope_from_access(access_context)
        if employee_id is not None and position_id is not None:
            services_memberships.require_employee_position_scope(cursor, employee_id, position_id)
        elif position_id is not None:
            services_memberships.ensure_department_access_for_position(cursor, access_context, position_id)
        if position_id is None:
            conditions = []
            params: list = []
            if employee_id is None:
                services_memberships.append_department_access_condition(cursor, access_context, conditions, params)
            if access_context:
                conditions.append("sr.organization_id = ?")
                params.append(access_context["membership"]["organization_id"])
            where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            cursor.execute(
                f"""
            SELECT sr.*, p.name AS position_name, p.department_id, d.name AS department_name
            FROM shift_requirements sr
            JOIN positions p ON p.id = sr.position_id
            LEFT JOIN departments d ON d.id = p.department_id
            {where_sql}
            ORDER BY d.display_order, d.id, sr.position_id, sr.shift_category
                """,
                params,
            )
        else:
            cursor.execute(
                """
                SELECT sr.*, p.name AS position_name, p.department_id, d.name AS department_name
                FROM shift_requirements sr
                JOIN positions p ON p.id = sr.position_id
                LEFT JOIN departments d ON d.id = p.department_id
                WHERE sr.position_id = ?
                  AND (? IS NULL OR sr.organization_id = ?)
                ORDER BY sr.shift_category
                """,
                (position_id, access_context["membership"]["organization_id"] if access_context else None, access_context["membership"]["organization_id"] if access_context else None),
            )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@router.post("/api/shift-requirements", tags=["Requirements"])
def save_shift_requirement(
    requirement: ShiftRequirementCreate,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    organization_id = _access["membership"]["organization_id"] if _access else 1
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        services_common.fetch_one_or_404(
            cursor,
            "SELECT id FROM positions WHERE id = ? AND organization_id = ?",
            (requirement.position_id, organization_id),
            "Position not found",
        )
        services_memberships.ensure_department_access_for_position(cursor, _access, requirement.position_id)
        cursor.execute(
            """
            INSERT INTO shift_requirements (
                organization_id, position_id, shift_category, required_total, required_female_min, required_male_min
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(position_id, shift_category)
            DO UPDATE SET required_total = excluded.required_total,
                          required_female_min = excluded.required_female_min,
                          required_male_min = excluded.required_male_min
            """,
            (
                organization_id,
                requirement.position_id,
                requirement.shift_category,
                requirement.required_total,
                requirement.required_female_min,
                requirement.required_male_min,
            ),
        )
        connection.commit()
        return {"message": "Shift requirement saved successfully", "requirement": requirement.model_dump()}
    finally:
        connection.close()


@router.get("/api/coverage-requirements", tags=["Requirements"])
def get_coverage_requirements(
    position_id: int | None = None,
    access_context: dict | None = Depends(services_access.require_schedule_view_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        employee_id = services_memberships.employee_scope_from_access(access_context)
        if employee_id is not None and position_id is not None:
            services_memberships.require_employee_position_scope(cursor, employee_id, position_id)
        elif position_id is not None:
            services_memberships.ensure_department_access_for_position(cursor, access_context, position_id)
        if position_id is None:
            conditions = []
            params: list = []
            if employee_id is None:
                services_memberships.append_department_access_condition(cursor, access_context, conditions, params)
            if access_context:
                conditions.append("cr.organization_id = ?")
                params.append(access_context["membership"]["organization_id"])
            where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            cursor.execute(
                f"""
                SELECT cr.*, p.name AS position_name, p.department_id, d.name AS department_name
                FROM coverage_requirements cr
                JOIN positions p ON p.id = cr.position_id
                LEFT JOIN departments d ON d.id = p.department_id
                {where_sql}
                ORDER BY d.display_order, d.id, cr.position_id, cr.start_time, cr.end_time
                """,
                params,
            )
        else:
            cursor.execute(
                """
                SELECT cr.*, p.name AS position_name, p.department_id, d.name AS department_name
                FROM coverage_requirements cr
                JOIN positions p ON p.id = cr.position_id
                LEFT JOIN departments d ON d.id = p.department_id
                WHERE cr.position_id = ?
                  AND (? IS NULL OR cr.organization_id = ?)
                ORDER BY cr.start_time, cr.end_time
                """,
                (position_id, access_context["membership"]["organization_id"] if access_context else None, access_context["membership"]["organization_id"] if access_context else None),
            )
        return [row_serializers.row_to_coverage_requirement_dict(row) for row in cursor.fetchall()]
    finally:
        connection.close()


@router.post("/api/coverage-requirements", tags=["Requirements"])
def add_coverage_requirement(
    requirement: CoverageRequirementCreate,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    organization_id = _access["membership"]["organization_id"] if _access else 1
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        services_common.fetch_one_or_404(
            cursor,
            "SELECT id FROM positions WHERE id = ? AND organization_id = ?",
            (requirement.position_id, organization_id),
            "Position not found",
        )
        services_memberships.ensure_department_access_for_position(cursor, _access, requirement.position_id)
        cursor.execute(
            """
            INSERT INTO coverage_requirements
                (organization_id, position_id, start_time, end_time, required_total, required_female_min, required_male_min, is_overnight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                requirement.position_id,
                requirement.start_time,
                requirement.end_time,
                requirement.required_total,
                requirement.required_female_min,
                requirement.required_male_min,
                int(requirement.is_overnight),
            ),
        )
        connection.commit()
        return {"message": "Coverage requirement added successfully", "coverage_requirement": {"id": cursor.lastrowid, **requirement.model_dump()}}
    finally:
        connection.close()


@router.put("/api/coverage-requirements/{requirement_id}", tags=["Requirements"])
def update_coverage_requirement(
    requirement_id: int,
    requirement: CoverageRequirementCreate,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        existing_requirement = services_common.fetch_one_or_404(
            cursor,
            "SELECT position_id, organization_id FROM coverage_requirements WHERE id = ?",
            (requirement_id,),
            "Coverage requirement not found",
        )
        if _access and int(existing_requirement["organization_id"]) != int(_access["membership"]["organization_id"]):
            raise HTTPException(status_code=404, detail="Coverage requirement not found")
        services_memberships.ensure_department_access_for_position(cursor, _access, existing_requirement["position_id"])
        organization_id = _access["membership"]["organization_id"] if _access else None
        if organization_id:
            services_common.fetch_one_or_404(
                cursor,
                "SELECT id FROM positions WHERE id = ? AND organization_id = ?",
                (requirement.position_id, organization_id),
                "Position not found",
            )
        else:
            services_common.fetch_one_or_404(cursor, "SELECT id FROM positions WHERE id = ?", (requirement.position_id,), "Position not found")
        services_memberships.ensure_department_access_for_position(cursor, _access, requirement.position_id)
        cursor.execute(
            """
            UPDATE coverage_requirements
            SET position_id = ?, start_time = ?, end_time = ?, required_total = ?, required_female_min = ?, required_male_min = ?, is_overnight = ?
            WHERE id = ?
            """,
            (
                requirement.position_id,
                requirement.start_time,
                requirement.end_time,
                requirement.required_total,
                requirement.required_female_min,
                requirement.required_male_min,
                int(requirement.is_overnight),
                requirement_id,
            ),
        )
        connection.commit()
        return {"message": "Coverage requirement updated successfully", "coverage_requirement": {"id": requirement_id, **requirement.model_dump()}}
    finally:
        connection.close()


@router.delete("/api/coverage-requirements/{requirement_id}", tags=["Requirements"])
def delete_coverage_requirement(
    requirement_id: int,
    _access: dict | None = Depends(services_access.require_setup_edit_if_auth_initialized),
):
    connection = database.get_connection()
    try:
        cursor = connection.cursor()
        requirement_row = services_common.fetch_one_or_404(
            cursor,
            "SELECT position_id, organization_id FROM coverage_requirements WHERE id = ?",
            (requirement_id,),
            "Coverage requirement not found",
        )
        if _access and int(requirement_row["organization_id"]) != int(_access["membership"]["organization_id"]):
            raise HTTPException(status_code=404, detail="Coverage requirement not found")
        services_memberships.ensure_department_access_for_position(cursor, _access, requirement_row["position_id"])
        cursor.execute("DELETE FROM coverage_requirements WHERE id = ?", (requirement_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Coverage requirement not found")
        connection.commit()
        return {"message": "Coverage requirement deleted successfully"}
    finally:
        connection.close()
