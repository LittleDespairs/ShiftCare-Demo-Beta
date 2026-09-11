"""Scheduling: optimization for ShiftCare."""
from __future__ import annotations

from shiftcare import config as app_constants
from shiftcare.scheduling import previews as scheduling_previews
from shiftcare.scheduling import ranking as scheduling_ranking
from shiftcare.scheduling import rules as scheduling_rules
from shiftcare.scheduling import settings as scheduling_settings
from shiftcare.services import schedule_queries as services_schedule_queries
import app_settings_service
import schedule_time

def max_consecutive_in_week(connection, employee_id: int, week_dates: list[str], predicate) -> int:
    best = 0
    current = 0

    for date_string in week_dates:
        if predicate(connection, employee_id, date_string):
            current += 1
            best = max(best, current)
        else:
            current = 0

    return best


def append_fatigue_summary_warnings(
    connection,
    employees: list[dict],
    position_id: int,
    week_dates: list[str],
    week_start_date: str,
    errors: list[str],
) -> None:
    app_settings = app_settings_service.get_position_app_settings(connection, position_id)
    for employee in employees:
        worked_days = len(services_schedule_queries.get_employee_week_worked_dates(connection, employee["id"], week_start_date))
        if worked_days > app_settings["max_work_days_per_week"]:
            errors.append(
                f"{employee['full_name']} has {worked_days} worked days in the week; mandatory weekly day off is violated"
            )

        max_nights = max_consecutive_in_week(connection, employee["id"], week_dates, services_schedule_queries.employee_has_night_on_date)
        if max_nights > app_settings["max_consecutive_nights"]:
            errors.append(
                f"{employee['full_name']} has {max_nights} consecutive night days; normal limit is {app_settings['max_consecutive_nights']}"
            )

        max_splits = max_consecutive_in_week(connection, employee["id"], week_dates, scheduling_rules.employee_has_split_day)
        if max_splits > app_settings["max_consecutive_split_days"]:
            errors.append(
                f"{employee['full_name']} has {max_splits} consecutive split days; normal limit is {app_settings['max_consecutive_split_days']}"
            )


def get_employee_week_entries(
    connection,
    employee_id: int,
    week_start_date: str,
    exclude_entry_ids: set[int] | None = None,
    staged_entries: list[dict] | None = None,
) -> list[dict]:
    exclude_entry_ids = exclude_entry_ids or set()
    staged_entries = staged_entries or []

    cursor = connection.cursor()
    cursor.execute(
        """
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
        WHERE se.employee_id = ?
          AND se.date >= ?
          AND se.date <= ?
          AND se.no_show = 0
        """,
        (employee_id, week_start_date, schedule_time.get_week_end_date(week_start_date)),
    )

    entries = [dict(row) for row in cursor.fetchall() if row["id"] not in exclude_entry_ids]
    for entry in entries:
        entry["is_overnight"] = bool(entry["is_overnight"])
        entry["template_is_overnight"] = bool(entry["template_is_overnight"])
        entry["is_split_only"] = bool(entry["is_split_only"])
        if entry.get("is_overnight_override") is not None:
            entry["is_overnight_override"] = bool(entry["is_overnight_override"])
    entries.extend(staged_entries)
    return entries


