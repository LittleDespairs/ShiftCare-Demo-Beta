"""Scheduling: feasibility for ShiftCare."""
from __future__ import annotations

from shiftcare.scheduling import coverage as scheduling_coverage
from shiftcare.services import schedule as services_schedule

def build_week_shortage_queue(
    connection,
    employees: list[dict],
    templates: list[dict],
    position_id: int,
    week_start_date: str,
    week_dates: list[str],
    slots: list[dict],
) -> list[dict]:
    queue = []
    for date_index, date_string in enumerate(week_dates):
        entries = services_schedule.get_schedule_entries(connection, position_id=position_id, dates=[date_string])
        for slot in slots:
            total, female, male = scheduling_coverage.count_slot_coverage(entries, slot)
            missing_total = max(0, slot["required_total"] - total)
            missing_female = max(0, slot["required_female_min"] - female)
            missing_male = max(0, slot["required_male_min"] - male)
            if missing_total <= 0 and missing_female <= 0 and missing_male <= 0:
                continue

            strict_candidates = scheduling_coverage.count_candidate_options_for_slot(
                connection,
                employees,
                templates,
                position_id,
                date_string,
                week_start_date,
                slot,
                fatigue_relaxation=0,
            )
            emergency_candidates = strict_candidates or scheduling_coverage.count_candidate_options_for_slot(
                connection,
                employees,
                templates,
                position_id,
                date_string,
                week_start_date,
                slot,
                fatigue_relaxation=1,
            )
            scarcity = strict_candidates if strict_candidates > 0 else emergency_candidates + 1000
            queue.append(
                {
                    "date": date_string,
                    "date_index": date_index,
                    "slot": slot,
                    "is_night_slot": slot["start"] >= 23 * 60 or slot["end"] <= 7 * 60 or slot["end"] > 24 * 60,
                    "missing_total": missing_total,
                    "missing_female": missing_female,
                    "missing_male": missing_male,
                    "strict_candidates": strict_candidates,
                    "emergency_candidates": emergency_candidates,
                    "scarcity": scarcity,
                }
            )

    queue.sort(
        key=lambda item: (
            -int(item["is_night_slot"]),
            item["scarcity"],
            -item["date_index"],
            -item["missing_total"],
            -item["missing_female"],
            -item["missing_male"],
            item["slot"]["start"],
        )
    )
    return queue


def build_generation_feasibility_report(
    connection,
    employees: list[dict],
    templates: list[dict],
    coverage_requirements: list[dict],
    legacy_requirements: list[dict],
    position_id: int,
    week_start_date: str,
    week_dates: list[str],
) -> dict:
    issues: list[dict] = []
    employee_count = len(employees)
    female_count = sum(1 for employee in employees if employee["sex"] == "female")
    male_count = sum(1 for employee in employees if employee["sex"] == "male")

    if coverage_requirements:
        slots = scheduling_coverage.build_atomic_slots(coverage_requirements, templates)
        if not slots:
            issues.append({
                "severity": "blocking",
                "kind": "coverage",
                "message": "No active coverage slots can be built from coverage requirements.",
            })

        for slot in slots:
            covering_templates = [template for template in templates if scheduling_coverage.template_covers_slot(template, slot)]
            if not covering_templates:
                issues.append({
                    "severity": "blocking",
                    "kind": "template",
                    "slot": scheduling_coverage.slot_to_report(slot),
                    "message": "No active shift template covers this required interval.",
                })
            if slot["required_total"] > employee_count:
                issues.append({
                    "severity": "blocking",
                    "kind": "staff",
                    "slot": scheduling_coverage.slot_to_report(slot),
                    "message": "Required staff is greater than employees assigned to the position.",
                })
            if slot["required_female_min"] > female_count:
                issues.append({
                    "severity": "blocking",
                    "kind": "female_staff",
                    "slot": scheduling_coverage.slot_to_report(slot),
                    "message": "Required female staff is greater than available female employees.",
                })
            if slot["required_male_min"] > male_count:
                issues.append({
                    "severity": "blocking",
                    "kind": "male_staff",
                    "slot": scheduling_coverage.slot_to_report(slot),
                    "message": "Required male staff is greater than available male employees.",
                })

        for date_string in week_dates:
            for slot in slots:
                strict_candidates = scheduling_coverage.count_candidate_options_for_slot(
                    connection,
                    employees,
                    templates,
                    position_id,
                    date_string,
                    week_start_date,
                    slot,
                    fatigue_relaxation=0,
                )
                emergency_candidates = strict_candidates or scheduling_coverage.count_candidate_options_for_slot(
                    connection,
                    employees,
                    templates,
                    position_id,
                    date_string,
                    week_start_date,
                    slot,
                    fatigue_relaxation=1,
                )
                if emergency_candidates == 0:
                    issues.append({
                        "severity": "blocking",
                        "kind": "candidate",
                        "date": date_string,
                        "slot": scheduling_coverage.slot_to_report(slot),
                        "message": "No eligible employee/template candidate can cover this interval.",
                    })
                elif strict_candidates == 0:
                    issues.append({
                        "severity": "warning",
                        "kind": "emergency_relaxation",
                        "date": date_string,
                        "slot": scheduling_coverage.slot_to_report(slot),
                        "message": "This interval is only coverable with emergency fatigue relaxation.",
                    })
    else:
        for requirement in legacy_requirements:
            category_templates = [template for template in templates if template["category"] == requirement["shift_category"]]
            if not category_templates:
                issues.append({
                    "severity": "blocking",
                    "kind": "template",
                    "shift_category": requirement["shift_category"],
                    "message": "No active template exists for this legacy shift requirement.",
                })
            if requirement["required_total"] > employee_count:
                issues.append({
                    "severity": "blocking",
                    "kind": "staff",
                    "shift_category": requirement["shift_category"],
                    "message": "Required staff is greater than employees assigned to the position.",
                })
            if requirement["required_female_min"] > female_count:
                issues.append({
                    "severity": "blocking",
                    "kind": "female_staff",
                    "shift_category": requirement["shift_category"],
                    "message": "Required female staff is greater than available female employees.",
                })
            if requirement["required_male_min"] > male_count:
                issues.append({
                    "severity": "blocking",
                    "kind": "male_staff",
                    "shift_category": requirement["shift_category"],
                    "message": "Required male staff is greater than available male employees.",
                })

    for issue in issues:
        issue["constraint_type"] = "hard" if issue["severity"] == "blocking" else "soft"

    hard_constraints = [issue for issue in issues if issue["constraint_type"] == "hard"]
    soft_constraints = [issue for issue in issues if issue["constraint_type"] == "soft"]

    return {
        "status": "blocking" if hard_constraints else "ok",
        "issues": issues,
        "hard_constraints": hard_constraints,
        "soft_constraints": soft_constraints,
    }


def format_feasibility_issue(issue: dict) -> str:
    parts = []
    if issue.get("date"):
        parts.append(str(issue["date"]))
    if issue.get("slot"):
        slot = issue["slot"]
        parts.append(f"{slot['start']}-{slot['end']}")
    if issue.get("shift_category"):
        parts.append(str(issue["shift_category"]))

    prefix = " ".join(parts)
    if prefix:
        return f"Pre-check {issue['severity']}: {prefix}: {issue['message']}"
    return f"Pre-check {issue['severity']}: {issue['message']}"
