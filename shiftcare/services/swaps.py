"""Services: swaps for ShiftCare."""
from __future__ import annotations

from datetime import timedelta
from fastapi import HTTPException
from shiftcare.scheduling import rules as scheduling_rules
from shiftcare.services import common as services_common
from shiftcare.services import preferences as services_preferences
from shiftcare.services import schedule_queries as services_schedule_queries
import app_settings_service
import row_serializers
import schedule_time

def schedule_entry_template_for_swap(entry: dict) -> dict:
    return {
        "id": entry["shift_template_id"],
        "name": entry["shift_template_name"],
        "category": entry["shift_category"],
        "start_time": entry["start_time"],
        "end_time": entry["end_time"],
        "is_overnight": bool(entry["is_overnight"]),
        "is_split_only": bool(entry["is_split_only"]),
    }


def fetch_schedule_entry_for_swap(cursor, schedule_entry_id: int, organization_id: int) -> dict:
    row = services_common.fetch_one_or_404(
        cursor,
        """
        SELECT
            se.id,
            se.public_id,
            se.organization_id,
            se.employee_id,
            se.position_id,
            se.date,
            se.shift_template_id,
            se.no_show,
            COALESCE(se.start_time_override, st.start_time) AS start_time,
            COALESCE(se.end_time_override, st.end_time) AS end_time,
            COALESCE(se.is_overnight_override, st.is_overnight) AS is_overnight,
            st.name AS shift_template_name,
            st.category AS shift_category,
            st.is_split_only,
            e.full_name AS employee_name,
            e.sex AS employee_sex,
            p.name AS position_name,
            p.department_id,
            d.name AS department_name
        FROM schedule_entries se
        JOIN shift_templates st ON st.id = se.shift_template_id
        JOIN employees e ON e.id = se.employee_id
        JOIN positions p ON p.id = se.position_id
        LEFT JOIN departments d ON d.id = p.department_id
        WHERE se.id = ? AND se.organization_id = ?
        """,
        (schedule_entry_id, organization_id),
        "Schedule entry not found",
    )
    item = dict(row)
    item["is_overnight"] = bool(item["is_overnight"])
    item["is_split_only"] = bool(item["is_split_only"])
    item["no_show"] = bool(item["no_show"])
    return item


def get_projected_entries_for_swap(
    connection,
    employee_id: int,
    date_string: str,
    excluded_entry_id: int,
) -> list[dict]:
    return [
        entry
        for entry in services_schedule_queries.get_employee_entries_for_date(connection, employee_id, date_string)
        if int(entry["id"]) != int(excluded_entry_id)
    ]


def projected_has_category(
    connection,
    employee_id: int,
    date_string: str,
    category: str,
    excluded_entry_id: int,
) -> bool:
    return any(
        services_schedule_queries.entry_category(entry) == category
        for entry in get_projected_entries_for_swap(connection, employee_id, date_string, excluded_entry_id)
    )


def validate_employee_can_receive_swap_entry(
    connection,
    employee_id: int,
    incoming_entry: dict,
    replaced_entry_id: int,
) -> str | None:
    cursor = connection.cursor()
    employee_row = services_common.fetch_one_or_404(cursor, "SELECT * FROM employees WHERE id = ?", (employee_id,), "Employee not found")
    employee = row_serializers.row_to_employee_dict(employee_row)
    template = schedule_entry_template_for_swap(incoming_entry)
    date_string = incoming_entry["date"]
    position_id = int(incoming_entry["position_id"])
    app_settings = app_settings_service.get_position_app_settings(connection, position_id)

    if incoming_entry.get("no_show"):
        return "No-show shifts cannot be swapped"
    day_status = services_preferences.get_employee_day_status(connection, employee_id, date_string)
    if day_status and day_status["status_type"] in {"sick", "vacation"}:
        return "Target employee is unavailable on this date"
    if not services_preferences.category_allowed_by_preferences(connection, employee, date_string, template["category"]):
        return "Employee preferences or permissions block this shift"
    cursor.execute(
        """
        SELECT 1
        FROM employee_positions
        WHERE employee_id = ? AND position_id = ?
        """,
        (employee_id, position_id),
    )
    if not cursor.fetchone():
        return "Employee is not assigned to this position"

    existing_entries = get_projected_entries_for_swap(connection, employee_id, date_string, replaced_entry_id)
    cross_position_rejection = scheduling_rules.cross_position_same_day_rejection(connection, position_id, existing_entries)
    if cross_position_rejection:
        return cross_position_rejection

    if any(services_schedule_queries.entry_category(entry) == template["category"] for entry in existing_entries):
        return "Employee already has this shift category on this date"

    incoming_interval = schedule_time.build_interval(template["start_time"], template["end_time"], template["is_overnight"])
    for entry in existing_entries:
        existing_interval = schedule_time.build_interval(entry["start_time"], entry["end_time"], bool(entry["is_overnight"]))
        if incoming_interval.overlaps(existing_interval):
            return "Employee already has an overlapping shift"

    pairing_rejection = scheduling_rules.explain_same_day_pairing_rejection(
        connection,
        employee,
        date_string,
        template,
        existing_entries,
        app_settings,
    )
    if pairing_rejection:
        return pairing_rejection

    previous_date = (schedule_time.parse_date_string(date_string) - timedelta(days=1)).isoformat()
    next_date = (schedule_time.parse_date_string(date_string) + timedelta(days=1)).isoformat()
    if template["category"] == "morning" and projected_has_category(connection, employee_id, previous_date, "night", replaced_entry_id):
        return "Morning after previous night is forbidden"
    if template["category"] == "night" and projected_has_category(connection, employee_id, next_date, "morning", replaced_entry_id):
        return "Night before next morning is forbidden"
    return None


