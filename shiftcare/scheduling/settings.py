"""Scheduling: settings for ShiftCare."""
from __future__ import annotations

from shiftcare import config as app_constants
import app_settings_service

def normalize_generation_mode(generation_mode: str | None) -> str:
    if generation_mode in app_constants.GENERATION_MODES:
        return generation_mode
    return app_constants.GENERATION_MODE_BALANCED


def scale_int(value: int, numerator: int, denominator: int = 100) -> int:
    return int(round(value * numerator / denominator))


def apply_generation_mode_settings(settings: dict, generation_mode: str | None) -> dict:
    mode = normalize_generation_mode(generation_mode)
    effective = dict(settings)
    if mode == app_constants.GENERATION_MODE_COVERAGE:
        effective["coverage_shortage_gain_weight"] = scale_int(effective["coverage_shortage_gain_weight"], 180)
        effective["coverage_overage_penalty_weight"] = scale_int(effective["coverage_overage_penalty_weight"], 70)
        for key in (
            "balance_missing_min_weight",
            "balance_target_distance_weight",
            "balance_over_target_weight",
            "balance_worked_day_weight",
            "balance_night_weight",
            "balance_split_weight",
            "balance_consecutive_night_weight",
            "balance_consecutive_split_weight",
        ):
            effective[key] = scale_int(effective[key], 45)
    elif mode == app_constants.GENERATION_MODE_REQUESTS:
        effective["coverage_shortage_gain_weight"] = max(1, scale_int(effective["coverage_shortage_gain_weight"], 85))
        for key in (
            "balance_missing_min_weight",
            "balance_target_distance_weight",
            "balance_over_target_weight",
            "balance_worked_day_weight",
            "balance_night_weight",
            "balance_split_weight",
            "balance_consecutive_night_weight",
            "balance_consecutive_split_weight",
        ):
            effective[key] = scale_int(effective[key], 60)
    return effective


def get_generation_app_settings(connection, position_id: int, generation_mode: str | None) -> dict:
    return apply_generation_mode_settings(
        app_settings_service.get_position_app_settings(connection, position_id),
        generation_mode,
    )
