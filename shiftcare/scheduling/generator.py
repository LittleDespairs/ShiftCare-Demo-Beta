"""Scheduling: generator for ShiftCare."""
from __future__ import annotations

from fastapi import HTTPException
from shiftcare import config as app_constants
from shiftcare.scheduling import data as scheduling_data
from shiftcare.scheduling import feasibility as scheduling_feasibility
from shiftcare.scheduling import interval as scheduling_interval
from shiftcare.scheduling import legacy as scheduling_legacy
from shiftcare.scheduling import optimization as scheduling_optimization
from shiftcare.scheduling import settings as scheduling_settings
from shiftcare.services import common as services_common
from shiftcare.services import day_status as services_day_status
import row_serializers
import schedule_time

def run_auto_generate_for_position(
    connection,
    position_id: int,
    week_start_date: str,
    generation_mode: str = app_constants.GENERATION_MODE_BALANCED,
    sync_day_off_statuses: bool = True,
) -> dict:
    generation_mode = scheduling_settings.normalize_generation_mode(generation_mode)
    cursor = connection.cursor()
    position_row = services_common.fetch_one_or_404(
        cursor,
        """
        SELECT p.*, d.public_id AS department_public_id, d.name AS department_name
        FROM positions p
        LEFT JOIN departments d ON d.id = p.department_id
        WHERE p.id = ?
        """,
        (position_id,),
        "Position not found",
    )
    position = row_serializers.row_to_position_dict(position_row)
    week_dates = schedule_time.build_week_dates(week_start_date)
    employees = scheduling_data.load_position_employees(connection, position_id)
    if not employees:
        raise HTTPException(status_code=400, detail="No employees assigned to this position")

    templates_list = scheduling_data.load_active_templates(connection, position_id)
    if not templates_list:
        raise HTTPException(status_code=400, detail="No active shift templates found")

    coverage_requirements = scheduling_data.load_coverage_requirements_for_position(connection, position_id)
    legacy_requirements = scheduling_data.load_legacy_shift_requirements(connection, position_id)
    if not coverage_requirements and not legacy_requirements:
        raise HTTPException(status_code=400, detail="No coverage or shift requirements found for this position")

    created_entries: list[dict] = []
    errors: list[str] = []
    unfilled_reports: list[dict] = []
    feasibility_report = scheduling_feasibility.build_generation_feasibility_report(
        connection,
        employees,
        templates_list,
        coverage_requirements,
        legacy_requirements,
        position_id,
        week_start_date,
        week_dates,
    )
    for issue in feasibility_report["issues"]:
        errors.append(scheduling_feasibility.format_feasibility_issue(issue))

    if coverage_requirements:
        scheduling_interval.fill_week_by_interval_coverage(
            connection,
            cursor,
            employees,
            templates_list,
            coverage_requirements,
            position_id,
            week_start_date,
            week_dates,
            created_entries,
            errors,
            unfilled_reports,
            generation_mode=generation_mode,
        )
    else:
        for date_string in week_dates:
            scheduling_legacy.fill_day_by_legacy_categories(
                connection,
                cursor,
                employees,
                templates_list,
                legacy_requirements,
                position_id,
                week_start_date,
                date_string,
                created_entries,
                errors,
                unfilled_reports,
                generation_mode=generation_mode,
            )

    optimization_moved_count = scheduling_optimization.post_optimize_generated_schedule(
        connection,
        cursor,
        employees,
        position_id,
        week_start_date,
        week_dates,
        created_entries,
        errors,
        generation_mode=generation_mode,
    )

    scheduling_optimization.append_fatigue_summary_warnings(connection, employees, position_id, week_dates, week_start_date, errors)
    day_off_count = 0
    if sync_day_off_statuses:
        day_off_count = services_day_status.sync_generated_day_off_statuses(
            connection,
            cursor,
            employees,
            position_id,
            week_dates,
        )

    return {
        "message": "Auto-generation finished",
        "generation_mode": generation_mode,
        "position_id": position_id,
        "position_name": position["name"],
        "created_count": len(created_entries),
        "created_entries": created_entries,
        "day_off_count": day_off_count,
        "optimization_moved_count": optimization_moved_count,
        "feasibility_report": feasibility_report,
        "unfilled_reports": unfilled_reports,
        "errors": errors,
    }


def load_positions_for_auto_generation(
    cursor,
    organization_id: int | None = None,
    department_ids: set[int] | None = None,
) -> list[dict]:
    conditions = []
    params: list = []
    if organization_id is not None:
        conditions.append("p.organization_id = ?")
        params.append(organization_id)
    if department_ids is not None:
        if not department_ids:
            conditions.append("1 = 0")
        else:
            placeholders = ",".join(["?"] * len(department_ids))
            conditions.append(f"p.department_id IN ({placeholders})")
            params.extend(sorted(department_ids))
    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    cursor.execute(
        f"""
        SELECT
            p.id,
            p.name,
            p.department_id,
            d.name AS department_name,
            COALESCE(MAX(CASE
                WHEN ep.is_primary = 1 AND ep.is_fallback_only = 0 THEN 1
                ELSE 0
            END), 0) AS has_primary_regular_staff,
            COALESCE(MAX(CASE
                WHEN ep.is_primary = 1 AND ep.is_fallback_only = 0 THEN ep.priority_score
                ELSE -1
            END), -1) AS best_primary_priority,
            COALESCE(MAX(CASE
                WHEN ep.is_fallback_only = 0 THEN ep.priority_score
                ELSE -1
            END), -1) AS best_regular_priority,
            COUNT(ep.employee_id) AS assignment_count
        FROM positions p
        LEFT JOIN departments d ON d.id = p.department_id
        LEFT JOIN employee_positions ep ON ep.position_id = p.id
        {where_sql}
        GROUP BY p.id, p.name, p.department_id, d.name, d.display_order, d.id
        ORDER BY
            d.display_order,
            d.id,
            has_primary_regular_staff DESC,
            best_primary_priority DESC,
            best_regular_priority DESC,
            assignment_count DESC,
            p.id
        """,
        params,
    )
    return [dict(row) for row in cursor.fetchall()]
