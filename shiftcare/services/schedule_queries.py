"""Services: schedule queries for ShiftCare."""
from __future__ import annotations

from datetime import timedelta
import schedule_time

def get_employee_week_shift_count(connection, employee_id: int, week_start_date: str) -> int:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM schedule_entries
        WHERE employee_id = ? AND date >= ? AND date <= ? AND no_show = 0
        """,
        (employee_id, week_start_date, schedule_time.get_week_end_date(week_start_date)),
    )
    return cursor.fetchone()["cnt"]


def get_employee_week_worked_dates(connection, employee_id: int, week_start_date: str) -> set[str]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT DISTINCT date
        FROM schedule_entries
        WHERE employee_id = ? AND date >= ? AND date <= ? AND no_show = 0
        """,
        (employee_id, week_start_date, schedule_time.get_week_end_date(week_start_date)),
    )
    return {row["date"] for row in cursor.fetchall()}


def entry_category(entry: dict) -> str:
    return entry.get("category") or entry.get("shift_category")


def get_employee_entries_for_date(connection, employee_id: int, date_string: str) -> list[dict]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT
            se.*,
            st.category,
            COALESCE(se.start_time_override, st.start_time) AS start_time,
            COALESCE(se.end_time_override, st.end_time) AS end_time,
            COALESCE(se.is_overnight_override, st.is_overnight) AS is_overnight,
            st.start_time AS template_start_time,
            st.end_time AS template_end_time,
            st.is_overnight AS template_is_overnight,
            st.is_split_only
        FROM schedule_entries se
        JOIN shift_templates st ON st.id = se.shift_template_id
        WHERE se.employee_id = ? AND se.date = ? AND se.no_show = 0
        ORDER BY COALESCE(se.start_time_override, st.start_time)
        """,
        (employee_id, date_string),
    )
    entries = [dict(row) for row in cursor.fetchall()]
    for entry in entries:
        entry["is_overnight"] = bool(entry["is_overnight"])
        entry["template_is_overnight"] = bool(entry["template_is_overnight"])
        entry["is_split_only"] = bool(entry["is_split_only"])
        if entry.get("is_overnight_override") is not None:
            entry["is_overnight_override"] = bool(entry["is_overnight_override"])
    return entries


def employee_has_night_on_date(connection, employee_id: int, date_string: str) -> bool:
    return any(entry["category"] == "night" for entry in get_employee_entries_for_date(connection, employee_id, date_string))


def get_previous_night_entries(
    connection,
    employee_id: int,
    date_string: str,
    staged_entries: list[dict] | None = None,
) -> list[dict]:
    previous_date = (schedule_time.parse_date_string(date_string) - timedelta(days=1)).isoformat()
    staged_entries = staged_entries or []
    return [
        entry
        for entry in [
            *get_employee_entries_for_date(connection, employee_id, previous_date),
            *[
                staged_entry
                for staged_entry in staged_entries
                if staged_entry["employee_id"] == employee_id and staged_entry["date"] == previous_date
            ],
        ]
        if entry_category(entry) == "night"
    ]


def had_previous_night(
    connection,
    employee_id: int,
    date_string: str,
    staged_entries: list[dict] | None = None,
) -> bool:
    return bool(get_previous_night_entries(connection, employee_id, date_string, staged_entries))


def get_next_morning_entries(
    connection,
    employee_id: int,
    date_string: str,
    staged_entries: list[dict] | None = None,
) -> list[dict]:
    next_date = (schedule_time.parse_date_string(date_string) + timedelta(days=1)).isoformat()
    staged_entries = staged_entries or []
    return [
        entry
        for entry in [
            *get_employee_entries_for_date(connection, employee_id, next_date),
            *[
                staged_entry
                for staged_entry in staged_entries
                if staged_entry["employee_id"] == employee_id and staged_entry["date"] == next_date
            ],
        ]
        if entry_category(entry) == "morning"
    ]


def has_next_morning(
    connection,
    employee_id: int,
    date_string: str,
    staged_entries: list[dict] | None = None,
) -> bool:
    return bool(get_next_morning_entries(connection, employee_id, date_string, staged_entries))


def get_break_minutes_after_previous_night(
    connection,
    employee_id: int,
    date_string: str,
    template: dict,
    staged_entries: list[dict] | None = None,
) -> int | None:
    previous_nights = get_previous_night_entries(connection, employee_id, date_string, staged_entries)
    if not previous_nights:
        return None

    current_start = 24 * 60 + schedule_time.time_to_minutes(template["start_time"])
    shortest_break = None
    for entry in previous_nights:
        night_interval = schedule_time.build_interval(entry["start_time"], entry["end_time"], bool(entry["is_overnight"]))
        break_minutes = current_start - night_interval.end
        if shortest_break is None or break_minutes < shortest_break:
            shortest_break = break_minutes

    return shortest_break


def get_break_minutes_between_same_day_categories(
    connection,
    employee_id: int,
    date_string: str,
    template: dict,
    first_category: str,
    second_category: str,
    entries: list[dict] | None = None,
) -> int | None:
    template_interval = schedule_time.build_interval(template["start_time"], template["end_time"], template["is_overnight"])
    breaks = []

    for entry in entries if entries is not None else get_employee_entries_for_date(connection, employee_id, date_string):
        if entry_category(entry) == first_category and template["category"] == second_category:
            first_interval = schedule_time.build_interval(entry["start_time"], entry["end_time"], bool(entry["is_overnight"]))
            breaks.append(template_interval.start - first_interval.end)

        if entry_category(entry) == second_category and template["category"] == first_category:
            second_interval = schedule_time.build_interval(entry["start_time"], entry["end_time"], bool(entry["is_overnight"]))
            breaks.append(second_interval.start - template_interval.end)

    if not breaks:
        return None

    return min(breaks)


def get_template_work_minutes(template: dict) -> int:
    interval = schedule_time.build_interval(template["start_time"], template["end_time"], bool(template["is_overnight"]))
    return interval.end - interval.start
