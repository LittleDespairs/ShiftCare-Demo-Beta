from __future__ import annotations

import sqlite3

from schemas import AppSettingsUpdate


MAX_WORK_DAYS_PER_WEEK = 6
MAX_CONSECUTIVE_NIGHTS = 2
EMERGENCY_MAX_CONSECUTIVE_NIGHTS = 3
MAX_CONSECUTIVE_SPLIT_DAYS = 2
EMERGENCY_MAX_CONSECUTIVE_SPLIT_DAYS = 3
MIN_REST_MINUTES_AFTER_NIGHT_BEFORE_EVENING = 8 * 60
MIN_REST_MINUTES_BETWEEN_MORNING_AND_EVENING = 0
MAX_DAILY_WORK_MINUTES = 12 * 60
AFTER_NIGHT_EVENING_PENALTY = 1200
DEFAULT_POSITION_COLOR = "#eff6ff"
DEFAULT_SCHEDULE_COLORS = {
    "schedule_morning_color": "#ecfeff",
    "schedule_evening_color": "#fff7ed",
    "schedule_night_color": "#eef2ff",
    "schedule_status_color": "#f5f3ff",
}

POSITION_GENERATION_LIMIT_FIELDS = (
    "max_consecutive_nights",
    "emergency_max_consecutive_nights",
    "max_consecutive_split_days",
    "emergency_max_consecutive_split_days",
)


def get_app_settings(connection, organization_id: int = 1) -> dict:
    cursor = connection.cursor()
    cursor.execute("SELECT key, value FROM app_settings WHERE organization_id = ?", (organization_id,))
    raw_settings = {row["key"]: row["value"] for row in cursor.fetchall()}

    def read_int(key: str, default: int) -> int:
        try:
            return int(raw_settings.get(key, default))
        except (TypeError, ValueError):
            return default

    def read_bool(key: str, default: bool) -> bool:
        raw_value = raw_settings.get(key)
        if raw_value is None:
            return default
        if isinstance(raw_value, bool):
            return raw_value
        return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}

    def read_color(key: str, default: str) -> str:
        raw_value = str(raw_settings.get(key, default)).strip()
        if len(raw_value) == 7 and raw_value.startswith("#"):
            hex_part = raw_value[1:]
            if all(character in "0123456789abcdefABCDEF" for character in hex_part):
                return raw_value
        return default

    return {
        "min_rest_minutes_between_morning_and_evening": read_int(
            "min_rest_minutes_between_morning_and_evening",
            MIN_REST_MINUTES_BETWEEN_MORNING_AND_EVENING,
        ),
        "min_rest_minutes_after_night_before_evening": read_int(
            "min_rest_minutes_after_night_before_evening",
            MIN_REST_MINUTES_AFTER_NIGHT_BEFORE_EVENING,
        ),
        "max_daily_work_minutes": read_int("max_daily_work_minutes", MAX_DAILY_WORK_MINUTES),
        "schedule_coverage_display_mode": (
            raw_settings.get("schedule_coverage_display_mode")
            if raw_settings.get("schedule_coverage_display_mode") in {"category", "interval"}
            else "interval"
        ),
        "schedule_morning_color": read_color("schedule_morning_color", DEFAULT_SCHEDULE_COLORS["schedule_morning_color"]),
        "schedule_evening_color": read_color("schedule_evening_color", DEFAULT_SCHEDULE_COLORS["schedule_evening_color"]),
        "schedule_night_color": read_color("schedule_night_color", DEFAULT_SCHEDULE_COLORS["schedule_night_color"]),
        "schedule_status_color": read_color("schedule_status_color", DEFAULT_SCHEDULE_COLORS["schedule_status_color"]),
        "allow_multiple_positions_per_day": read_bool("allow_multiple_positions_per_day", False),
        "max_work_days_per_week": read_int("max_work_days_per_week", MAX_WORK_DAYS_PER_WEEK),
        "max_consecutive_nights": read_int("max_consecutive_nights", MAX_CONSECUTIVE_NIGHTS),
        "emergency_max_consecutive_nights": read_int("emergency_max_consecutive_nights", EMERGENCY_MAX_CONSECUTIVE_NIGHTS),
        "max_consecutive_split_days": read_int("max_consecutive_split_days", MAX_CONSECUTIVE_SPLIT_DAYS),
        "emergency_max_consecutive_split_days": read_int("emergency_max_consecutive_split_days", EMERGENCY_MAX_CONSECUTIVE_SPLIT_DAYS),
        "after_night_evening_penalty": read_int("after_night_evening_penalty", AFTER_NIGHT_EVENING_PENALTY),
        "consecutive_night_penalty": read_int("consecutive_night_penalty", 500),
        "consecutive_split_penalty": read_int("consecutive_split_penalty", 450),
        "coverage_shortage_gain_weight": read_int("coverage_shortage_gain_weight", 100),
        "coverage_overage_penalty_weight": read_int("coverage_overage_penalty_weight", 25),
        "target_gender_bonus_weight": read_int("target_gender_bonus_weight", 250),
        "wrong_gender_penalty_weight": read_int("wrong_gender_penalty_weight", 120),
        "balance_missing_min_weight": read_int("balance_missing_min_weight", 300),
        "balance_target_distance_weight": read_int("balance_target_distance_weight", 70),
        "balance_over_target_weight": read_int("balance_over_target_weight", 80),
        "balance_over_max_weight": read_int("balance_over_max_weight", 10000),
        "balance_worked_day_weight": read_int("balance_worked_day_weight", 15),
        "balance_night_weight": read_int("balance_night_weight", 60),
        "balance_split_weight": read_int("balance_split_weight", 55),
        "balance_consecutive_night_weight": read_int("balance_consecutive_night_weight", 120),
        "balance_consecutive_split_weight": read_int("balance_consecutive_split_weight", 100),
        "balance_excess_night_weight": read_int("balance_excess_night_weight", 2000),
        "balance_excess_split_weight": read_int("balance_excess_split_weight", 1800),
    }


