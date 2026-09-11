"""Services: preferences for ShiftCare."""
from __future__ import annotations

from shiftcare import config as app_constants
from shiftcare.services import common as services_common
from shiftcare.services import schedule_queries as services_schedule_queries
import schedule_time

def get_week_preference(connection, employee_id: int, date_string: str) -> str:
    preferences = get_week_preferences(connection, employee_id, date_string)
    if any(item["request_type"] in {"day_off", "vacation"} for item in preferences):
        blocker = next(item["request_type"] for item in preferences if item["request_type"] in {"day_off", "vacation"})
        return "off_day" if blocker == "day_off" else blocker
    excluded = [item["target_category"] for item in preferences if item["request_type"] == "exclude_shift"]
    requested = [item["target_category"] for item in preferences if item["request_type"] == "request_shift"]
    if len(excluded) == 1:
        return f"not_{excluded[0]}"
    if len(requested) == 1 and not excluded:
        return f"only_{requested[0]}"
    return "no_preference"


def get_week_preferences(connection, employee_id: int, date_string: str) -> list[dict]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT preference_type, request_type, target_category
        FROM employee_week_preferences
        WHERE employee_id = ? AND preference_date = ?
        """,
        (employee_id, date_string),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    normalized = []
    for row in rows:
        request_type = row.get("request_type")
        target_category = row.get("target_category")
        preference_type = row.get("preference_type") or ""
        if not request_type:
            if preference_type == "off_day":
                request_type = "day_off"
            elif preference_type == "vacation":
                request_type = "vacation"
            elif preference_type.startswith("not_"):
                request_type = "exclude_shift"
                target_category = preference_type.removeprefix("not_")
            elif preference_type.startswith("only_"):
                request_type = "request_shift"
                target_category = preference_type.removeprefix("only_")
        normalized.append({
            "preference_type": preference_type,
            "request_type": request_type,
            "target_category": target_category,
        })
    return normalized


def week_preferences_allow_category(preferences: list[dict], category: str) -> bool:
    if any(item["request_type"] in {"day_off", "vacation"} for item in preferences):
        return False
    if any(item["request_type"] == "exclude_shift" and item["target_category"] == category for item in preferences):
        return False
    return True


def weekly_shift_request_penalty(connection, employee_id: int, date_string: str, category: str) -> int:
    preferences = get_week_preferences(connection, employee_id, date_string)
    requested_categories = {
        item["target_category"]
        for item in preferences
        if item["request_type"] == "request_shift" and item["target_category"]
    }
    if not requested_categories:
        return 0
    if category in requested_categories:
        return -250
    return 120


def normalize_preference_request(preference_type: str | None, request_type: str | None, target_category: str | None) -> list[dict]:
    preference_type = preference_type or ""
    if preference_type == "off_day" and (not target_category or request_type == "request_shift"):
        request_type = "day_off"
    elif preference_type == "vacation" and (not target_category or request_type == "request_shift"):
        request_type = "vacation"
    elif preference_type == "no_morning_evening_combo" and (not target_category or request_type == "request_shift"):
        request_type = "no_morning_evening_combo"
    elif preference_type.startswith("not_") and request_type == "request_shift" and not target_category:
        request_type = "exclude_shift"
        target_category = preference_type.removeprefix("not_")
    if not request_type:
        if preference_type == "off_day":
            request_type = "day_off"
        elif preference_type == "vacation":
            request_type = "vacation"
        elif preference_type == "no_morning_evening_combo":
            request_type = "no_morning_evening_combo"
        elif preference_type.startswith("not_"):
            request_type = "exclude_shift"
            target_category = preference_type.removeprefix("not_")
        elif preference_type.startswith("only_"):
            target_category = preference_type.removeprefix("only_")
            requests = [{
                "preference_type": f"only_{target_category}",
                "request_type": "request_shift",
                "target_category": target_category,
            }]
            requests.extend(
                {
                    "preference_type": f"not_{other_category}",
                    "request_type": "exclude_shift",
                    "target_category": other_category,
                }
                for other_category in ("morning", "evening", "night")
                if other_category != target_category
            )
            return requests
    if request_type == "request_shift" and not target_category and preference_type.startswith("only_"):
        target_category = preference_type.removeprefix("only_")
    if request_type == "exclude_shift" and not target_category and preference_type.startswith("not_"):
        target_category = preference_type.removeprefix("not_")
    return [{
        "preference_type": preference_type,
        "request_type": request_type,
        "target_category": target_category,
    }]


def get_recurring_preferences(connection, employee_id: int, date_string: str, preference_kind: str) -> list[dict]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT preference_type, request_type, target_category
        FROM employee_recurring_preferences
        WHERE employee_id = ? AND preference_kind = ? AND day_of_week = ?
        """,
        (employee_id, preference_kind, schedule_time.recurring_day_of_week(date_string)),
    )
    preferences = []
    seen = set()
    for row in cursor.fetchall():
        row_dict = dict(row)
        for normalized in normalize_preference_request(
            row_dict.get("preference_type"),
            row_dict.get("request_type"),
            row_dict.get("target_category"),
        ):
            if not normalized["request_type"]:
                continue
            key = (normalized["request_type"], normalized["target_category"])
            if key in seen:
                continue
            seen.add(key)
            preferences.append(normalized)
    return preferences


