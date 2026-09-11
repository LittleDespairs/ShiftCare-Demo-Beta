"""Scheduling: coverage for ShiftCare."""
from __future__ import annotations

from shiftcare.scheduling import previews as scheduling_previews
from shiftcare.scheduling import rules as scheduling_rules
import schedule_time

def build_atomic_slots(requirements: list[dict], templates: list[dict]) -> list[dict]:
    points = {0, 24 * 60}
    normalized_requirements = []
    for requirement in requirements:
        interval = schedule_time.build_interval(requirement["start_time"], requirement["end_time"], bool(requirement["is_overnight"]))
        normalized_requirements.append((interval, requirement))
        points.add(interval.start)
        points.add(interval.end)

    for template in templates:
        interval = schedule_time.build_interval(template["start_time"], template["end_time"], template["is_overnight"])
        points.add(interval.start)
        points.add(interval.end)

    sorted_points = sorted(points)
    slots = []
    for index in range(len(sorted_points) - 1):
        start = sorted_points[index]
        end = sorted_points[index + 1]
        if start == end:
            continue
        required_total = 0
        required_female = 0
        required_male = 0
        for interval, requirement in normalized_requirements:
            if interval.contains(start, end):
                required_total = max(required_total, requirement["required_total"])
                required_female = max(required_female, requirement["required_female_min"])
                required_male = max(required_male, requirement["required_male_min"])
        if required_total > 0 or required_female > 0 or required_male > 0:
            slots.append({
                "start": start,
                "end": end,
                "required_total": required_total,
                "required_female_min": required_female,
                "required_male_min": required_male,
            })
    return slots


def count_slot_coverage(entries: list[dict], slot: dict) -> tuple[int, int, int]:
    total = 0
    female = 0
    male = 0
    for entry in entries:
        if entry.get("no_show"):
            continue
        interval = schedule_time.build_interval(entry["start_time"], entry["end_time"], bool(entry["is_overnight"]))
        if interval.contains(slot["start"], slot["end"]):
            total += 1
            if entry.get("employee_sex") == "female":
                female += 1
            if entry.get("employee_sex") == "male":
                male += 1
    return total, female, male


def coverage_shortage(entries: list[dict], slots: list[dict]) -> int:
    shortage = 0
    for slot in slots:
        total, female, male = count_slot_coverage(entries, slot)
        shortage += max(0, slot["required_total"] - total) * 10
        shortage += max(0, slot["required_female_min"] - female) * 4
        shortage += max(0, slot["required_male_min"] - male) * 4
    return shortage


def coverage_overage(entries: list[dict], slots: list[dict]) -> int:
    overage = 0
    for slot in slots:
        total, _female, _male = count_slot_coverage(entries, slot)
        overage += max(0, total - slot["required_total"])
    return overage


def slot_shortage_score(entries: list[dict], slot: dict) -> int:
    total, female, male = count_slot_coverage(entries, slot)
    return (
        max(0, slot["required_total"] - total) * 10
        + max(0, slot["required_female_min"] - female) * 4
        + max(0, slot["required_male_min"] - male) * 4
    )


def template_covers_slot(template: dict, slot: dict) -> bool:
    interval = schedule_time.build_interval(template["start_time"], template["end_time"], template["is_overnight"])
    return interval.contains(slot["start"], slot["end"])


def count_candidate_options_for_slot(
    connection,
    employees: list[dict],
    templates: list[dict],
    position_id: int,
    date_string: str,
    week_start_date: str,
    slot: dict,
    fatigue_relaxation: int = 0,
) -> int:
    count = 0
    for employee in employees:
        for template in templates:
            if not template_covers_slot(template, slot):
                continue
            if any(
                scheduling_previews.build_valid_assignment_previews(
                    connection,
                    employee,
                    assignment_templates,
                    position_id,
                    date_string,
                    week_start_date,
                    fatigue_relaxation=fatigue_relaxation,
                )
                is not None
                for assignment_templates in scheduling_previews.build_template_assignment_options(template, templates)
            ):
                count += 1
    return count


def format_slot_time(slot: dict) -> str:
    return f"{slot['start'] // 60:02d}:{slot['start'] % 60:02d}-{slot['end'] // 60 % 24:02d}:{slot['end'] % 60:02d}"


def slot_to_report(slot: dict) -> dict:
    return {
        "start": f"{slot['start'] // 60:02d}:{slot['start'] % 60:02d}",
        "end": f"{slot['end'] // 60 % 24:02d}:{slot['end'] % 60:02d}",
        "required_total": slot["required_total"],
        "required_female_min": slot["required_female_min"],
        "required_male_min": slot["required_male_min"],
    }


def summarize_reasons(reason_counts: dict[str, int], limit: int = 4) -> str:
    if not reason_counts:
        return "no available employees found"
    ordered = sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))
    return "; ".join(f"{reason} ({count})" for reason, count in ordered[:limit])