def max_consecutive_projected(entries: list[dict], week_dates: list[str], predicate) -> int:
    entries_by_date: dict[str, list[dict]] = {}
    for entry in entries:
        entries_by_date.setdefault(entry["date"], []).append(entry)

    best = 0
    current = 0
    for date_string in week_dates:
        if predicate(entries_by_date.get(date_string, [])):
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def projected_employee_score(employee: dict, entries: list[dict], week_dates: list[str], app_settings: dict) -> int:
    week_count = len(entries)
    worked_dates = {entry["date"] for entry in entries}
    night_count = sum(1 for entry in entries if services_schedule_queries.entry_category(entry) == "night")
    split_day_count = sum(
        1
        for date_string in week_dates
        if {"morning", "evening"}.issubset({services_schedule_queries.entry_category(entry) for entry in entries if entry["date"] == date_string})
    )
    max_nights = max_consecutive_projected(
        entries,
        week_dates,
        lambda day_entries: any(services_schedule_queries.entry_category(entry) == "night" for entry in day_entries),
    )
    max_splits = max_consecutive_projected(
        entries,
        week_dates,
        lambda day_entries: {"morning", "evening"}.issubset({services_schedule_queries.entry_category(entry) for entry in day_entries}),
    )

    score = 0
    score += max(0, employee["min_shifts_per_week"] - week_count) * app_settings["balance_missing_min_weight"]
    score += abs(employee["target_shifts_per_week"] - week_count) * app_settings["balance_target_distance_weight"]
    score += max(0, week_count - employee["target_shifts_per_week"]) * app_settings["balance_over_target_weight"]
    score += max(0, week_count - employee["max_shifts_per_week"]) * app_settings["balance_over_max_weight"]
    score += len(worked_dates) * app_settings["balance_worked_day_weight"]
    score += max(0, len(worked_dates) - app_settings["max_work_days_per_week"]) * app_settings["balance_over_max_weight"]
    score += night_count * app_settings["balance_night_weight"]
    score += split_day_count * app_settings["balance_split_weight"]
    score += max_nights * app_settings["balance_consecutive_night_weight"]
    score += max_splits * app_settings["balance_consecutive_split_weight"]
    score += max(0, max_nights - app_settings["max_consecutive_nights"]) * app_settings["balance_excess_night_weight"]
    score += max(0, max_splits - app_settings["max_consecutive_split_days"]) * app_settings["balance_excess_split_weight"]
    return score


def get_projected_assignment_score(
    connection,
    employee: dict,
    week_start_date: str,
    staged_entries: list[dict],
    app_settings: dict,
) -> int:
    week_dates = schedule_time.build_week_dates(week_start_date)
    projected_entries = get_employee_week_entries(
        connection,
        employee["id"],
        week_start_date,
        staged_entries=staged_entries,
    )
    return projected_employee_score(employee, projected_entries, week_dates, app_settings)


def get_projected_assignment_counts(
    connection,
    employee: dict,
    week_start_date: str,
    staged_entries: list[dict],
) -> tuple[int, int]:
    week_dates = schedule_time.build_week_dates(week_start_date)
    projected_entries = get_employee_week_entries(
        connection,
        employee["id"],
        week_start_date,
        staged_entries=staged_entries,
    )
    projected_night_count = sum(1 for entry in projected_entries if services_schedule_queries.entry_category(entry) == "night")
    projected_split_count = sum(
        1
        for date_string in week_dates
        if {"morning", "evening"}.issubset({services_schedule_queries.entry_category(entry) for entry in projected_entries if entry["date"] == date_string})
    )
    return projected_night_count, projected_split_count


def get_projected_category_metrics(
    connection,
    employee: dict,
    week_start_date: str,
    staged_entries: list[dict],
    categories: list[str],
) -> tuple[int, int]:
    week_dates = schedule_time.build_week_dates(week_start_date)
    projected_entries = get_employee_week_entries(
        connection,
        employee["id"],
        week_start_date,
        staged_entries=staged_entries,
    )
    target_categories = set(categories)
    projected_category_count = sum(1 for entry in projected_entries if services_schedule_queries.entry_category(entry) in target_categories)
    projected_category_streak = max_consecutive_projected(
        projected_entries,
        week_dates,
        lambda day_entries: any(services_schedule_queries.entry_category(entry) in target_categories for entry in day_entries),
    )
    return projected_category_count, projected_category_streak


def row_to_template_for_assignment(row: dict) -> dict:
    return {
        "id": row["shift_template_id"],
        "name": row["shift_template_name"],
        "category": services_schedule_queries.entry_category(row),
        "start_time": row["start_time"],
        "end_time": row["end_time"],
        "is_overnight": bool(row["is_overnight"]),
        "is_active": True,
        "is_split_only": bool(row["is_split_only"]),
    }