def validate_shift_swap_request_rows(connection, swap_request: dict) -> tuple[dict, dict]:
    cursor = connection.cursor()
    organization_id = int(swap_request["organization_id"])
    requester_entry = fetch_schedule_entry_for_swap(cursor, int(swap_request["requester_schedule_entry_id"]), organization_id)
    target_entry = fetch_schedule_entry_for_swap(cursor, int(swap_request["target_schedule_entry_id"]), organization_id)

    if int(requester_entry["employee_id"]) != int(swap_request["requester_employee_id"]):
        raise HTTPException(status_code=409, detail="Requester shift no longer belongs to the requester")
    if int(target_entry["employee_id"]) != int(swap_request["target_employee_id"]):
        raise HTTPException(status_code=409, detail="Target shift no longer belongs to the target employee")
    if int(requester_entry["position_id"]) != int(target_entry["position_id"]):
        raise HTTPException(status_code=400, detail="Shift swaps must stay inside one position")
    if requester_entry["date"] and target_entry["date"]:
        if schedule_time.get_week_start_for_date(requester_entry["date"]) != schedule_time.get_week_start_for_date(target_entry["date"]):
            raise HTTPException(status_code=400, detail="Shift swaps must stay inside one week")
    requester_rejection = validate_employee_can_receive_swap_entry(
        connection,
        int(swap_request["requester_employee_id"]),
        target_entry,
        int(swap_request["requester_schedule_entry_id"]),
    )
    if requester_rejection:
        raise HTTPException(status_code=400, detail=f"Requester cannot take target shift: {requester_rejection}")
    target_rejection = validate_employee_can_receive_swap_entry(
        connection,
        int(swap_request["target_employee_id"]),
        requester_entry,
        int(swap_request["target_schedule_entry_id"]),
    )
    if target_rejection:
        raise HTTPException(status_code=400, detail=f"Target employee cannot take requester shift: {target_rejection}")
    return requester_entry, target_entry


def shift_swap_select_sql(extra_where: str = "") -> str:
    where_sql = f"WHERE {extra_where}" if extra_where else ""
    return f"""
        SELECT
            ssr.*,
            requester.full_name AS requester_employee_name,
            target.full_name AS target_employee_name,
            rse.date AS requester_date,
            rse.position_id AS requester_position_id,
            rst.name AS requester_shift_template_name,
            rst.category AS requester_shift_category,
            COALESCE(rse.start_time_override, rst.start_time) AS requester_start_time,
            COALESCE(rse.end_time_override, rst.end_time) AS requester_end_time,
            rp.name AS requester_position_name,
            rd.name AS requester_department_name,
            tse.date AS target_date,
            tse.position_id AS target_position_id,
            tst.name AS target_shift_template_name,
            tst.category AS target_shift_category,
            COALESCE(tse.start_time_override, tst.start_time) AS target_start_time,
            COALESCE(tse.end_time_override, tst.end_time) AS target_end_time,
            tp.name AS target_position_name,
            td.name AS target_department_name
        FROM shift_swap_requests ssr
        JOIN employees requester ON requester.id = ssr.requester_employee_id
        JOIN employees target ON target.id = ssr.target_employee_id
        JOIN schedule_entries rse ON rse.id = ssr.requester_schedule_entry_id
        JOIN shift_templates rst ON rst.id = rse.shift_template_id
        JOIN positions rp ON rp.id = rse.position_id
        LEFT JOIN departments rd ON rd.id = rp.department_id
        JOIN schedule_entries tse ON tse.id = ssr.target_schedule_entry_id
        JOIN shift_templates tst ON tst.id = tse.shift_template_id
        JOIN positions tp ON tp.id = tse.position_id
        LEFT JOIN departments td ON td.id = tp.department_id
        {where_sql}
        ORDER BY ssr.created_at DESC, ssr.id DESC
    """


def shift_swap_row_to_dict(row) -> dict:
    item = dict(row)
    return {
        "id": item["id"],
        "public_id": item.get("public_id"),
        "organization_id": item["organization_id"],
        "requester_employee_id": item["requester_employee_id"],
        "requester_employee_name": item["requester_employee_name"],
        "target_employee_id": item["target_employee_id"],
        "target_employee_name": item["target_employee_name"],
        "requester_schedule_entry_id": item["requester_schedule_entry_id"],
        "target_schedule_entry_id": item["target_schedule_entry_id"],
        "status": item["status"],
        "requester_note": item.get("requester_note"),
        "target_note": item.get("target_note"),
        "admin_note": item.get("admin_note"),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "target_responded_at": item.get("target_responded_at"),
        "reviewed_at": item.get("reviewed_at"),
        "reviewed_by": item.get("reviewed_by"),
        "requester_shift": {
            "date": item["requester_date"],
            "position_id": item["requester_position_id"],
            "position_name": item["requester_position_name"],
            "department_name": item.get("requester_department_name"),
            "template_name": item["requester_shift_template_name"],
            "category": item["requester_shift_category"],
            "start_time": item["requester_start_time"],
            "end_time": item["requester_end_time"],
        },
        "target_shift": {
            "date": item["target_date"],
            "position_id": item["target_position_id"],
            "position_name": item["target_position_name"],
            "department_name": item.get("target_department_name"),
            "template_name": item["target_shift_template_name"],
            "category": item["target_shift_category"],
            "start_time": item["target_start_time"],
            "end_time": item["target_end_time"],
        },
    }


def fetch_shift_swap_request(cursor, swap_request_id: int, organization_id: int) -> dict:
    cursor.execute(
        shift_swap_select_sql("ssr.id = ? AND ssr.organization_id = ?"),
        (swap_request_id, organization_id),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Shift swap request not found")
    return dict(row)
