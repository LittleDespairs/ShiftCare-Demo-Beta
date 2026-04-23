from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


def get_export_label(key: str, lang: str) -> str:
    labels = {
        "en": {
            "sick": "Sick",
            "day_off": "Day off",
            "no_show": "No-show",
        },
        "ru": {
            "sick": "Болен",
            "day_off": "Выходной",
            "no_show": "Неявка",
        },
        "he": {
            "sick": "מחלה",
            "day_off": "יום חופשי",
            "no_show": "אי הגעה",
        },
    }
    return labels.get(lang, labels["en"]).get(key, key)


def build_schedule_cell_text(entries: list[dict], day_status: dict | None = None, lang: str = "en") -> str:
    if day_status and day_status.get("status_type") in {"sick", "day_off"}:
        return get_export_label(day_status["status_type"], lang)

    return "\n".join(
        get_export_label("no_show", lang) if entry.get("no_show") else entry["shift_template_name"]
        for entry in sorted(entries, key=lambda item: item["start_time"])
    )


def build_schedule_export_workbook(
    position: dict,
    week_start_date: str,
    week_dates: list[str],
    employees: list[dict],
    entries: list[dict],
    day_status_map: dict[tuple[int, str], dict],
    lang: str = "en",
) -> BytesIO:
    grouped_entries: dict[tuple[int, str], list[dict]] = {}
    for entry in entries:
        grouped_entries.setdefault((entry["employee_id"], entry["date"]), []).append(entry)

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Schedule"
    worksheet.sheet_view.rightToLeft = True

    header_fill = PatternFill("solid", fgColor="D9EAF7")
    date_fill = PatternFill("solid", fgColor="F3F6F9")
    thin_side = Side(style="thin", color="CCCCCC")
    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    worksheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=9)
    worksheet["A1"] = f"Schedule export - {position['name']} - week starting {week_start_date}"
    worksheet["A1"].font = Font(bold=True, size=14)
    worksheet["A1"].alignment = center

    headers = ["Employee", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Weekly total"]
    for col_index, header in enumerate(headers, start=1):
        cell = worksheet.cell(row=3, column=col_index, value=header)
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = center
        cell.border = thin_border

    for index, current_date in enumerate(["", *week_dates, ""], start=1):
        cell = worksheet.cell(row=4, column=index, value=current_date)
        cell.fill = date_fill
        cell.alignment = center
        cell.border = thin_border

    for row_index, employee in enumerate(employees, start=5):
        name_cell = worksheet.cell(row=row_index, column=1, value=employee["full_name"])
        name_cell.font = Font(bold=True)
        name_cell.alignment = center
        name_cell.border = thin_border
        weekly_count = 0
        max_lines = 1
        for day_offset, current_date in enumerate(week_dates, start=2):
            day_entries = grouped_entries.get((employee["id"], current_date), [])
            day_status = day_status_map.get((employee["id"], current_date))
            if not (day_status and day_status.get("status_type") in {"sick", "day_off"}):
                weekly_count += sum(1 for entry in day_entries if not entry.get("no_show"))
            text = build_schedule_cell_text(day_entries, day_status, lang)
            max_lines = max(max_lines, text.count("\n") + 1 if text else 1)
            cell = worksheet.cell(row=row_index, column=day_offset, value=text)
            cell.alignment = center
            cell.border = thin_border
        total_cell = worksheet.cell(row=row_index, column=9, value=weekly_count)
        total_cell.alignment = center
        total_cell.border = thin_border
        worksheet.row_dimensions[row_index].height = max(22, max_lines * 18)

    for column in "ABCDEFGHI":
        worksheet.column_dimensions[column].width = 24 if column != "I" else 12
    worksheet.freeze_panes = "B5"
    worksheet.page_setup.orientation = "landscape"
    worksheet.page_setup.paperSize = worksheet.PAPERSIZE_A4
    worksheet.page_setup.fitToWidth = 1
    worksheet.page_setup.fitToHeight = 0
    worksheet.print_title_rows = "1:4"
    worksheet.print_options.horizontalCentered = True

    summary_sheet = workbook.create_sheet("Summary")
    summary_sheet.sheet_view.rightToLeft = True
    summary_sheet["A1"] = "Coordinator summary"
    summary_sheet["A1"].font = Font(bold=True, size=14)
    summary_sheet["A3"] = "Position"
    summary_sheet["B3"] = position["name"]
    summary_sheet["A4"] = "Week start"
    summary_sheet["B4"] = week_start_date
    summary_sheet["A5"] = "Assigned employees"
    summary_sheet["B5"] = len(employees)
    summary_sheet["A6"] = "Schedule entries"
    summary_sheet["B6"] = len(entries)
    summary_sheet["A7"] = "Worked shifts"
    summary_sheet["B7"] = sum(1 for entry in entries if not entry.get("no_show"))
    summary_sheet["A8"] = "No-show entries"
    summary_sheet["B8"] = sum(1 for entry in entries if entry.get("no_show"))
    summary_sheet["A9"] = "Sick days"
    summary_sheet["B9"] = sum(1 for item in day_status_map.values() if item.get("status_type") == "sick")
    summary_sheet["A10"] = "Day-off statuses"
    summary_sheet["B10"] = sum(1 for item in day_status_map.values() if item.get("status_type") == "day_off")
    summary_sheet.column_dimensions["A"].width = 28
    summary_sheet.column_dimensions["B"].width = 24

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output
