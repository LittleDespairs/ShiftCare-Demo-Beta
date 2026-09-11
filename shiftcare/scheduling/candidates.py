"""Scheduling: candidates for ShiftCare."""
from __future__ import annotations

from shiftcare import config as app_constants
from shiftcare.scheduling import coverage as scheduling_coverage
from shiftcare.scheduling import optimization as scheduling_optimization
from shiftcare.scheduling import previews as scheduling_previews
from shiftcare.scheduling import ranking as scheduling_ranking
from shiftcare.scheduling import rules as scheduling_rules
from shiftcare.scheduling import settings as scheduling_settings
from shiftcare.services import preferences as services_preferences
import schedule_time

def template_start_minutes(template: dict) -> int:
    return schedule_time.time_to_minutes(template["start_time"])


def choose_best_interval_candidate(
    connection,
    employees: list[dict],
    templates: list[dict],
    position_id: int,
    date_string: str,
    week_start_date: str,
    current_entries: list[dict],
    slots: list[dict],
    fatigue_relaxation: int = 0,
    target_slot: dict | None = None,
    generation_mode: str = app_constants.GENERATION_MODE_BALANCED,
):
    app_settings = scheduling_settings.get_generation_app_settings(connection, position_id, generation_mode)
    baseline_shortage = scheduling_coverage.coverage_shortage(current_entries, slots)
    baseline_overage = scheduling_coverage.coverage_overage(current_entries, slots)
    baseline_target_shortage = scheduling_coverage.slot_shortage_score(current_entries, target_slot) if target_slot is not None else 0
    target_needs_female = False
    target_needs_male = False
    target_needs_total = False
    if target_slot is not None:
        target_total, target_female, target_male = scheduling_coverage.count_slot_coverage(current_entries, target_slot)
        target_needs_total = target_total < target_slot["required_total"]
        target_needs_female = target_female < target_slot["required_female_min"]
        target_needs_male = target_male < target_slot["required_male_min"]
    candidates = []

    for employee in employees:
        if target_slot is not None and not target_needs_total:
            if target_needs_female and employee["sex"] != "female":
                continue
            if target_needs_male and employee["sex"] != "male":
                continue
        for template in templates:
            if target_slot is not None and not scheduling_coverage.template_covers_slot(template, target_slot):
                continue
            for assignment_templates in scheduling_previews.build_template_assignment_options(template, templates):
                previews = scheduling_previews.build_valid_assignment_previews(
                    connection,
                    employee,
                    assignment_templates,
                    position_id,
                    date_string,
                    week_start_date,
                    fatigue_relaxation=fatigue_relaxation,
                )
                if previews is None:
                    continue

                projected_entries = [*current_entries, *previews]
                shortage_gain = baseline_shortage - scheduling_coverage.coverage_shortage(projected_entries, slots)
                overage_cost = scheduling_coverage.coverage_overage(projected_entries, slots) - baseline_overage
                target_shortage_gain = (
                    baseline_target_shortage - scheduling_coverage.slot_shortage_score(projected_entries, target_slot)
                    if target_slot is not None
                    else 0
                )
                score = (
                    shortage_gain * app_settings["coverage_shortage_gain_weight"]
                    - overage_cost * app_settings["coverage_overage_penalty_weight"]
                )
                if target_slot is not None:
                    if target_needs_female and employee["sex"] == "female":
                        score += app_settings["target_gender_bonus_weight"]
                    if target_needs_male and employee["sex"] == "male":
                        score += app_settings["target_gender_bonus_weight"]
                    if (target_needs_female and employee["sex"] != "female") or (target_needs_male and employee["sex"] != "male"):
                        score -= app_settings["wrong_gender_penalty_weight"]
                if target_slot is not None:
                    if target_shortage_gain <= 0:
                        continue
                elif score <= 0:
                    continue

                soft_preference_penalty = services_preferences.strict_recurring_preference_penalty(
                    connection,
                    employee["id"],
                    date_string,
                    assignment_templates,
                )
                soft_preference_penalty += services_preferences.soft_recurring_preference_penalty(
                    connection,
                    employee["id"],
                    date_string,
                    assignment_templates,
                    projected_entries,
                )
                soft_preference_penalty += sum(
                    services_preferences.weekly_shift_request_penalty(connection, employee["id"], date_string, assignment_template["category"])
                    for assignment_template in assignment_templates
                )
                fatigue_penalty = sum(
                    scheduling_rules.get_fatigue_penalty(connection, employee["id"], date_string, assignment_template)
                    for assignment_template in assignment_templates
                )
                projected_same_category_count, projected_same_category_streak = scheduling_optimization.get_projected_category_metrics(
                    connection,
                    employee,
                    week_start_date,
                    previews,
                    [assignment_template["category"] for assignment_template in assignment_templates],
                )
                projected_night_count, projected_split_count = scheduling_optimization.get_projected_assignment_counts(
                    connection,
                    employee,
                    week_start_date,
                    previews,
                )
                projected_balance = scheduling_optimization.get_projected_assignment_score(
                    connection,
                    employee,
                    week_start_date,
                    previews,
                    app_settings,
                )
                candidates.append((
                    scheduling_ranking.interval_generation_sort_key(
                        generation_mode,
                        target_shortage_gain,
                        score,
                        overage_cost,
                        soft_preference_penalty,
                        fatigue_penalty,
                        projected_same_category_count,
                        projected_same_category_streak,
                        projected_night_count,
                        projected_split_count,
                        projected_balance,
                        scheduling_ranking.candidate_assignment_priority(employee),
                        scheduling_ranking.candidate_priority(connection, employee, date_string, week_start_date),
                    ),
                    employee,
                    assignment_templates,
                    score,
                ))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1], candidates[0][2], candidates[0][3]


def insert_generated_entry(cursor, employee: dict, position_id: int, date_string: str, template: dict, created_entries: list[dict]):
    cursor.execute("SELECT organization_id FROM positions WHERE id = ?", (position_id,))
    position_row = cursor.fetchone()
    organization_id = int(position_row["organization_id"]) if position_row else 1
    cursor.execute(
        """
        INSERT INTO schedule_entries (organization_id, employee_id, position_id, date, shift_template_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (organization_id, employee["id"], position_id, date_string, template["id"]),
    )
    created_entries.append(
        {
            "id": cursor.lastrowid,
            "employee_id": employee["id"],
            "employee_name": employee["full_name"],
            "date": date_string,
            "shift_template_name": template["name"],
            "shift_category": template["category"],
        }
    )


def insert_generated_assignment(cursor, employee: dict, position_id: int, date_string: str, templates: list[dict], created_entries: list[dict]):
    for template in templates:
        insert_generated_entry(cursor, employee, position_id, date_string, template, created_entries)
