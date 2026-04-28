from html import escape
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from excel_export import (
    build_schedule_cell_payload,
    build_unique_employees_by_priority_position,
    format_total,
    get_export_label,
    get_weekday_labels,
)


def xml_text(value: object) -> str:
    return escape(str(value), quote=False)


def word_paragraph(text: object, bold: bool = False, align: str | None = None) -> str:
    text_value = xml_text(text)
    run_properties = "<w:rPr><w:b/></w:rPr>" if bold else ""
    paragraph_properties = f"<w:pPr><w:jc w:val=\"{align}\"/></w:pPr>" if align else ""
    return f"<w:p>{paragraph_properties}<w:r>{run_properties}<w:t>{text_value}</w:t></w:r></w:p>"


def word_cell(
    lines: list[str] | str | int,
    width: int,
    bold: bool = False,
    align: str = "center",
    shading: str | None = None,
) -> str:
    if not isinstance(lines, list):
        lines = [str(lines)]
    paragraphs = "".join(word_paragraph(line, bold=bold, align=align) for line in lines) or word_paragraph("", align=align)
    shading_xml = f"<w:shd w:fill=\"{shading}\"/>" if shading else ""
    return (
        "<w:tc>"
        f"<w:tcPr><w:tcW w:w=\"{width}\" w:type=\"dxa\"/><w:vAlign w:val=\"center\"/>{shading_xml}</w:tcPr>"
        f"{paragraphs}"
        "</w:tc>"
    )


def word_row(
    cells: list[list[str] | str | int],
    widths: list[int],
    bold: bool = False,
    header: bool = False,
    shading: str | None = None,
    alignments: list[str] | None = None,
) -> str:
    row_properties = "<w:trPr><w:tblHeader/></w:trPr>" if header else ""
    resolved_alignments = alignments or ["center"] * len(cells)
    rendered_cells = "".join(
        word_cell(
            cell,
            width=widths[index],
            bold=bold,
            align=resolved_alignments[index] if index < len(resolved_alignments) else "center",
            shading=shading,
        )
        for index, cell in enumerate(cells)
    )
    return f"<w:tr>{row_properties}{rendered_cells}</w:tr>"


def word_table(rows: list[str], widths: list[int]) -> str:
    grid_columns = "".join(f"<w:gridCol w:w=\"{width}\"/>" for width in widths)
    return (
        "<w:tbl>"
        "<w:tblPr>"
        "<w:tblW w:w=\"0\" w:type=\"auto\"/>"
        "<w:tblLayout w:type=\"fixed\"/>"
        "<w:tblCellMar>"
        "<w:top w:w=\"90\" w:type=\"dxa\"/>"
        "<w:left w:w=\"90\" w:type=\"dxa\"/>"
        "<w:bottom w:w=\"90\" w:type=\"dxa\"/>"
        "<w:right w:w=\"90\" w:type=\"dxa\"/>"
        "</w:tblCellMar>"
        "<w:tblBorders>"
        "<w:top w:val=\"single\" w:sz=\"6\" w:space=\"0\" w:color=\"94A3B8\"/>"
        "<w:left w:val=\"single\" w:sz=\"6\" w:space=\"0\" w:color=\"94A3B8\"/>"
        "<w:bottom w:val=\"single\" w:sz=\"6\" w:space=\"0\" w:color=\"94A3B8\"/>"
        "<w:right w:val=\"single\" w:sz=\"6\" w:space=\"0\" w:color=\"94A3B8\"/>"
        "<w:insideH w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"CBD5E1\"/>"
        "<w:insideV w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"CBD5E1\"/>"
        "</w:tblBorders>"
        "</w:tblPr>"
        f"<w:tblGrid>{grid_columns}</w:tblGrid>"
        f"{''.join(rows)}"
        "</w:tbl>"
    )


def create_docx(document_body: str) -> BytesIO:
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {document_body}
    <w:sectPr>
      <w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/>
      <w:pgMar w:top="720" w:right="720" w:bottom="720" w:left="720" w:header="360" w:footer="360" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>
"""
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
""",
        )
        archive.writestr("word/document.xml", document_xml)
    output.seek(0)
    return output


def build_summary_rows(summary_rows: list[tuple[str, object]], lang: str) -> str:
    widths = [4500, 4500]
    table_rows = [word_row([get_export_label("summary_title", lang), ""], widths, bold=True, header=True, shading="D9EAF7")]
    for key, value in summary_rows:
        table_rows.append(word_row([get_export_label(key, lang), value], widths, alignments=["left", "center"]))
    return word_table(table_rows, widths)