def explain_unfilled_interval_slot(
    connection,
    employees: list[dict],
    templates: list[dict],
    position_id: int,
    date_string: str,
    week_start_date: str,
    slot: dict,
    require_female: bool = False,
    require_male: bool = False,
) -> str:
    covering_templates = [template for template in templates if template_covers_slot(template, slot)]
    if not covering_templates:
        return "no active shift template covers this time interval"

    reason_counts: dict[str, int] = {}
    for employee in employees:
        if require_female and employee["sex"] != "female":
            reason_counts["not enough female employees available"] = reason_counts.get("not enough female employees available", 0) + 1
            continue
        if require_male and employee["sex"] != "male":
            reason_counts["not enough male employees available"] = reason_counts.get("not enough male employees available", 0) + 1
            continue

        employee_had_relevant_template = False
        for template in covering_templates:
            for assignment_templates in scheduling_previews.build_template_assignment_options(template, templates):
                staged_entries: list[dict] = []
                option_reason = None
                for assignment_template in assignment_templates:
                    reason = scheduling_rules.explain_employee_template_rejection(
                        connection,
                        employee,
                        position_id,
                        date_string,
                        assignment_template,
                        week_start_date,
                        fatigue_relaxation=1,
                        staged_entries=staged_entries,
                    )
                    if reason:
                        option_reason = reason
                        break
                    staged_entries.append(scheduling_previews.create_entry_preview(employee, position_id, date_string, assignment_template))

                if option_reason is None:
                    employee_had_relevant_template = True
                    break
                reason_counts[option_reason] = reason_counts.get(option_reason, 0) + 1

            if employee_had_relevant_template:
                break

    if not reason_counts:
        return "candidates existed, but they did not improve coverage without overfilling other intervals"

    return summarize_reasons(reason_counts)


def build_interval_underfilled_message(
    connection,
    employees: list[dict],
    templates: list[dict],
    position_id: int,
    week_start_date: str,
    date_string: str,
    slot: dict,
    total: int,
    female: int,
    male: int,
) -> str:
    require_female = female < slot["required_female_min"]
    require_male = male < slot["required_male_min"]
    reasons = explain_unfilled_interval_slot(
        connection,
        employees,
        templates,
        position_id,
        date_string,
        week_start_date,
        slot,
        require_female=require_female,
        require_male=require_male,
    )
    return (
        f"{date_string} {format_slot_time(slot)} underfilled: "
        f"staff {total}/{slot['required_total']}, women {female}/{slot['required_female_min']}, "
        f"men {male}/{slot['required_male_min']}. "
        f"Reasons: {reasons}"
    )


def build_interval_underfilled_report(
    connection,
    employees: list[dict],
    templates: list[dict],
    position_id: int,
    week_start_date: str,
    date_string: str,
    slot: dict,
    total: int,
    female: int,
    male: int,
) -> dict:
    require_female = female < slot["required_female_min"]
    require_male = male < slot["required_male_min"]
    reasons = explain_unfilled_interval_slot(
        connection,
        employees,
        templates,
        position_id,
        date_string,
        week_start_date,
        slot,
        require_female=require_female,
        require_male=require_male,
    )
    return {
        "kind": "interval",
        "date": date_string,
        "slot": slot_to_report(slot),
        "actual": {
            "total": total,
            "female": female,
            "male": male,
        },
        "missing": {
            "total": max(0, slot["required_total"] - total),
            "female": max(0, slot["required_female_min"] - female),
            "male": max(0, slot["required_male_min"] - male),
        },
        "reasons": reasons,
    }


def build_legacy_underfilled_report(
    connection,
    employees: list[dict],
    templates: list[dict],
    position_id: int,
    week_start_date: str,
    date_string: str,
    requirement: dict,
    total: int,
    female: int,
    male: int,
) -> dict:
    require_female = female < requirement["required_female_min"]
    require_male = male < requirement["required_male_min"]
    reasons = explain_unfilled_legacy_category(
        connection,
        employees,
        templates,
        position_id,
        date_string,
        week_start_date,
        requirement["shift_category"],
        require_female=require_female,
        require_male=require_male,
    )
    return {
        "kind": "legacy_category",
        "date": date_string,
        "shift_category": requirement["shift_category"],
        "actual": {
            "total": total,
            "female": female,
            "male": male,
        },
        "missing": {
            "total": max(0, requirement["required_total"] - total),
            "female": max(0, requirement["required_female_min"] - female),
            "male": max(0, requirement["required_male_min"] - male),
        },
        "reasons": reasons,
    }


def explain_unfilled_legacy_category(
    connection,
    employees: list[dict],
    templates: list[dict],
    position_id: int,
    date_string: str,
    week_start_date: str,
    category: str,
    require_female: bool = False,
    require_male: bool = False,
) -> str:
    category_templates = [template for template in templates if template["category"] == category]
    if not category_templates:
        return f"no active {category} templates"

    reason_counts: dict[str, int] = {}
    for employee in employees:
        if require_female and employee["sex"] != "female":
            reason_counts["not enough female employees available"] = reason_counts.get("not enough female employees available", 0) + 1
            continue
        if require_male and employee["sex"] != "male":
            reason_counts["not enough male employees available"] = reason_counts.get("not enough male employees available", 0) + 1
            continue

        for template in category_templates:
            reason = scheduling_rules.explain_employee_template_rejection(
                connection,
                employee,
                position_id,
                date_string,
                template,
                week_start_date,
                fatigue_relaxation=1,
            )
            if reason is None:
                break
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    return summarize_reasons(reason_counts)