def get_recurring_preference(connection, employee_id: int, date_string: str, preference_kind: str) -> str:
    preferences = get_recurring_preferences(connection, employee_id, date_string, preference_kind)
    if any(item["request_type"] in {"day_off", "vacation"} for item in preferences):
        blocker = next(item["request_type"] for item in preferences if item["request_type"] in {"day_off", "vacation"})
        return "off_day" if blocker == "day_off" else blocker
    if any(item["request_type"] == "no_morning_evening_combo" for item in preferences):
        return "no_morning_evening_combo"
    excluded = [item["target_category"] for item in preferences if item["request_type"] == "exclude_shift"]
    requested = [item["target_category"] for item in preferences if item["request_type"] == "request_shift"]
    if len(requested) == 1 and set(excluded) == {"morning", "evening", "night"} - {requested[0]}:
        return f"only_{requested[0]}"
    if len(excluded) == 1 and not requested:
        return f"not_{excluded[0]}"
    return "no_preference"


def preference_allows_category(preference_type: str, category: str) -> bool:
    if preference_type in ("no_preference", "no_morning_evening_combo"):
        return True
    if preference_type in ("off_day", "vacation"):
        return False
    if preference_type.startswith("only_"):
        return preference_type == f"only_{category}"
    if preference_type == f"not_{category}":
        return False
    return True


def recurring_preferences_allow_category(preferences: list[dict], category: str) -> bool:
    if any(item["request_type"] in {"day_off", "vacation"} for item in preferences):
        return False
    if any(item["request_type"] == "exclude_shift" and item["target_category"] == category for item in preferences):
        return False
    return True


def recurring_requested_categories(preferences: list[dict]) -> set[str]:
    return {
        item["target_category"]
        for item in preferences
        if item["request_type"] == "request_shift" and item["target_category"]
    }


def strict_recurring_preference_penalty(
    connection,
    employee_id: int,
    date_string: str,
    assignment_templates: list[dict],
) -> int:
    preferences = get_recurring_preferences(connection, employee_id, date_string, "strict")
    requested_categories = recurring_requested_categories(preferences)
    if not requested_categories or not assignment_templates:
        return 0

    penalty = 0
    for template in assignment_templates:
        category = template["category"]
        penalty += -app_constants.STRICT_REQUEST_MATCH_BONUS if category in requested_categories else app_constants.STRICT_REQUEST_MISMATCH_PENALTY
    return penalty


def soft_recurring_preference_penalty(
    connection,
    employee_id: int,
    date_string: str,
    assignment_templates: list[dict],
    projected_entries: list[dict] | None = None,
) -> int:
    preferences = get_recurring_preferences(connection, employee_id, date_string, "soft")
    if not preferences or not assignment_templates:
        return 0
    if any(item["request_type"] in {"day_off", "vacation"} for item in preferences):
        return app_constants.SOFT_DAY_OFF_PENALTY

    penalty = 0
    assignment_categories = [template["category"] for template in assignment_templates]
    requested_categories = recurring_requested_categories(preferences)
    for category in assignment_categories:
        if not recurring_preferences_allow_category(preferences, category):
            penalty += app_constants.SOFT_PREFERENCE_PENALTY
        if requested_categories:
            penalty += -250 if category in requested_categories else 120

    if any(item["request_type"] == "no_morning_evening_combo" for item in preferences):
        projected_categories = set(assignment_categories)
        projected_categories.update(services_schedule_queries.entry_category(entry) for entry in (projected_entries or []))
        if "morning" in projected_categories and "evening" in projected_categories:
            penalty += app_constants.SOFT_COMBO_PENALTY

    return penalty


def get_employee_day_status(connection, employee_id: int, date_string: str):
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT status_type
        FROM employee_day_statuses
        WHERE employee_id = ? AND date = ?
        """,
        (employee_id, date_string),
    )
    return cursor.fetchone()


def get_general_preference(connection, employee_id: int) -> dict:
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM employee_preferences WHERE employee_id = ?", (employee_id,))
    row = cursor.fetchone()
    if not row:
        return {
            "allow_morning": True,
            "allow_evening": True,
            "allow_night": True,
            "allow_morning_evening_combo": True,
        }
    return {
        "allow_morning": bool(row["allow_morning"]),
        "allow_evening": bool(row["allow_evening"]),
        "allow_night": bool(row["allow_night"]),
        "allow_morning_evening_combo": bool(row["allow_morning_evening_combo"]),
    }


def category_allowed_by_preferences(connection, employee: dict, date_string: str, category: str) -> bool:
    if category == "night" and not employee["can_work_night"]:
        return False
    if services_common.is_weekend(date_string) and not employee["can_work_weekends"]:
        return False

    general = get_general_preference(connection, employee["id"])
    if category == "morning" and not general["allow_morning"]:
        return False
    if category == "evening" and not general["allow_evening"]:
        return False
    if category == "night" and not general["allow_night"]:
        return False

    weekly = get_week_preference(connection, employee["id"], date_string)
    if not week_preferences_allow_category(get_week_preferences(connection, employee["id"], date_string), category):
        return False

    strict_recurring_preferences = get_recurring_preferences(connection, employee["id"], date_string, "strict")
    if not recurring_preferences_allow_category(strict_recurring_preferences, category):
        return False
    return True