def build_generated_assignment_groups(connection, created_entries: list[dict], position_id: int) -> list[list[dict]]:
    created_ids = [entry["id"] for entry in created_entries if entry.get("id")]
    if not created_ids:
        return []

    placeholders = ",".join(["?"] * len(created_ids))
    cursor = connection.cursor()
    cursor.execute(
        f"""
        SELECT
            se.id,
            se.employee_id,
            se.position_id,
            se.date,
            se.shift_template_id,
            st.name AS shift_template_name,
            st.category,
            st.start_time,
            st.end_time,
            st.is_overnight,
            st.is_split_only
        FROM schedule_entries se
        JOIN shift_templates st ON st.id = se.shift_template_id
        WHERE se.id IN ({placeholders})
          AND se.position_id = ?
        ORDER BY se.date, se.employee_id, st.start_time
        """,
        [*created_ids, position_id],
    )
    rows = [dict(row) for row in cursor.fetchall()]
    rows_by_id = {row["id"]: row for row in rows}
    visited: set[int] = set()
    groups: list[list[dict]] = []

    for row in rows:
        if row["id"] in visited:
            continue

        if row["category"] in {"morning", "evening"}:
            group = [
                candidate
                for candidate in rows
                if candidate["employee_id"] == row["employee_id"]
                and candidate["position_id"] == row["position_id"]
                and candidate["date"] == row["date"]
                and candidate["category"] in {"morning", "evening"}
            ]
        else:
            group = [row]

        group = [item for item in group if item["id"] in rows_by_id and item["id"] not in visited]
        if not group:
            continue
        for item in group:
            visited.add(item["id"])
        groups.append(sorted(group, key=lambda item: schedule_time.time_to_minutes(item["start_time"])))

    return groups


def post_optimize_generated_schedule(
    connection,
    cursor,
    employees: list[dict],
    position_id: int,
    week_start_date: str,
    week_dates: list[str],
    created_entries: list[dict],
    errors: list[str],
    generation_mode: str = app_constants.GENERATION_MODE_BALANCED,
) -> int:
    if scheduling_settings.normalize_generation_mode(generation_mode) != app_constants.GENERATION_MODE_BALANCED:
        return 0

    app_settings = scheduling_settings.get_generation_app_settings(connection, position_id, generation_mode)
    employee_by_id = {employee["id"]: employee for employee in employees}
    groups = build_generated_assignment_groups(connection, created_entries, position_id)
    moved_count = 0

    for group in groups:
        if not group:
            continue

        original_employee = employee_by_id.get(group[0]["employee_id"])
        if original_employee is None:
            continue

        date_string = group[0]["date"]
        entry_ids = {entry["id"] for entry in group}
        assignment_templates = [row_to_template_for_assignment(entry) for entry in group]
        original_assignment_priority = scheduling_ranking.candidate_assignment_priority(original_employee)
        original_entries_before = get_employee_week_entries(connection, original_employee["id"], week_start_date)
        original_entries_after = get_employee_week_entries(
            connection,
            original_employee["id"],
            week_start_date,
            exclude_entry_ids=entry_ids,
        )
        original_score_before = projected_employee_score(original_employee, original_entries_before, week_dates, app_settings)
        original_score_after = projected_employee_score(original_employee, original_entries_after, week_dates, app_settings)

        best_employee = None
        best_improvement = 0
        for candidate in employees:
            if candidate["id"] == original_employee["id"]:
                continue
            if scheduling_ranking.candidate_assignment_priority(candidate) > original_assignment_priority:
                continue

            previews = scheduling_previews.build_valid_assignment_previews(
                connection,
                candidate,
                assignment_templates,
                position_id,
                date_string,
                week_start_date,
                fatigue_relaxation=0,
            )
            if previews is None:
                continue

            candidate_entries_before = get_employee_week_entries(connection, candidate["id"], week_start_date)
            candidate_entries_after = get_employee_week_entries(
                connection,
                candidate["id"],
                week_start_date,
                staged_entries=previews,
            )
            before_score = original_score_before + projected_employee_score(
                candidate,
                candidate_entries_before,
                week_dates,
                app_settings,
            )
            after_score = original_score_after + projected_employee_score(
                candidate,
                candidate_entries_after,
                week_dates,
                app_settings,
            )
            improvement = before_score - after_score

            if improvement > best_improvement:
                best_improvement = improvement
                best_employee = candidate

        if best_employee is None or best_improvement < 80:
            continue

        cursor.execute(
            f"""
            UPDATE schedule_entries
            SET employee_id = ?
            WHERE id IN ({','.join(['?'] * len(entry_ids))})
            """,
            [best_employee["id"], *entry_ids],
        )
        for created_entry in created_entries:
            if created_entry.get("id") in entry_ids:
                created_entry["employee_id"] = best_employee["id"]
                created_entry["employee_name"] = best_employee["full_name"]
        moved_count += len(entry_ids)

    return moved_count
