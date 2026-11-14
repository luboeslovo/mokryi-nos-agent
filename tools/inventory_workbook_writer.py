"""Serialize the inventory movement workbook with public Python tooling."""

from __future__ import annotations

import os
import stat
import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo

from inventory_workbook_contract import (
    AMOUNT_COLUMNS,
    DATE_NUMBER_FORMAT,
    DATETIME_NUMBER_FORMAT,
    LAST_SUCCESSFUL_UPDATE_CELL,
    LOADED_END_CELL,
    LOADED_START_CELL,
    PARAMETERS_SHEET_NAME,
    QUANTITY_COLUMNS,
    REPORT_FIRST_DATA_ROW,
    REPORT_GROUP_HEADERS,
    REPORT_HEADERS,
    REPORT_HEADER_ROW,
    REPORT_LAST_COLUMN,
    REPORT_LOADED_END_CELL,
    REPORT_LOADED_START_CELL,
    REPORT_SHEET_NAME,
    REPORT_TABLE_NAME,
    REPORT_TOTAL_LABEL_END_COLUMN,
    REQUESTED_END_CELL,
    REQUESTED_START_CELL,
    TOTAL_COLUMNS,
    WRAPPED_TEXT_COLUMNS,
    subtotal_formulas,
    table_end_row,
    total_row,
)


FONT_NAME = "Arial"
TEXT_COLOR = "1F2937"
WHITE = "FFFFFF"
SECTION_FILL = "E8EEF7"
INPUT_FILL = "FFF2CC"
LOADED_FILL = "F3F4F6"
NOTE_FILL = "FFF8E1"
TOTAL_FILL = "D9E2F3"
HEADER_FILL = "4472C4"


def _fill(color: str) -> PatternFill:
    return PatternFill(fill_type="solid", fgColor=color)


def _border(color: str) -> Border:
    side = Side(style="thin", color=color)
    return Border(left=side, right=side, top=side, bottom=side)


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _excel_number(value: object) -> int | float:
    if isinstance(value, Decimal):
        integral = value.to_integral_value()
        return int(integral) if value == integral else float(value)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    return float(value)


def _style_cells(
    worksheet: Any,
    cell_range: str,
    *,
    fill: PatternFill | None = None,
    font: Font | None = None,
    alignment: Alignment | None = None,
    border: Border | None = None,
) -> None:
    for row in worksheet[cell_range]:
        for cell in row:
            if fill is not None:
                cell.fill = fill
            if font is not None:
                cell.font = font
            if alignment is not None:
                cell.alignment = alignment
            if border is not None:
                cell.border = border


def _write_parameters_sheet(
    worksheet: Any,
    start: date,
    end: date,
    generated_at: datetime,
) -> None:
    worksheet.sheet_view.showGridLines = False
    worksheet.merge_cells("A1:D1")
    worksheet["A1"] = "Параметры отчёта"
    worksheet["A3"] = "Период для следующего обновления"
    worksheet["A4"] = "Дата начала"
    worksheet["A5"] = "Дата окончания"
    worksheet[REQUESTED_START_CELL] = start
    worksheet[REQUESTED_END_CELL] = end
    worksheet["A7"] = "Последнее успешное обновление"
    worksheet["A8"] = "Начало загруженного периода"
    worksheet["A9"] = "Конец загруженного периода"
    worksheet["A10"] = "Дата и время обновления"
    worksheet[LOADED_START_CELL] = start
    worksheet[LOADED_END_CELL] = end
    worksheet[LAST_SUCCESSFUL_UPDATE_CELL] = generated_at
    worksheet.merge_cells("A12:D12")
    worksheet["A12"] = (
        "После изменения дат сохраните и закройте книгу, затем запустите "
        "«Обновить отчёт»."
    )

    _style_cells(
        worksheet,
        "A1:D12",
        font=Font(name=FONT_NAME, size=11, color=TEXT_COLOR),
    )
    worksheet["A1"].font = Font(
        name=FONT_NAME,
        size=16,
        bold=True,
        color=TEXT_COLOR,
    )
    for cell_range in ("A3:D3", "A7:D7"):
        _style_cells(
            worksheet,
            cell_range,
            fill=_fill(SECTION_FILL),
            font=Font(name=FONT_NAME, bold=True, color=TEXT_COLOR),
            border=_border("B8C2D1"),
        )
    _style_cells(
        worksheet,
        "A4:A5",
        font=Font(name=FONT_NAME, bold=True, color=TEXT_COLOR),
    )
    _style_cells(
        worksheet,
        "B4:B5",
        fill=_fill(INPUT_FILL),
        font=Font(name=FONT_NAME, bold=True, color=TEXT_COLOR),
        alignment=Alignment(horizontal="center"),
        border=_border("A67C00"),
    )
    for ref in (REQUESTED_START_CELL, REQUESTED_END_CELL, LOADED_START_CELL, LOADED_END_CELL):
        worksheet[ref].number_format = DATE_NUMBER_FORMAT
    worksheet[LAST_SUCCESSFUL_UPDATE_CELL].number_format = DATETIME_NUMBER_FORMAT
    _style_cells(worksheet, "B8:B10", fill=_fill(LOADED_FILL))
    _style_cells(
        worksheet,
        "A12:D12",
        fill=_fill(NOTE_FILL),
        font=Font(name=FONT_NAME, italic=True, color="7A5200"),
        alignment=Alignment(vertical="center", wrap_text=True),
        border=_border("D6B656"),
    )
    worksheet.row_dimensions[12].height = 34
    worksheet.column_dimensions["A"].width = 34
    worksheet.column_dimensions["B"].width = 20
    worksheet.column_dimensions["C"].width = 12
    worksheet.column_dimensions["D"].width = 12


