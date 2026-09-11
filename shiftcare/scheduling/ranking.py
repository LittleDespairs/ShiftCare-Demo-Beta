"""Scheduling: ranking for ShiftCare."""
from __future__ import annotations

from shiftcare import config as app_constants
from shiftcare.scheduling import rules as scheduling_rules
from shiftcare.scheduling import settings as scheduling_settings
from shiftcare.services import schedule_queries as services_schedule_queries
import schedule_time

def generation_preference_penalty(penalty: int, generation_mode: str | None) -> int:
    mode = scheduling_settings.normalize_generation_mode(generation_mode)
    if mode == app_constants.GENERATION_MODE_COVERAGE:
        return scheduling_settings.scale_int(penalty, 35)
    if mode == app_constants.GENERATION_MODE_REQUESTS:
        return penalty * 3
    return penalty


def interval_generation_sort_key(
    generation_mode: str | None,
    target_shortage_gain: int,
    score: int,
    overage_cost: int,
    soft_preference_penalty: int,
    fatigue_penalty: int,
    projected_same_category_count: int,
    projected_same_category_streak: int,
    projected_night_count: int,
    projected_split_count: int,
    projected_balance: int,
    assignment_priority: tuple,
    priority: tuple,
):
    mode = scheduling_settings.normalize_generation_mode(generation_mode)
    shortage_priority = -target_shortage_gain if target_shortage_gain else -score
    preference_priority = generation_preference_penalty(soft_preference_penalty, mode)
    need_priority = priority[:1]
    workload_priority = priority[1:]
    if mode == app_constants.GENERATION_MODE_COVERAGE:
        return (
            shortage_priority,
            -score,
            overage_cost,
            fatigue_penalty,
            need_priority,
            assignment_priority,
            projected_balance,
            preference_priority,
            projected_same_category_count,
            projected_same_category_streak,
            projected_night_count,
            projected_split_count,
            workload_priority,
        )
    if mode == app_constants.GENERATION_MODE_REQUESTS:
        return (
            preference_priority,
            shortage_priority,
            fatigue_penalty,
            need_priority,
            assignment_priority,
            projected_balance,
            -score,
            overage_cost,
            projected_same_category_count,
            projected_same_category_streak,
            projected_night_count,
            projected_split_count,
            workload_priority,
        )
    return (
        shortage_priority,
        preference_priority,
        -score,
        overage_cost,
        fatigue_penalty,
        need_priority,
        assignment_priority,
        projected_balance,
        projected_same_category_count,
        projected_same_category_streak,
        projected_night_count,
        projected_split_count,
        workload_priority,
    )


def legacy_generation_sort_key(
    generation_mode: str | None,
    soft_preference_penalty: int,
    fatigue_penalty: int,
    projected_same_category_count: int,
    projected_same_category_streak: int,
    projected_night_count: int,
    projected_split_count: int,
    projected_balance: int,
    assignment_priority: tuple,
    priority: tuple,
):
    mode = scheduling_settings.normalize_generation_mode(generation_mode)
    preference_priority = generation_preference_penalty(soft_preference_penalty, mode)
    need_priority = priority[:1]
    workload_priority = priority[1:]
    if mode == app_constants.GENERATION_MODE_COVERAGE:
        return (
            fatigue_penalty,
            need_priority,
            assignment_priority,
            projected_balance,
            preference_priority,
            projected_same_category_count,
            projected_same_category_streak,
            projected_night_count,
            projected_split_count,
            workload_priority,
        )
    if mode == app_constants.GENERATION_MODE_REQUESTS:
        return (
            preference_priority,
            fatigue_penalty,
            need_priority,
            assignment_priority,
            projected_balance,
            projected_same_category_count,
            projected_same_category_streak,
            projected_night_count,
            projected_split_count,
            workload_priority,
        )
    return (
        preference_priority,
        fatigue_penalty,
        need_priority,
        assignment_priority,
        projected_balance,
        projected_same_category_count,
        projected_same_category_streak,
        projected_night_count,
        projected_split_count,
        workload_priority,
    )


def get_employee_week_category_count(connection, employee_id: int, week_start_date: str, category: str) -> int:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM schedule_entries se
        JOIN shift_templates st ON st.id = se.shift_template_id
        WHERE se.employee_id = ?
          AND se.date >= ?
          AND se.date <= ?
          AND st.category = ?
          AND se.no_show = 0
        """,
        (employee_id, week_start_date, schedule_time.get_week_end_date(week_start_date), category),
    )
    return cursor.fetchone()["cnt"]


def get_employee_week_split_day_count(connection, employee_id: int, week_start_date: str) -> int:
    return sum(
        1
        for date_string in schedule_time.build_week_dates(week_start_date)
        if scheduling_rules.employee_has_split_day(connection, employee_id, date_string)
    )


def candidate_priority(connection, employee: dict, date_string: str, week_start_date: str) -> tuple:
    week_count = services_schedule_queries.get_employee_week_shift_count(connection, employee["id"], week_start_date)
    worked_dates = services_schedule_queries.get_employee_week_worked_dates(connection, employee["id"], week_start_date)
    night_count = get_employee_week_category_count(connection, employee["id"], week_start_date, "night")
    split_count = get_employee_week_split_day_count(connection, employee["id"], week_start_date)
    if week_count < employee["min_shifts_per_week"]:
        bucket = 0
    elif week_count < employee["target_shifts_per_week"]:
        bucket = 1
    else:
        bucket = 2
    return (
        bucket,
        len(worked_dates),
        week_count,
        night_count,
        split_count,
        employee["id"],
    )


def candidate_assignment_priority(employee: dict) -> tuple:
    return (
        1 if employee.get("is_fallback_only") else 0,
        0 if employee.get("is_primary") else 1,
        -int(employee.get("priority_score", 50)),
    )
