"""Services: day status for ShiftCare."""
from __future__ import annotations

from shiftcare.services import schedule as services_schedule

def get_employee_day_status_map(connection, employee_ids: list[int], dates: list[str]) -> dict[tuple[int, str], dict]:
    if not employee_ids or not dates:
        return {}

    cursor = connection.cursor()
    employee_placeholders = ",".join(["?"] * len(employee_ids))
    date_placeholders = ",".join(["?"] * len(dates))
    cursor.execute(
        f"""
        SELECT *
        FROM employee_day_statuses
        WHERE employee_id IN ({employee_placeholders})
          AND date IN ({date_placeholders})
        """,
        [*employee_ids, *dates],
    )
    return {(row["employee_id"], row["date"]): dict(row) for row in cursor.fetchall()}


def sync_employee_day_off_status_for_date(connection, cursor, employee_id: int, date_string: str) -> None:
    cursor.execute("SELECT organization_id FROM employees WHERE id = ?", (employee_id,))
    employee_row = cursor.fetchone()
    organization_id = int(employee_row["organization_id"]) if employee_row else 1
    cursor.execute(
        """
        SELECT 1
        FROM schedule_entries
        WHERE employee_id = ? AND date = ?
        LIMIT 1
        """,
        (employee_id, date_string),
    )
    has_any_schedule_entry = cursor.fetchone() is not None

    if has_any_schedule_entry:
        cursor.execute(
            """
            DELETE FROM employee_day_statuses
            WHERE employee_id = ? AND date = ? AND status_type = 'day_off'
            """,
            (employee_id, date_string),
        )
        return

    cursor.execute(
        """
        SELECT status_type
        FROM employee_day_statuses
        WHERE employee_id = ? AND date = ?
        """,
        (employee_id, date_string),
    )
    existing_status = cursor.fetchone()
    if existing_status is not None:
        return

    cursor.execute(
        """
        INSERT INTO employee_day_statuses (organization_id, employee_id, date, status_type)
        VALUES (?, ?, ?, 'day_off')
        """,
        (organization_id, employee_id, date_string),
    )


def sync_generated_day_off_statuses(
    connection,
    cursor,
    employees: list[dict],
    position_id: int,
    dates: list[str],
) -> int:
    employee_ids = [employee["id"] for employee in employees]
    if not employee_ids or not dates:
        return 0

    employee_placeholders = ",".join(["?"] * len(employee_ids))
    date_placeholders = ",".join(["?"] * len(dates))
    cursor.execute(
        f"""
        DELETE FROM employee_day_statuses
        WHERE status_type = 'day_off'
          AND employee_id IN ({employee_placeholders})
          AND date IN ({date_placeholders})
        """,
        [*employee_ids, *dates],
    )

    entries = services_schedule.get_schedule_entries(connection, dates=dates)
    employee_id_set = set(employee_ids)
    scheduled_days = {
        (entry["employee_id"], entry["date"])
        for entry in entries
        if entry["employee_id"] in employee_id_set
    }
    day_status_map = get_employee_day_status_map(connection, employee_ids, dates)
    cursor.execute(
        f"""
        SELECT id, organization_id
        FROM employees
        WHERE id IN ({employee_placeholders})
        """,
        employee_ids,
    )
    organization_id_by_employee_id = {int(row["id"]): int(row["organization_id"]) for row in cursor.fetchall()}

    inserted_count = 0
    for employee_id in employee_ids:
        for date_string in dates:
            if (employee_id, date_string) in scheduled_days:
                continue
            if (employee_id, date_string) in day_status_map:
                continue
            cursor.execute(
                """
                INSERT INTO employee_day_statuses (organization_id, employee_id, date, status_type)
                VALUES (?, ?, ?, 'day_off')
                """,
                (organization_id_by_employee_id.get(employee_id, 1), employee_id, date_string),
            )
            inserted_count += 1

    return inserted_count