def _write_report_sheet(
    worksheet: Any,
    start: date,
    end: date,
    rows: list[dict[str, Any]],
    applied_filter: str,
    notes: list[str],
) -> None:
    data_count = len(rows)
    table_last_row = table_end_row(data_count)
    totals_row = total_row(data_count)

    worksheet.sheet_view.showGridLines = False
    worksheet.merge_cells(f"A1:{REPORT_LAST_COLUMN}1")
    worksheet.merge_cells("A3:B3")
    worksheet["A1"] = "Отчет движения товара"
    worksheet["A3"] = "Фактический период"
    worksheet[REPORT_LOADED_START_CELL] = start
    worksheet["D3"] = "—"
    worksheet[REPORT_LOADED_END_CELL] = end
    worksheet["A5"] = "Фильтр при формировании"
    worksheet["C5"] = applied_filter

    for range_ref, cell_ref, label in REPORT_GROUP_HEADERS:
        worksheet.merge_cells(range_ref)
        worksheet[cell_ref] = label
    for column_index, header in enumerate(REPORT_HEADERS, start=1):
        worksheet.cell(REPORT_HEADER_ROW, column_index, header)

    for offset, row in enumerate(rows):
        row_number = REPORT_FIRST_DATA_ROW + offset
        values = (
            _excel_number(row["number"]),
            row["category"],
            _excel_number(row["nmi_id"]),
            _clean_text(row.get("brand")),
            _clean_text(row["nomenclature_name"]),
            _excel_number(row["opening_quantity"]),
            _excel_number(row["opening_amount"]),
            _excel_number(row["intake_quantity"]),
            _excel_number(row["intake_amount"]),
            _excel_number(row["ending_quantity"]),
            _excel_number(row["ending_amount"]),
        )
        for column_index, value in enumerate(values, start=1):
            worksheet.cell(row_number, column_index, value)

    if not rows:
        for column_index in range(1, len(REPORT_HEADERS) + 1):
            worksheet.cell(REPORT_FIRST_DATA_ROW, column_index, None)

    table_ref = f"A{REPORT_HEADER_ROW}:{REPORT_LAST_COLUMN}{table_last_row}"
    inventory_table = Table(displayName=REPORT_TABLE_NAME, ref=table_ref)
    inventory_table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    worksheet.add_table(inventory_table)

    worksheet.cell(totals_row, 1, "ИТОГО")
    formulas = subtotal_formulas(data_count)
    for column in TOTAL_COLUMNS:
        worksheet[f"{column}{totals_row}"] = formulas[column]

    _style_cells(
        worksheet,
        f"A1:{REPORT_LAST_COLUMN}{totals_row}",
        fill=_fill(WHITE),
        font=Font(name=FONT_NAME, size=11, color=TEXT_COLOR),
    )
    worksheet["A1"].font = Font(
        name=FONT_NAME,
        size=18,
        bold=True,
        color=TEXT_COLOR,
    )
    _style_cells(
        worksheet,
        "A3:E3",
        alignment=Alignment(vertical="center"),
    )
    worksheet["A3"].font = Font(
        name=FONT_NAME,
        bold=True,
        color=TEXT_COLOR,
    )
    worksheet[REPORT_LOADED_START_CELL].number_format = DATE_NUMBER_FORMAT
    worksheet[REPORT_LOADED_END_CELL].number_format = DATE_NUMBER_FORMAT
    worksheet["A5"].font = Font(
        name=FONT_NAME,
        bold=True,
        color=TEXT_COLOR,
    )
    _style_cells(
        worksheet,
        f"{TOTAL_COLUMNS[0]}7:{REPORT_LAST_COLUMN}7",
        fill=_fill(SECTION_FILL),
        font=Font(name=FONT_NAME, bold=True, color=TEXT_COLOR),
        alignment=Alignment(horizontal="center", vertical="center", wrap_text=True),
        border=_border("B8C2D1"),
    )
    _style_cells(
        worksheet,
        f"A{REPORT_HEADER_ROW}:{REPORT_LAST_COLUMN}{REPORT_HEADER_ROW}",
        fill=_fill(HEADER_FILL),
        font=Font(name=FONT_NAME, bold=True, color=WHITE),
        alignment=Alignment(horizontal="center", vertical="center", wrap_text=True),
        border=_border(WHITE),
    )
    worksheet.row_dimensions[REPORT_HEADER_ROW].height = 42

    _style_cells(
        worksheet,
        f"A{REPORT_FIRST_DATA_ROW}:{REPORT_LAST_COLUMN}{table_last_row}",
        alignment=Alignment(vertical="top"),
    )
    _style_cells(
        worksheet,
        f"A{REPORT_FIRST_DATA_ROW}:A{table_last_row}",
        alignment=Alignment(horizontal="center", vertical="top"),
    )
    _style_cells(
        worksheet,
        f"C{REPORT_FIRST_DATA_ROW}:C{table_last_row}",
        alignment=Alignment(horizontal="center", vertical="top"),
    )
    for column in WRAPPED_TEXT_COLUMNS:
        _style_cells(
            worksheet,
            f"{column}{REPORT_FIRST_DATA_ROW}:{column}{table_last_row}",
            alignment=Alignment(vertical="top", wrap_text=True),
        )
    for column in QUANTITY_COLUMNS:
        for row_number in range(REPORT_FIRST_DATA_ROW, table_last_row + 1):
            worksheet[f"{column}{row_number}"].number_format = "#,##0.###"
    for column in AMOUNT_COLUMNS:
        for row_number in range(REPORT_FIRST_DATA_ROW, table_last_row + 1):
            worksheet[f"{column}{row_number}"].number_format = "#,##0.00"
    for row_number in range(REPORT_FIRST_DATA_ROW, table_last_row + 1):
        worksheet[f"C{row_number}"].number_format = "0"

    for offset, row in enumerate(rows):
        row_number = REPORT_FIRST_DATA_ROW + offset
        category_lines = max(1, (len(str(row.get("category") or "")) + 41) // 42)
        brand_lines = max(1, (len(str(row.get("brand") or "")) + 19) // 20)
        name_lines = max(
            1,
            (len(str(row.get("nomenclature_name") or "")) + 45) // 46,
        )
        worksheet.row_dimensions[row_number].height = max(
            19,
            max(category_lines, brand_lines, name_lines) * 15,
        )

    _style_cells(
        worksheet,
        f"A{totals_row}:{REPORT_LAST_COLUMN}{totals_row}",
        fill=_fill(TOTAL_FILL),
        font=Font(name=FONT_NAME, bold=True, color=TEXT_COLOR),
        border=_border("9EADBF"),
    )
    _style_cells(
        worksheet,
        f"A{totals_row}:{REPORT_TOTAL_LABEL_END_COLUMN}{totals_row}",
        alignment=Alignment(horizontal="right"),
    )
    for column in QUANTITY_COLUMNS:
        worksheet[f"{column}{totals_row}"].number_format = "#,##0.###"
    for column in AMOUNT_COLUMNS:
        worksheet[f"{column}{totals_row}"].number_format = "#,##0.00"

    widths = {
        "A": 7,
        "B": 34,
        "C": 15,
        "D": 20,
        "E": 42,
        "F": 17,
        "G": 17,
        "H": 17,
        "I": 17,
        "J": 17,
        "K": 17,
    }
    for column, width in widths.items():
        worksheet.column_dimensions[column].width = width
    worksheet.freeze_panes = f"A{REPORT_FIRST_DATA_ROW}"

    note_row = totals_row + 2
    for note in notes:
        worksheet.merge_cells(f"A{note_row}:{REPORT_LAST_COLUMN}{note_row}")
        worksheet[f"A{note_row}"] = note
        _style_cells(
            worksheet,
            f"A{note_row}:{REPORT_LAST_COLUMN}{note_row}",
            fill=_fill(WHITE),
            font=Font(name=FONT_NAME, italic=True, color="000000"),
            alignment=Alignment(vertical="top", wrap_text=True),
        )
        worksheet.row_dimensions[note_row].height = 30
        note_row += 1


def _build_workbook(
    start: date,
    end: date,
    rows: list[dict[str, Any]],
    applied_filter: str,
    notes: list[str],
    generated_at: datetime,
) -> Workbook:
    workbook = Workbook()
    parameters = workbook.active
    parameters.title = PARAMETERS_SHEET_NAME
    report = workbook.create_sheet(REPORT_SHEET_NAME)
    _write_parameters_sheet(parameters, start, end, generated_at)
    _write_report_sheet(report, start, end, rows, applied_filter, notes)
    workbook.calculation.calcMode = "auto"
    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    return workbook


def write_inventory_workbook(
    output_path: Path,
    start: date,
    end: date,
    rows: list[dict[str, Any]],
    applied_filter: str,
    notes: list[str],
    *,
    generated_at: datetime | None = None,
) -> None:
    """Create and atomically publish one XLSX without Node or sidecars."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temp_path = tempfile.mkstemp(
        prefix=f".{output.stem}.export_",
        suffix=".xlsx",
        dir=output.parent,
    )
    os.close(descriptor)
    temp_path = Path(raw_temp_path)
    try:
        workbook = _build_workbook(
            start,
            end,
            rows,
            applied_filter,
            notes,
            generated_at or datetime.now().replace(microsecond=0),
        )
        workbook.save(temp_path)
        metadata = temp_path.stat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size <= 0:
            raise OSError("openpyxl did not create a non-empty XLSX file.")
        os.replace(temp_path, output)
    finally:
        temp_path.unlink(missing_ok=True)
