"""Scheduling: rules for ShiftCare."""
from __future__ import annotations

from datetime import timedelta
from fastapi import HTTPException
from schemas import ScheduleEntryCreate
from shiftcare.services import common as services_common
from shiftcare.services import preferences as services_preferences
from shiftcare.services import schedule_queries as services_schedule_queries
import app_settings_service
import row_serializers
import schedule_time

def get_projected_day_work_minutes(existing_entries: list[dict], template: dict) -> int:
    return sum(services_schedule_queries.get_template_work_minutes(entry) for entry in existing_entries) + services_schedule_queries.get_template_work_minutes(template)


def get_position_same_day_other_positions_flags(connection, position_ids: set[int]) -> dict[int, bool]:
    if not position_ids:
        return {}

    cursor = connection.cursor()
    placeholders = ",".join(["?"] * len(position_ids))
    cursor.execute(
        f"""
        SELECT id, allow_same_day_other_positions
        FROM positions
        WHERE id IN ({placeholders})
        """,
        sorted(position_ids),
    )
    return {int(row["id"]): bool(row["allow_same_day_other_positions"]) for row in cursor.fetchall()}


def cross_position_same_day_rejection(
    connection,
    position_id: int,
    existing_entries: list[dict],
) -> str | None:
    existing_position_ids = {int(entry["position_id"]) for entry in existing_entries}
    other_position_ids = {existing_position_id for existing_position_id in existing_position_ids if existing_position_id != position_id}
    if not other_position_ids:
        return None

    involved_position_ids = set(other_position_ids)
    involved_position_ids.add(position_id)
    flags = get_position_same_day_other_positions_flags(connection, involved_position_ids)
    if not all(flags.get(involved_position_id, False) for involved_position_id in involved_position_ids):
        return "same-day work with other positions is not allowed for one of the positions"
    return None


def employee_has_split_day(connection, employee_id: int, date_string: str) -> bool:
    entries = services_schedule_queries.get_employee_entries_for_date(connection, employee_id, date_string)
    categories = {entry["category"] for entry in entries}
    return "morning" in categories and "evening" in categories


def would_have_night_day(connection, employee_id: int, date_string: str, template: dict) -> bool:
    return template["category"] == "night" or services_schedule_queries.employee_has_night_on_date(connection, employee_id, date_string)


def would_have_split_day(connection, employee_id: int, date_string: str, template: dict) -> bool:
    entries = services_schedule_queries.get_employee_entries_for_date(connection, employee_id, date_string)
    categories = {entry["category"] for entry in entries}
    categories.add(template["category"])
    return "morning" in categories and "evening" in categories


def explain_same_day_pairing_rejection(
    connection,
    employee: dict,
    date_string: str,
    template: dict,
    existing_entries: list[dict],
    app_settings: dict,
) -> str | None:
    if not existing_entries:
        return None

    if len(existing_entries) >= 2:
        return "employee already has two shifts that day"

    existing_categories = {services_schedule_queries.entry_category(entry) for entry in existing_entries}
    projected_categories = set(existing_categories)
    projected_categories.add(template["category"])

    if projected_categories == {"morning", "evening"}:
        if not employee["can_work_mornings_and_evenings"]:
            return "employee cannot work morning and evening on the same day"
        if services_preferences.get_week_preference(connection, employee["id"], date_string) == "no_morning_evening_combo":
            return "weekly preference blocks morning-evening combo"
        if services_preferences.get_recurring_preference(connection, employee["id"], date_string, "strict") == "no_morning_evening_combo":
            return "permanent strict preference blocks morning-evening combo"

        morning_evening_break = services_schedule_queries.get_break_minutes_between_same_day_categories(
            connection,
            employee["id"],
            date_string,
            template,
            "morning",
            "evening",
            entries=existing_entries,
        )
        if (
            morning_evening_break is not None
            and morning_evening_break < app_settings["min_rest_minutes_between_morning_and_evening"]
        ):
            return "morning-evening rest gap is too short"
        if get_projected_day_work_minutes(existing_entries, template) > app_settings["max_daily_work_minutes"]:
            return "daily work limit exceeded"

        return None

    if projected_categories == {"morning", "night"}:
        return None

    return "employee already has another shift type that cannot be paired"


