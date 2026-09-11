"""Scheduling: data for ShiftCare."""
from __future__ import annotations

import row_serializers

def load_position_employees(connection, position_id: int) -> list[dict]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT e.*, ep.is_primary, ep.priority_score, ep.is_fallback_only
        FROM employees e
        JOIN employee_positions ep ON ep.employee_id = e.id
        WHERE ep.position_id = ?
        ORDER BY ep.is_fallback_only ASC, ep.is_primary DESC, ep.priority_score DESC, e.id
        """,
        (position_id,),
    )
    employees = []
    for row in cursor.fetchall():
        employee = row_serializers.row_to_employee_dict(row)
        employee["is_primary"] = bool(row["is_primary"])
        employee["priority_score"] = row["priority_score"]
        employee["is_fallback_only"] = bool(row["is_fallback_only"])
        employees.append(employee)
    return employees


def load_active_templates(connection, position_id: int) -> list[dict]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT st.*, p.name AS position_name, p.department_id, d.name AS department_name
        FROM shift_templates st
        JOIN positions p ON p.id = st.position_id
        LEFT JOIN departments d ON d.id = p.department_id
        WHERE st.position_id = ? AND st.is_active = 1
        ORDER BY st.start_time, st.end_time, st.category
        """,
        (position_id,),
    )
    return [row_serializers.row_to_shift_template_dict(row) for row in cursor.fetchall()]


def load_coverage_requirements_for_position(connection, position_id: int) -> list[dict]:
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM coverage_requirements WHERE position_id = ? ORDER BY start_time", (position_id,))
    return [dict(row) for row in cursor.fetchall()]


def load_legacy_shift_requirements(connection, position_id: int) -> list[dict]:
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM shift_requirements WHERE position_id = ?", (position_id,))
    return [dict(row) for row in cursor.fetchall()]
