"""Scheduling: interval for ShiftCare."""
from __future__ import annotations

from shiftcare import config as app_constants
from shiftcare.scheduling import candidates as scheduling_candidates
from shiftcare.scheduling import coverage as scheduling_coverage
from shiftcare.scheduling import feasibility as scheduling_feasibility
from shiftcare.services import schedule as services_schedule

def fill_week_by_interval_coverage(
    connection,
    cursor,
    employees: list[dict],
    templates: list[dict],
    requirements: list[dict],
    position_id: int,
    week_start_date: str,
    week_dates: list[str],
    created_entries: list[dict],
    errors: list[str],
    unfilled_reports: list[dict],
    generation_mode: str = app_constants.GENERATION_MODE_BALANCED,
):
    slots = scheduling_coverage.build_atomic_slots(requirements, templates)
    if not slots:
        errors.append("No active coverage slots for this week")
        return

    guard = 0
    while guard < 1500:
        guard += 1
        queue = scheduling_feasibility.build_week_shortage_queue(
            connection,
            employees,
            templates,
            position_id,
            week_start_date,
            week_dates,
            slots,
        )
        if not queue:
            break

        assigned = False
        for shortage in queue:
            current_entries = services_schedule.get_schedule_entries(connection, position_id=position_id, dates=[shortage["date"]])
            for fatigue_relaxation in (0, 1):
                candidate = scheduling_candidates.choose_best_interval_candidate(
                    connection=connection,
                    employees=employees,
                    templates=templates,
                    position_id=position_id,
                    date_string=shortage["date"],
                    week_start_date=week_start_date,
                    current_entries=current_entries,
                    slots=slots,
                    fatigue_relaxation=fatigue_relaxation,
                    target_slot=shortage["slot"],
                    generation_mode=generation_mode,
                )
                if candidate is None:
                    continue

                employee, assignment_templates, _score = candidate
                scheduling_candidates.insert_generated_assignment(cursor, employee, position_id, shortage["date"], assignment_templates, created_entries)
                if fatigue_relaxation == 1:
                    errors.append(f"{shortage['date']}: emergency fatigue relaxation was used to cover a slot")
                assigned = True
                break

            if assigned:
                break

        if not assigned:
            break

    for date_string in week_dates:
        final_entries = services_schedule.get_schedule_entries(connection, position_id=position_id, dates=[date_string])
        for slot in slots:
            total, female, male = scheduling_coverage.count_slot_coverage(final_entries, slot)
            if total < slot["required_total"] or female < slot["required_female_min"] or male < slot["required_male_min"]:
                unfilled_reports.append(scheduling_coverage.build_interval_underfilled_report(
                    connection,
                    employees,
                    templates,
                    position_id,
                    week_start_date,
                    date_string,
                    slot,
                    total,
                    female,
                    male,
                ))
                errors.append(scheduling_coverage.build_interval_underfilled_message(
                    connection,
                    employees,
                    templates,
                    position_id,
                    week_start_date,
                    date_string,
                    slot,
                    total,
                    female,
                    male,
                ))


def fill_day_by_interval_coverage(
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
    slots = scheduling_coverage.build_atomic_slots(requirements, templates)
    if not slots:
        errors.append(f"No active coverage slots for {date_string}")
        return

    guard = 0
    while guard < 200:
        guard += 1
        current_entries = services_schedule.get_schedule_entries(connection, position_id=position_id, dates=[date_string])
        if scheduling_coverage.coverage_shortage(current_entries, slots) == 0:
            break
        candidate = None
        for fatigue_relaxation in (0, 1):
            candidate = scheduling_candidates.choose_best_interval_candidate(
                connection=connection,
                employees=employees,
                templates=templates,
                position_id=position_id,
                date_string=date_string,
                week_start_date=week_start_date,
                current_entries=current_entries,
                slots=slots,
                fatigue_relaxation=fatigue_relaxation,
                generation_mode=generation_mode,
            )
            if candidate is not None:
                if fatigue_relaxation == 1:
                    errors.append(f"{date_string}: emergency fatigue relaxation was used to cover a slot")
                break
        if candidate is None:
            break
        employee, assignment_templates, _score = candidate
        scheduling_candidates.insert_generated_assignment(cursor, employee, position_id, date_string, assignment_templates, created_entries)

    final_entries = services_schedule.get_schedule_entries(connection, position_id=position_id, dates=[date_string])
    remaining = scheduling_coverage.coverage_shortage(final_entries, slots)
    if remaining > 0:
        for slot in slots:
            total, female, male = scheduling_coverage.count_slot_coverage(final_entries, slot)
            if total < slot["required_total"] or female < slot["required_female_min"] or male < slot["required_male_min"]:
                unfilled_reports.append(scheduling_coverage.build_interval_underfilled_report(
                    connection,
                    employees,
                    templates,
                    position_id,
                    week_start_date,
                    date_string,
                    slot,
                    total,
                    female,
                    male,
                ))
                errors.append(scheduling_coverage.build_interval_underfilled_message(
                    connection,
                    employees,
                    templates,
                    position_id,
                    week_start_date,
                    date_string,
                    slot,
                    total,
                    female,
                    male,
                ))