def count_consecutive_days_before(connection, employee_id: int, date_string: str, predicate) -> int:
    current_date = schedule_time.parse_date_string(date_string) - timedelta(days=1)
    count = 0

    while count < 7:
        if not predicate(connection, employee_id, current_date.isoformat()):
            break
        count += 1
        current_date -= timedelta(days=1)

    return count


def count_consecutive_days_after(connection, employee_id: int, date_string: str, predicate) -> int:
    current_date = schedule_time.parse_date_string(date_string) + timedelta(days=1)
    count = 0

    while count < 7:
        if not predicate(connection, employee_id, current_date.isoformat()):
            break
        count += 1
        current_date += timedelta(days=1)

    return count


def get_fatigue_penalty(connection, employee_id: int, date_string: str, template: dict) -> int:
    row = connection.execute("SELECT organization_id FROM employees WHERE id = ?", (employee_id,)).fetchone()
    organization_id = int(row["organization_id"]) if row else 1
    app_settings = app_settings_service.get_app_settings(connection, organization_id=organization_id)
    penalty = 0

    if services_schedule_queries.had_previous_night(connection, employee_id, date_string):
        if template["category"] == "evening":
            penalty += app_settings["after_night_evening_penalty"]
        elif template["category"] == "night":
            penalty += app_settings["after_night_evening_penalty"] // 2

    if would_have_night_day(connection, employee_id, date_string, template):
        previous_nights = count_consecutive_days_before(connection, employee_id, date_string, services_schedule_queries.employee_has_night_on_date)
        next_nights = count_consecutive_days_after(connection, employee_id, date_string, services_schedule_queries.employee_has_night_on_date)
        penalty += (previous_nights + next_nights) * app_settings["consecutive_night_penalty"]

    if would_have_split_day(connection, employee_id, date_string, template):
        previous_splits = count_consecutive_days_before(connection, employee_id, date_string, employee_has_split_day)
        next_splits = count_consecutive_days_after(connection, employee_id, date_string, employee_has_split_day)
        penalty += (previous_splits + next_splits) * app_settings["consecutive_split_penalty"]

    return penalty


