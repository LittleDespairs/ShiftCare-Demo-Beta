"""Services: schedule for ShiftCare."""
from __future__ import annotations



def get_schedule_entries(
    connection,
    position_id: int | None = None,
    dates: list[str] | None = None,
    employee_id: int | None = None,
    organization_id: int | None = None,
    department_ids: set[int] | None = None,
) -> list[dict]:
    cursor = connection.cursor()
    clauses = []
    params: list = []
    if organization_id is not None:
        clauses.append("se.organization_id = ?")
        params.append(organization_id)
    if position_id is not None:
        clauses.append("se.position_id = ?")
        params.append(position_id)
    if dates:
        clauses.append(f"se.date IN ({','.join(['?'] * len(dates))})")
        params.extend(dates)
    if employee_id is not None:
        clauses.append("se.employee_id = ?")
        params.append(employee_id)
    if department_ids is not None:
        if not department_ids:
            clauses.append("1 = 0")
        else:
            placeholders = ",".join(["?"] * len(department_ids))
            clauses.append(f"p.department_id IN ({placeholders})")
            params.extend(sorted(department_ids))
    where_sql = "WHERE " + " AND ".join(clauses) if clauses else ""
    cursor.execute(
        f"""
        SELECT
            se.id,
            se.employee_id,
            se.position_id,
            se.date,
            se.shift_template_id,
            se.no_show,
            se.start_time_override,
            se.end_time_override,
            se.is_overnight_override,
            st.name AS shift_template_name,
            st.category AS shift_category,
            COALESCE(se.start_time_override, st.start_time) AS start_time,
            COALESCE(se.end_time_override, st.end_time) AS end_time,
            COALESCE(se.is_overnight_override, st.is_overnight) AS is_overnight,
            st.start_time AS template_start_time,
            st.end_time AS template_end_time,
            st.is_overnight AS template_is_overnight,
            st.is_split_only,
            p.name AS position_name,
            p.color AS position_color,
            p.department_id AS department_id,
            d.name AS department_name,
            e.full_name AS employee_name,
            e.sex AS employee_sex
        FROM schedule_entries se
        JOIN shift_templates st ON st.id = se.shift_template_id
        JOIN positions p ON p.id = se.position_id
        LEFT JOIN departments d ON d.id = p.department_id
        JOIN employees e ON e.id = se.employee_id
        {where_sql}
        ORDER BY se.date, se.employee_id, se.position_id, COALESCE(se.start_time_override, st.start_time)
        """,
        params,
    )
    items = [dict(row) for row in cursor.fetchall()]
    for item in items:
        item["is_overnight"] = bool(item["is_overnight"])
        item["template_is_overnight"] = bool(item["template_is_overnight"])
        item["is_split_only"] = bool(item["is_split_only"])
        item["no_show"] = bool(item["no_show"])
        if item["is_overnight_override"] is not None:
            item["is_overnight_override"] = bool(item["is_overnight_override"])
        item["time_overridden"] = (
            item["start_time_override"] is not None
            or item["end_time_override"] is not None
            or item["is_overnight_override"] is not None
        )
    return items


def clear_week_schedule_records(
    cursor,
    week_dates: list[str],
    *,
    position_id: int | None = None,
    employee_ids: list[int] | None = None,
    organization_id: int | None = None,
    department_ids: set[int] | None = None,
) -> tuple[int, int]:
    date_placeholders = ",".join(["?"] * len(week_dates))
    if position_id is None:
        schedule_clauses = [f"date IN ({date_placeholders})"]
        schedule_params: list = [*week_dates]
        if organization_id is not None:
            schedule_clauses.append("organization_id = ?")
            schedule_params.append(organization_id)
        if department_ids is not None:
            if not department_ids:
                return 0, 0
            department_placeholders = ",".join(["?"] * len(department_ids))
            schedule_clauses.append(
                f"position_id IN (SELECT id FROM positions WHERE department_id IN ({department_placeholders}))"
            )
            schedule_params.extend(sorted(department_ids))
        cursor.execute(
            f"""
            DELETE FROM schedule_entries
            WHERE {" AND ".join(schedule_clauses)}
            """,
            schedule_params,
        )
        deleted_count = cursor.rowcount
        day_status_clauses = ["status_type = 'day_off'", f"date IN ({date_placeholders})"]
        day_status_params: list = [*week_dates]
        if organization_id is not None:
            day_status_clauses.append("organization_id = ?")
            day_status_params.append(organization_id)
        if department_ids is not None:
            department_placeholders = ",".join(["?"] * len(department_ids))
            day_status_clauses.append(
                """
                employee_id IN (
                    SELECT DISTINCT ep.employee_id
                    FROM employee_positions ep
                    JOIN positions p ON p.id = ep.position_id
                    WHERE p.department_id IN (""" + department_placeholders + """)
                )
                """
            )
            day_status_params.extend(sorted(department_ids))
        cursor.execute(
            f"""
            DELETE FROM employee_day_statuses
            WHERE {" AND ".join(day_status_clauses)}
            """,
            day_status_params,
        )
        return deleted_count, cursor.rowcount

    schedule_clauses = [f"position_id = ?", f"date IN ({date_placeholders})"]
    schedule_params: list = [position_id, *week_dates]
    if organization_id is not None:
        schedule_clauses.append("organization_id = ?")
        schedule_params.append(organization_id)
    cursor.execute(
        f"""
        DELETE FROM schedule_entries
        WHERE {" AND ".join(schedule_clauses)}
        """,
        schedule_params,
    )
    deleted_count = cursor.rowcount
    day_off_deleted_count = 0
    if employee_ids:
        employee_placeholders = ",".join(["?"] * len(employee_ids))
        day_status_clauses = [
            "status_type = 'day_off'",
            f"employee_id IN ({employee_placeholders})",
            f"date IN ({date_placeholders})",
        ]
        day_status_params: list = [*employee_ids, *week_dates]
        if organization_id is not None:
            day_status_clauses.append("organization_id = ?")
            day_status_params.append(organization_id)
        cursor.execute(
            f"""
            DELETE FROM employee_day_statuses
            WHERE {" AND ".join(day_status_clauses)}
            """,
            day_status_params,
        )
        day_off_deleted_count = cursor.rowcount
    return deleted_count, day_off_deleted_count