def build_schedule_export_document(
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

    widths = [2200, *([1600] * 7), 1998]
    rows = [
        word_row(
            [get_export_label("employee", lang), *get_weekday_labels(lang), get_export_label("weekly_total", lang)],
            widths,
            bold=True,
            header=True,
            shading="D9EAF7",
        ),
        word_row(["", *week_dates, ""], widths, bold=True, header=True, shading="F3F6F9"),
    ]
    total_worked_count = 0
    total_worked_minutes = 0
    for employee in employees:
        day_cells = []
        weekly_count = 0
        weekly_minutes = 0
        for current_date in week_dates:
            payload = build_schedule_cell_payload(
                grouped_entries.get((employee["id"], current_date), []),
                position["id"],
                day_status_map.get((employee["id"], current_date)),
                lang,
            )
            day_cells.append([line["text"] for line in payload["lines"]] or [""])
            weekly_count += payload["worked_count"]
            weekly_minutes += payload["worked_minutes"]
            total_worked_count += payload["worked_count"]
            total_worked_minutes += payload["worked_minutes"]
        rows.append(
            word_row(
                [employee["full_name"], *day_cells, format_total(weekly_count, weekly_minutes, lang)],
                widths,
                alignments=["left", *(["center"] * 8)],
            )
        )

    summary_rows = [
        ("position", position["name"]),
        ("week_start", week_start_date),
        ("assigned_employees", len(employees)),
        ("schedule_entries", len(entries)),
        ("worked_shifts", format_total(total_worked_count, total_worked_minutes, lang)),
        ("no_show_entries", sum(1 for entry in entries if entry.get("no_show"))),
        ("sick_days", sum(1 for item in day_status_map.values() if item.get("status_type") == "sick")),
        ("day_off_statuses", sum(1 for item in day_status_map.values() if item.get("status_type") == "day_off")),
    ]
    title = (
        f"{get_export_label('schedule_title', lang)} - {position['name']} - "
        f"{get_export_label('week_starting', lang)} {week_start_date}"
    )
    body = (
        word_paragraph(title, bold=True)
        + word_table(rows, widths)
        + word_paragraph("")
        + build_summary_rows(summary_rows, lang)
    )
    return create_docx(body)


def build_all_schedule_export_document(
    positions: list[dict],
    week_start_date: str,
    week_dates: list[str],
    employees_by_position: dict[int, list[dict]],
    entries: list[dict],
    day_status_map: dict[tuple[int, str], dict],
    lang: str = "en",
) -> BytesIO:
    employees_by_priority_position = build_unique_employees_by_priority_position(positions, employees_by_position)
    grouped_entries: dict[tuple[int, str], list[dict]] = {}
    for entry in entries:
        grouped_entries.setdefault((entry["employee_id"], entry["date"]), []).append(entry)

    widths = [1500, 650, 1900, *([1450] * 7), 1198]
    rows = [
        word_row(
            [
                get_export_label("position", lang),
                get_export_label("row_number", lang),
                get_export_label("employee", lang),
                *get_weekday_labels(lang),
                get_export_label("weekly_total", lang),
            ],
            widths,
            bold=True,
            header=True,
            shading="D9EAF7",
        ),
        word_row(["", "", "", *week_dates, ""], widths, bold=True, header=True, shading="F3F6F9"),
    ]
    total_worked_count = 0
    total_worked_minutes = 0
    total_employee_rows = 0
    row_number = 1
    for position in positions:
        for employee in employees_by_priority_position.get(position["id"], []):
            day_cells = []
            weekly_count = 0
            weekly_minutes = 0
            for current_date in week_dates:
                payload = build_schedule_cell_payload(
                    grouped_entries.get((employee["id"], current_date), []),
                    position["id"],
                    day_status_map.get((employee["id"], current_date)),
                    lang,
                )
                day_cells.append([line["text"] for line in payload["lines"]] or [""])
                weekly_count += payload["worked_count"]
                weekly_minutes += payload["worked_minutes"]
                total_worked_count += payload["worked_count"]
                total_worked_minutes += payload["worked_minutes"]
            rows.append(
                word_row(
                    [
                        position["name"],
                        row_number,
                        employee["full_name"],
                        *day_cells,
                        format_total(weekly_count, weekly_minutes, lang),
                    ],
                    widths,
                    alignments=["left", "center", "left", *(["center"] * 8)],
                )
            )
            row_number += 1
            total_employee_rows += 1

    summary_rows = [
        ("positions", len(positions)),
        ("week_start", week_start_date),
        ("assigned_employees", total_employee_rows),
        ("schedule_entries", len(entries)),
        ("worked_shifts", format_total(total_worked_count, total_worked_minutes, lang)),
        ("no_show_entries", sum(1 for entry in entries if entry.get("no_show"))),
        ("sick_days", sum(1 for item in day_status_map.values() if item.get("status_type") == "sick")),
        ("day_off_statuses", sum(1 for item in day_status_map.values() if item.get("status_type") == "day_off")),
    ]
    title = f"{get_export_label('schedule_title', lang)} - {get_export_label('week_starting', lang)} {week_start_date}"
    body = (
        word_paragraph(title, bold=True)
        + word_table(rows, widths)
        + word_paragraph("")
        + build_summary_rows(summary_rows, lang)
    )
    return create_docx(body)