def can_employee_take_template(
    connection,
    employee: dict,
    position_id: int,
    date_string: str,
    template: dict,
    week_start_date: str,
    fatigue_relaxation: int = 0,
    staged_entries: list[dict] | None = None,
) -> bool:
    app_settings = app_settings_service.get_position_app_settings(connection, position_id)
    staged_entries = staged_entries or []
    week_end_date = schedule_time.get_week_end_date(week_start_date)
    staged_week_entries = [
        entry
        for entry in staged_entries
        if entry["employee_id"] == employee["id"] and week_start_date <= entry["date"] <= week_end_date
    ]

    if services_preferences.get_employee_day_status(connection, employee["id"], date_string):
        return False
    if not services_preferences.category_allowed_by_preferences(connection, employee, date_string, template["category"]):
        return False
    if services_schedule_queries.get_employee_week_shift_count(connection, employee["id"], week_start_date) + len(staged_week_entries) >= employee["max_shifts_per_week"]:
        return False

    worked_dates = services_schedule_queries.get_employee_week_worked_dates(connection, employee["id"], week_start_date)
    worked_dates.update(entry["date"] for entry in staged_week_entries)
    projected_worked_dates = set(worked_dates)
    projected_worked_dates.add(date_string)
    if len(projected_worked_dates) > app_settings["max_work_days_per_week"]:
        return False

    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT 1
        FROM employee_positions
        WHERE employee_id = ? AND position_id = ?
        """,
        (employee["id"], position_id),
    )
    if not cursor.fetchone():
        return False

    new_interval = schedule_time.build_interval(template["start_time"], template["end_time"], template["is_overnight"])
    existing_entries = [
        *services_schedule_queries.get_employee_entries_for_date(connection, employee["id"], date_string),
        *[
            entry
            for entry in staged_entries
            if entry["employee_id"] == employee["id"] and entry["date"] == date_string
        ],
    ]

    if cross_position_same_day_rejection(connection, position_id, existing_entries):
        return False

    for entry in existing_entries:
        existing_interval = schedule_time.build_interval(entry["start_time"], entry["end_time"], bool(entry["is_overnight"]))
        if new_interval.overlaps(existing_interval):
            return False

    if explain_same_day_pairing_rejection(connection, employee, date_string, template, existing_entries, app_settings):
        return False

    if services_schedule_queries.had_previous_night(connection, employee["id"], date_string, staged_entries=staged_entries):
        if template["category"] == "morning":
            return False

        if template["category"] == "evening":
            break_minutes = services_schedule_queries.get_break_minutes_after_previous_night(
                connection,
                employee["id"],
                date_string,
                template,
                staged_entries=staged_entries,
            )
            if (
                break_minutes is None
                or break_minutes < app_settings["min_rest_minutes_after_night_before_evening"]
            ):
                return False

    if template["category"] == "night" and services_schedule_queries.has_next_morning(
        connection,
        employee["id"],
        date_string,
        staged_entries=staged_entries,
    ):
        return False

    if would_have_night_day(connection, employee["id"], date_string, template):
        previous_nights = count_consecutive_days_before(connection, employee["id"], date_string, services_schedule_queries.employee_has_night_on_date)
        next_nights = count_consecutive_days_after(connection, employee["id"], date_string, services_schedule_queries.employee_has_night_on_date)
        projected_nights = previous_nights + 1 + next_nights
        allowed_nights = (
            app_settings["max_consecutive_nights"]
            if fatigue_relaxation == 0
            else app_settings["emergency_max_consecutive_nights"]
        )
        if projected_nights > allowed_nights:
            return False

    existing_categories = {services_schedule_queries.entry_category(entry) for entry in existing_entries}
    projected_categories = set(existing_categories)
    projected_categories.add(template["category"])
    if "morning" in projected_categories and "evening" in projected_categories:
        previous_splits = count_consecutive_days_before(connection, employee["id"], date_string, employee_has_split_day)
        next_splits = count_consecutive_days_after(connection, employee["id"], date_string, employee_has_split_day)
        projected_splits = previous_splits + 1 + next_splits
        allowed_splits = (
            app_settings["max_consecutive_split_days"]
            if fatigue_relaxation == 0
            else app_settings["emergency_max_consecutive_split_days"]
        )
        if projected_splits > allowed_splits:
            return False

    return True


def explain_employee_template_rejection(
    connection,
    employee: dict,
    position_id: int,
    date_string: str,
    template: dict,
    week_start_date: str,
    fatigue_relaxation: int = 0,
    staged_entries: list[dict] | None = None,
) -> str | None:
    app_settings = app_settings_service.get_position_app_settings(connection, position_id)
    staged_entries = staged_entries or []
    week_end_date = schedule_time.get_week_end_date(week_start_date)
    staged_week_entries = [
        entry
        for entry in staged_entries
        if entry["employee_id"] == employee["id"] and week_start_date <= entry["date"] <= week_end_date
    ]

    if services_preferences.get_employee_day_status(connection, employee["id"], date_string):
        return "day status blocks employee"
    if not services_preferences.category_allowed_by_preferences(connection, employee, date_string, template["category"]):
        return "employee preferences or permissions block this shift"
    if services_schedule_queries.get_employee_week_shift_count(connection, employee["id"], week_start_date) + len(staged_week_entries) >= employee["max_shifts_per_week"]:
        return "employee reached weekly maximum shifts"

    worked_dates = services_schedule_queries.get_employee_week_worked_dates(connection, employee["id"], week_start_date)
    worked_dates.update(entry["date"] for entry in staged_week_entries)
    projected_worked_dates = set(worked_dates)
    projected_worked_dates.add(date_string)
    if len(projected_worked_dates) > app_settings["max_work_days_per_week"]:
        return "mandatory weekly day off would be violated"

    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT 1
        FROM employee_positions
        WHERE employee_id = ? AND position_id = ?
        """,
        (employee["id"], position_id),
    )
    if not cursor.fetchone():
        return "employee is not assigned to this position"

    new_interval = schedule_time.build_interval(template["start_time"], template["end_time"], template["is_overnight"])
    existing_entries = [
        *services_schedule_queries.get_employee_entries_for_date(connection, employee["id"], date_string),
        *[
            entry
            for entry in staged_entries
            if entry["employee_id"] == employee["id"] and entry["date"] == date_string
        ],
    ]
    cross_position_rejection = cross_position_same_day_rejection(connection, position_id, existing_entries)
    if cross_position_rejection:
        return cross_position_rejection
    for entry in existing_entries:
        existing_interval = schedule_time.build_interval(entry["start_time"], entry["end_time"], bool(entry["is_overnight"]))
        if new_interval.overlaps(existing_interval):
            return "employee already has an overlapping shift"

    pairing_rejection = explain_same_day_pairing_rejection(
        connection,
        employee,
        date_string,
        template,
        existing_entries,
        app_settings,
    )
    if pairing_rejection:
        return pairing_rejection

    if services_schedule_queries.had_previous_night(connection, employee["id"], date_string, staged_entries=staged_entries):
        if template["category"] == "morning":
            return "morning after previous night is forbidden"

        if template["category"] == "evening":
            break_minutes = services_schedule_queries.get_break_minutes_after_previous_night(
                connection,
                employee["id"],
                date_string,
                template,
                staged_entries=staged_entries,
            )
            if (
                break_minutes is None
                or break_minutes < app_settings["min_rest_minutes_after_night_before_evening"]
            ):
                return "night-evening rest gap is too short"

    if template["category"] == "night" and services_schedule_queries.has_next_morning(
        connection,
        employee["id"],
        date_string,
        staged_entries=staged_entries,
    ):
        return "night before next morning is forbidden"

    if would_have_night_day(connection, employee["id"], date_string, template):
        previous_nights = count_consecutive_days_before(connection, employee["id"], date_string, services_schedule_queries.employee_has_night_on_date)
        next_nights = count_consecutive_days_after(connection, employee["id"], date_string, services_schedule_queries.employee_has_night_on_date)
        projected_nights = previous_nights + 1 + next_nights
        allowed_nights = (
            app_settings["max_consecutive_nights"]
            if fatigue_relaxation == 0
            else app_settings["emergency_max_consecutive_nights"]
        )
        if projected_nights > allowed_nights:
            return "too many consecutive night shifts"

    existing_categories = {services_schedule_queries.entry_category(entry) for entry in existing_entries}
    projected_categories = set(existing_categories)
    projected_categories.add(template["category"])
    if "morning" in projected_categories and "evening" in projected_categories:
        previous_splits = count_consecutive_days_before(connection, employee["id"], date_string, employee_has_split_day)
        next_splits = count_consecutive_days_after(connection, employee["id"], date_string, employee_has_split_day)
        projected_splits = previous_splits + 1 + next_splits
        allowed_splits = (
            app_settings["max_consecutive_split_days"]
            if fatigue_relaxation == 0
            else app_settings["emergency_max_consecutive_split_days"]
        )
        if projected_splits > allowed_splits:
            return "too many consecutive split shifts"

    return None


