"""Construct and validate staged assignments without selecting a candidate."""
from __future__ import annotations

from shiftcare.scheduling import rules as scheduling_rules


def create_entry_preview(employee: dict, position_id: int, date_string: str, template: dict) -> dict:
    return {
        "id": -1,
        "employee_id": employee["id"],
        "position_id": position_id,
        "date": date_string,
        "shift_template_id": template["id"],
        "shift_template_name": template["name"],
        "shift_category": template["category"],
        "start_time": template["start_time"],
        "end_time": template["end_time"],
        "is_overnight": template["is_overnight"],
        "is_split_only": template["is_split_only"],
        "employee_name": employee["full_name"],
        "employee_sex": employee["sex"],
    }


def build_template_assignment_options(template: dict, templates: list[dict]) -> list[list[dict]]:
    return [[template]]


def build_valid_assignment_previews(
    connection,
    employee: dict,
    assignment_templates: list[dict],
    position_id: int,
    date_string: str,
    week_start_date: str,
    fatigue_relaxation: int = 0,
) -> list[dict] | None:
    staged_entries: list[dict] = []

    for template in assignment_templates:
        if not scheduling_rules.can_employee_take_template(
            connection,
            employee,
            position_id,
            date_string,
            template,
            week_start_date,
            fatigue_relaxation=fatigue_relaxation,
            staged_entries=staged_entries,
        ):
            return None
        staged_entries.append(create_entry_preview(employee, position_id, date_string, template))

    return staged_entries