def apply_position_generation_limits(settings: dict, position: dict | sqlite3.Row | None) -> dict:
    effective_settings = dict(settings)
    if position is None:
        return effective_settings

    for field in POSITION_GENERATION_LIMIT_FIELDS:
        value = position[field] if isinstance(position, sqlite3.Row) else position.get(field)
        if value is not None:
            effective_settings[field] = int(value)
    return effective_settings


def get_position_app_settings(
    connection,
    position_id: int,
    base_settings: dict | None = None,
    organization_id: int = 1,
) -> dict:
    settings = base_settings or get_app_settings(connection, organization_id=organization_id)
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT max_consecutive_nights, emergency_max_consecutive_nights,
               max_consecutive_split_days, emergency_max_consecutive_split_days
        FROM positions
        WHERE id = ?
        """,
        (position_id,),
    )
    return apply_position_generation_limits(settings, cursor.fetchone())


def save_app_settings(connection, settings: AppSettingsUpdate, organization_id: int = 1) -> None:
    cursor = connection.cursor()
    for key, value in settings.model_dump(exclude_none=True).items():
        cursor.execute(
            """
            INSERT INTO app_settings (organization_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(key)
            DO UPDATE SET organization_id = excluded.organization_id,
                          value = excluded.value
            """,
            (organization_id, key, str(value)),
        )


def reset_visual_color_settings(connection, organization_id: int = 1) -> int:
    cursor = connection.cursor()
    for key, value in DEFAULT_SCHEDULE_COLORS.items():
        cursor.execute(
            """
            INSERT INTO app_settings (organization_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(key)
            DO UPDATE SET organization_id = excluded.organization_id,
                          value = excluded.value
            """,
            (organization_id, key, value),
        )
    cursor.execute("UPDATE positions SET color = ?", (DEFAULT_POSITION_COLOR,))
    return cursor.rowcount
