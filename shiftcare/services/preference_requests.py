"""Services: preference requests for ShiftCare."""
from __future__ import annotations

from schemas import EmployeeWeekPreferenceCreate
from shiftcare import config as app_constants

def count_confirmed_week_preference_days(cursor, organization_id: int, employee_id: int, week_start_date: str) -> int:
    cursor.execute(
        """
        SELECT COUNT(DISTINCT preference_date) AS count
        FROM employee_week_preferences
        WHERE organization_id = ?
          AND employee_id = ?
          AND week_start_date = ?
        """,
        (organization_id, employee_id, week_start_date),
    )
    return int(cursor.fetchone()["count"] or 0)


def has_confirmed_week_preference_on_date(
    cursor,
    organization_id: int,
    employee_id: int,
    preference_date: str,
) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM employee_week_preferences
        WHERE organization_id = ?
          AND employee_id = ?
          AND preference_date = ?
        LIMIT 1
        """,
        (organization_id, employee_id, preference_date),
    )
    return cursor.fetchone() is not None


def should_queue_week_preference_for_approval(
    cursor,
    preference_context: dict | None,
    organization_id: int,
    preference: EmployeeWeekPreferenceCreate,
) -> bool:
    if not preference_context or preference_context.get("scope") != "own":
        return False
    if has_confirmed_week_preference_on_date(cursor, organization_id, preference.employee_id, preference.preference_date):
        return False
    confirmed_day_count = count_confirmed_week_preference_days(
        cursor,
        organization_id,
        preference.employee_id,
        preference.week_start_date,
    )
    return confirmed_day_count >= app_constants.EMPLOYEE_DIRECT_WEEKLY_PREFERENCE_DAY_LIMIT


def delete_matching_pending_week_preference_requests(
    cursor,
    organization_id: int,
    preference: EmployeeWeekPreferenceCreate,
) -> None:
    if preference.request_type in {"day_off", "vacation"}:
        cursor.execute(
            """
            DELETE FROM employee_week_preference_requests
            WHERE organization_id = ?
              AND employee_id = ?
              AND preference_date = ?
              AND status = 'pending'
            """,
            (organization_id, preference.employee_id, preference.preference_date),
        )
        return
    cursor.execute(
        """
        DELETE FROM employee_week_preference_requests
        WHERE organization_id = ?
          AND employee_id = ?
          AND preference_date = ?
          AND request_type = ?
          AND target_category = ?
          AND status = 'pending'
        """,
        (
            organization_id,
            preference.employee_id,
            preference.preference_date,
            preference.request_type,
            preference.target_category,
        ),
    )


def save_confirmed_week_preference(
    cursor,
    preference: EmployeeWeekPreferenceCreate,
    organization_id: int,
    user_id: int | None,
    now: str,
    cleanup_pending: bool = True,
) -> int:
    if preference.request_type in {"day_off", "vacation"}:
        cursor.execute(
            """
            DELETE FROM employee_week_preferences
            WHERE organization_id = ? AND employee_id = ? AND preference_date = ?
            """,
            (organization_id, preference.employee_id, preference.preference_date),
        )
    else:
        cursor.execute(
            """
            DELETE FROM employee_week_preferences
            WHERE organization_id = ? AND employee_id = ? AND preference_date = ?
              AND request_type = ? AND target_category = ?
            """,
            (
                organization_id,
                preference.employee_id,
                preference.preference_date,
                preference.request_type,
                preference.target_category,
            ),
        )
    cursor.execute(
        """
        INSERT INTO employee_week_preferences
            (organization_id, employee_id, week_start_date, preference_date, preference_type,
             request_type, target_category, updated_at, updated_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            organization_id,
            preference.employee_id,
            preference.week_start_date,
            preference.preference_date,
            preference.preference_type,
            preference.request_type,
            preference.target_category,
            now,
            user_id,
        ),
    )
    preference_id = int(cursor.lastrowid)
    if cleanup_pending:
        delete_matching_pending_week_preference_requests(cursor, organization_id, preference)
    return preference_id


def queue_week_preference_request(
    cursor,
    preference: EmployeeWeekPreferenceCreate,
    organization_id: int,
    user_id: int | None,
    now: str,
) -> int:
    delete_matching_pending_week_preference_requests(cursor, organization_id, preference)
    cursor.execute(
        """
        INSERT INTO employee_week_preference_requests (
            organization_id, employee_id, week_start_date, preference_date, preference_type,
            request_type, target_category, status, created_at, updated_at, updated_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
        """,
        (
            organization_id,
            preference.employee_id,
            preference.week_start_date,
            preference.preference_date,
            preference.preference_type,
            preference.request_type,
            preference.target_category,
            now,
            now,
            user_id,
        ),
    )
    return int(cursor.lastrowid)
