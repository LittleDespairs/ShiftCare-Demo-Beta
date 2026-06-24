from __future__ import annotations

import sqlite3


def _has_column(row: sqlite3.Row, key: str) -> bool:
    return key in row.keys()


def row_to_employee_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "public_id": row["public_id"] if _has_column(row, "public_id") else None,
        "id_card": row["id_card"] if _has_column(row, "id_card") else None,
        "full_name": row["full_name"],
        "sex": row["sex"],
        "min_shifts_per_week": row["min_shifts_per_week"],
        "target_shifts_per_week": row["target_shifts_per_week"],
        "max_shifts_per_week": row["max_shifts_per_week"],
        "can_work_night": bool(row["can_work_night"]),
        "can_work_weekends": bool(row["can_work_weekends"]),
        "can_work_evenings_after_night": bool(row["can_work_evenings_after_night"]),
        "can_work_mornings_and_evenings": bool(row["can_work_mornings_and_evenings"]),
    }


def row_to_department_dict(row: sqlite3.Row) -> dict:
    item = {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"] if _has_column(row, "description") else None,
        "display_order": row["display_order"] if _has_column(row, "display_order") else 0,
        "is_active": bool(row["is_active"]) if _has_column(row, "is_active") else True,
    }
    if _has_column(row, "public_id"):
        item["public_id"] = row["public_id"]
    return item


def row_to_position_dict(row: sqlite3.Row) -> dict:
    item = {
        "id": row["id"],
        "department_id": row["department_id"] if _has_column(row, "department_id") else None,
        "department_public_id": row["department_public_id"] if _has_column(row, "department_public_id") else None,
        "department_name": row["department_name"] if _has_column(row, "department_name") else None,
        "name": row["name"],
        "color": row["color"] if _has_column(row, "color") and row["color"] else "#eff6ff",
        "requires_continuous_coverage": bool(row["requires_continuous_coverage"]),
        "minimum_staff_presence": row["minimum_staff_presence"],
        "allow_same_day_other_positions": bool(row["allow_same_day_other_positions"])
        if _has_column(row, "allow_same_day_other_positions")
        else False,
        "max_consecutive_nights": row["max_consecutive_nights"] if _has_column(row, "max_consecutive_nights") else None,
        "emergency_max_consecutive_nights": row["emergency_max_consecutive_nights"]
        if _has_column(row, "emergency_max_consecutive_nights")
        else None,
        "max_consecutive_split_days": row["max_consecutive_split_days"]
        if _has_column(row, "max_consecutive_split_days")
        else None,
        "emergency_max_consecutive_split_days": row["emergency_max_consecutive_split_days"]
        if _has_column(row, "emergency_max_consecutive_split_days")
        else None,
    }
    if _has_column(row, "public_id"):
        item["public_id"] = row["public_id"]
    if _has_column(row, "is_primary"):
        item["is_primary"] = bool(row["is_primary"])
    if _has_column(row, "priority_score"):
        item["priority_score"] = row["priority_score"]
    if _has_column(row, "is_fallback_only"):
        item["is_fallback_only"] = bool(row["is_fallback_only"])
    return item


def row_to_shift_template_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "public_id": row["public_id"] if _has_column(row, "public_id") else None,
        "position_id": row["position_id"] if _has_column(row, "position_id") else None,
        "position_public_id": row["position_public_id"] if _has_column(row, "position_public_id") else None,
        "position_name": row["position_name"] if _has_column(row, "position_name") else None,
        "department_id": row["department_id"] if _has_column(row, "department_id") else None,
        "department_name": row["department_name"] if _has_column(row, "department_name") else None,
        "name": row["name"],
        "category": row["category"],
        "start_time": row["start_time"],
        "end_time": row["end_time"],
        "is_overnight": bool(row["is_overnight"]),
        "is_active": bool(row["is_active"]),
        "is_split_only": bool(row["is_split_only"]),
    }


def row_to_coverage_requirement_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "public_id": row["public_id"] if _has_column(row, "public_id") else None,
        "position_id": row["position_id"],
        "position_public_id": row["position_public_id"] if _has_column(row, "position_public_id") else None,
        "position_name": row["position_name"] if _has_column(row, "position_name") else None,
        "department_id": row["department_id"] if _has_column(row, "department_id") else None,
        "department_name": row["department_name"] if _has_column(row, "department_name") else None,
        "start_time": row["start_time"],
        "end_time": row["end_time"],
        "required_total": row["required_total"],
        "required_female_min": row["required_female_min"],
        "required_male_min": row["required_male_min"],
        "is_overnight": bool(row["is_overnight"]),
    }