def validate_schedule_entry_basic(connection, entry: ScheduleEntryCreate):
    schedule_time.parse_date_string(entry.date)
    cursor = connection.cursor()
    employee_row = services_common.fetch_one_or_404(cursor, "SELECT * FROM employees WHERE id = ?", (entry.employee_id,), "Employee not found")
    services_common.fetch_one_or_404(cursor, "SELECT * FROM positions WHERE id = ?", (entry.position_id,), "Position not found")
    template_row = services_common.fetch_one_or_404(
        cursor,
        "SELECT * FROM shift_templates WHERE id = ? AND position_id = ?",
        (entry.shift_template_id, entry.position_id),
        "Shift template not found for this position",
    )
    employee = row_serializers.row_to_employee_dict(employee_row)
    template = row_serializers.row_to_shift_template_dict(template_row)
    week_start = schedule_time.get_week_start_for_date(entry.date)
    if not can_employee_take_template(connection, employee, entry.position_id, entry.date, template, week_start):
        raise HTTPException(status_code=400, detail="Employee cannot be assigned to this shift")
    return employee, template


def validate_manual_schedule_entry_basics(connection, entry: ScheduleEntryCreate):
    schedule_time.parse_date_string(entry.date)
    cursor = connection.cursor()
    services_common.fetch_one_or_404(cursor, "SELECT id FROM employees WHERE id = ?", (entry.employee_id,), "Employee not found")
    services_common.fetch_one_or_404(cursor, "SELECT id FROM positions WHERE id = ?", (entry.position_id,), "Position not found")
    template_row = services_common.fetch_one_or_404(
        cursor,
        "SELECT * FROM shift_templates WHERE id = ? AND position_id = ?",
        (entry.shift_template_id, entry.position_id),
        "Shift template not found for this position",
    )
    return row_serializers.row_to_shift_template_dict(template_row)
