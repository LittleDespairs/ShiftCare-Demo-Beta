"""Scheduling: legacy for ShiftCare."""
from __future__ import annotations

from shiftcare import config as app_constants
from shiftcare.scheduling import candidates as scheduling_candidates
from shiftcare.scheduling import coverage as scheduling_coverage
from shiftcare.scheduling import optimization as scheduling_optimization
from shiftcare.scheduling import previews as scheduling_previews
from shiftcare.scheduling import ranking as scheduling_ranking
from shiftcare.scheduling import rules as scheduling_rules
from shiftcare.scheduling import settings as scheduling_settings
from shiftcare.services import preferences as services_preferences
from shiftcare.services import schedule as services_schedule
from shiftcare.services import schedule_queries as services_schedule_queries

def fill_day_by_legacy_categories(
    connection,
    cursor,
    employees: list[dict],
    templates: list[dict],
    requirements: list[dict],
    position_id: int,
    week_start_date: str,
    date_string: str,
    created_entries: list[dict],
    errors: list[str],
    unfilled_reports: list[dict],
    generation_mode: str = app_constants.GENERATION_MODE_BALANCED,
):
    app_settings = scheduling_settings.get_generation_app_settings(connection, position_id, generation_mode)
    for requirement in requirements:
        category = requirement["shift_category"]
        category_templates = [template for template in templates if template["category"] == category]
        while True:
            entries = [
                entry for entry in services_schedule.get_schedule_entries(connection, position_id=position_id, dates=[date_string])
                if entry["shift_category"] == category
            ]
            female_count = sum(1 for entry in entries if entry["employee_sex"] == "female")
            male_count = sum(1 for entry in entries if entry["employee_sex"] == "male")
            if (
                len(entries) >= requirement["required_total"]
                and female_count >= requirement["required_female_min"]
                and male_count >= requirement["required_male_min"]
            ):
                break

            require_female = female_count < requirement["required_female_min"]
            require_male = male_count < requirement["required_male_min"]
            candidates = []
            for fatigue_relaxation in (0, 1):
                for employee in employees:
                    if require_female and employee["sex"] != "female":
                        continue
                    if require_male and employee["sex"] != "male":
                        continue
                    for template in category_templates:
                        if scheduling_rules.can_employee_take_template(
                            connection,
                            employee,
                            position_id,
                            date_string,
                            template,
                            week_start_date,
                            fatigue_relaxation=fatigue_relaxation,
                        ):
                            fatigue_penalty = scheduling_rules.get_fatigue_penalty(connection, employee["id"], date_string, template)
                            preview = scheduling_previews.create_entry_preview(employee, position_id, date_string, template)
                            projected_entries = [
                                *services_schedule_queries.get_employee_entries_for_date(connection, employee["id"], date_string),
                                preview,
                            ]
                            soft_preference_penalty = services_preferences.strict_recurring_preference_penalty(
                                connection,
                                employee["id"],
                                date_string,
                                [template],
                            )
                            soft_preference_penalty += services_preferences.soft_recurring_preference_penalty(
                                connection,
                                employee["id"],
                                date_string,
                                [template],
                                projected_entries,
                            )
                            soft_preference_penalty += services_preferences.weekly_shift_request_penalty(
                                connection,
                                employee["id"],
                                date_string,
                                template["category"],
                            )
                            projected_same_category_count, projected_same_category_streak = scheduling_optimization.get_projected_category_metrics(
                                connection,
                                employee,
                                week_start_date,
                                [preview],
                                [template["category"]],
                            )
                            projected_night_count, projected_split_count = scheduling_optimization.get_projected_assignment_counts(
                                connection,
                                employee,
                                week_start_date,
                                [preview],
                            )
                            projected_balance = scheduling_optimization.get_projected_assignment_score(
                                connection,
                                employee,
                                week_start_date,
                                [preview],
                                app_settings,
                            )
                            candidates.append((
                                scheduling_ranking.legacy_generation_sort_key(
                                    generation_mode,
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
                                template,
                            ))
                if candidates:
                    if fatigue_relaxation == 1:
                        errors.append(f"{date_string} {category}: emergency fatigue relaxation was used to cover a slot")
                    break
            if not candidates:
                report = scheduling_coverage.build_legacy_underfilled_report(
                    connection,
                    employees,
                    templates,
                    position_id,
                    week_start_date,
                    date_string,
                    requirement,
                    len(entries),
                    female_count,
                    male_count,
                )
                unfilled_reports.append(report)
                errors.append(
                    f"{date_string} {category} underfilled: staff {len(entries)}/{requirement['required_total']}, "
                    f"women {female_count}/{requirement['required_female_min']}, "
                    f"men {male_count}/{requirement['required_male_min']}. "
                    f"Reasons: {report['reasons']}"
                )
                break
            candidates.sort()
            _, employee, template = candidates[0]
            scheduling_candidates.insert_generated_entry(cursor, employee, position_id, date_string, template, created_entries)
