"""Small Open XML fixtures for inventory workbook unit tests."""

from __future__ import annotations

import zipfile
from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape

from inventory_workbook_contract import (
    LAST_SUCCESSFUL_UPDATE_CELL,
    LOADED_END_CELL,
    LOADED_START_CELL,
    PARAMETERS_SHEET_NAME,
    REPORT_FIRST_DATA_ROW,
    REPORT_HEADERS,
    REPORT_HEADER_ROW,
    REPORT_LAST_COLUMN,
    REPORT_LOADED_END_CELL,
    REPORT_LOADED_START_CELL,
    REPORT_REQUIRED_MERGES,
    REPORT_SHEET_NAME,
    REPORT_TABLE_NAME,
    REQUESTED_END_CELL,
    REQUESTED_START_CELL,
    TOTAL_COLUMNS,
    subtotal_formulas,
    table_end_row,
    total_row,
)


def excel_serial(value: date | datetime) -> float:
    moment = (
        datetime.combine(value, datetime.min.time())
        if isinstance(value, date) and not isinstance(value, datetime)
        else value
    )
    return (moment - datetime(1899, 12, 30)).total_seconds() / 86400


def cell_xml(ref: str, value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return f'<c r="{ref}" s="2"><v>{excel_serial(value)}</v></c>'
    if isinstance(value, date):
        return f'<c r="{ref}" s="1"><v>{excel_serial(value)}</v></c>'
    if isinstance(value, str):
        return (
            f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
        )
    return f'<c r="{ref}"><v>{value}</v></c>'


def default_rows(count: int) -> list[dict[str, object]]:
    return [
        {
            "number": index + 1,
            "category": f"Категория {index + 1}",
            "brand": "Тестовый бренд" if index % 2 == 0 else "",
            "nmi_id": 900000 + index,
            "nomenclature_name": f"Синтетический товар {index + 1}",
            "opening_quantity": index + 1,
            "opening_amount": (index + 1) * 100.25,
            "intake_quantity": index + 2,
            "intake_amount": (index + 2) * 50.5,
            "ending_quantity": index + 3,
            "ending_amount": (index + 3) * 75.75,
        }
        for index in range(count)
    ]


def write_inventory_workbook_fixture(
    path: Path,
    *,
    requested_start: date | str | None = date(2026, 8, 1),
    requested_end: date | str | None = date(2026, 8, 18),
    loaded_start: date | str | None = date(2026, 8, 1),
    loaded_end: date | str | None = date(2026, 8, 18),
    last_successful_update: datetime | str | None = datetime(2026, 9, 8, 14, 30),
    rows: list[dict[str, object]] | None = None,
) -> None:
    report_rows = default_rows(0) if rows is None else rows
    data_count = len(report_rows)
    table_last_row = table_end_row(data_count)
    totals_row = total_row(data_count)

    parameter_cells = "".join(
        [
            cell_xml("A1", "Параметры отчёта"),
            cell_xml(REQUESTED_START_CELL, requested_start),
            cell_xml(REQUESTED_END_CELL, requested_end),
            cell_xml(LOADED_START_CELL, loaded_start),
            cell_xml(LOADED_END_CELL, loaded_end),
            cell_xml(LAST_SUCCESSFUL_UPDATE_CELL, last_successful_update),
        ]
    )

    header_cells = "".join(
        cell_xml(
            f"{chr(ord('A') + index)}{REPORT_HEADER_ROW}",
            header,
        )
        for index, header in enumerate(REPORT_HEADERS)
    )
    data_cells = []
    for offset, item in enumerate(report_rows):
        row_number = REPORT_FIRST_DATA_ROW + offset
        values = [
            item["number"],
            item["category"],
            item["brand"],
            item["nmi_id"],
            item["nomenclature_name"],
            item["opening_quantity"],
            item["opening_amount"],
            item["intake_quantity"],
            item["intake_amount"],
            item["ending_quantity"],
            item["ending_amount"],
        ]
        data_cells.append(
            "".join(
                cell_xml(f"{chr(ord('A') + index)}{row_number}", value)
                for index, value in enumerate(values)
            )
        )

    formulas = subtotal_formulas(data_count)
    total_cells = [cell_xml(f"A{totals_row}", "ИТОГО")]
    for column in TOTAL_COLUMNS:
        total_value = sum(
            float(
                item[
                    {
                        "F": "opening_quantity",
                        "G": "opening_amount",
                        "H": "intake_quantity",
                        "I": "intake_amount",
                        "J": "ending_quantity",
                        "K": "ending_amount",
                    }[column]
                ]
            )
            for item in report_rows
        )
        total_cells.append(
            f'<c r="{column}{totals_row}"><f>'
            f'{escape(formulas[column].lstrip("="))}'
            f'</f><v>{total_value}</v></c>'
        )

    workbook_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="{PARAMETERS_SHEET_NAME}" sheetId="1" r:id="rId1"/>
    <sheet name="{REPORT_SHEET_NAME}" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>
'''
    workbook_rels_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="worksheet" Target="worksheets/sheet2.xml"/>
</Relationships>
'''
    parameters_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData><row>{parameter_cells}</row></sheetData>
</worksheet>
'''
    merge_cells_xml = "".join(
        f'<mergeCell ref="{range_ref}"/>'
        for range_ref in REPORT_REQUIRED_MERGES
    )
    report_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheetData>
    <row>{cell_xml("A1", "Отчет движения товара")}</row>
    <row>{cell_xml(REPORT_LOADED_START_CELL, loaded_start)}{cell_xml(REPORT_LOADED_END_CELL, loaded_end)}</row>
    <row>{header_cells}</row>
    {''.join(f'<row>{item}</row>' for item in data_cells)}
    <row>{''.join(total_cells)}</row>
  </sheetData>
  <mergeCells count="{len(REPORT_REQUIRED_MERGES)}">{merge_cells_xml}</mergeCells>
  <tableParts count="1"><tablePart r:id="rId1"/></tableParts>
</worksheet>
'''
    report_rels_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="table" Target="../tables/table1.xml"/>
</Relationships>
'''
    table_columns = "".join(
        f'<tableColumn id="{index + 1}" name="{escape(header)}"/>'
        for index, header in enumerate(REPORT_HEADERS)
    )
    table_ref = f"A{REPORT_HEADER_ROW}:{REPORT_LAST_COLUMN}{table_last_row}"
    table_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 id="1" name="{REPORT_TABLE_NAME}" displayName="{REPORT_TABLE_NAME}"
 ref="{table_ref}" totalsRowShown="0">
  <autoFilter ref="{table_ref}"/>
  <tableColumns count="{len(REPORT_HEADERS)}">{table_columns}</tableColumns>
</table>
'''
    styles_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <numFmts count="2">
    <numFmt numFmtId="164" formatCode="dd.mm.yyyy"/>
    <numFmt numFmtId="165" formatCode="dd.mm.yyyy hh:mm"/>
  </numFmts>
  <cellXfs count="3">
    <xf numFmtId="0"/>
    <xf numFmtId="164" applyNumberFormat="1"/>
    <xf numFmtId="165" applyNumberFormat="1"/>
  </cellXfs>
</styleSheet>
'''

    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", parameters_xml)
        archive.writestr("xl/worksheets/sheet2.xml", report_xml)
        archive.writestr(
            "xl/worksheets/_rels/sheet2.xml.rels",
            report_rels_xml,
        )
        archive.writestr("xl/tables/table1.xml", table_xml)
        archive.writestr("xl/styles.xml", styles_xml)
