"""Stable workbook contract for the permanent inventory report."""

from __future__ import annotations

import posixpath
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


PARAMETERS_SHEET_NAME = "Параметры"
REPORT_SHEET_NAME = "Отчет движения товара"

REQUESTED_START_CELL = "B4"
REQUESTED_END_CELL = "B5"
LOADED_START_CELL = "B8"
LOADED_END_CELL = "B9"
LAST_SUCCESSFUL_UPDATE_CELL = "B10"
DATE_NUMBER_FORMAT = "dd.mm.yyyy"
DATETIME_NUMBER_FORMAT = "dd.mm.yyyy hh:mm"

REPORT_LOADED_START_CELL = "C3"
REPORT_LOADED_END_CELL = "E3"
REPORT_HEADER_ROW = 8
REPORT_FIRST_DATA_ROW = REPORT_HEADER_ROW + 1
REPORT_TABLE_NAME = "InventoryMovementTable"
REPORT_LAST_COLUMN = "K"
REPORT_TOTAL_LABEL_END_COLUMN = "E"

REPORT_HEADERS = (
    "№",
    "Категория",
    "Артикул ИТ",
    "Бренд",
    "Название номенклатуры",
    "Остаток на начало, количество",
    "Остаток на начало, сумма",
    "Приход, количество",
    "Приход, сумма",
    "Остаток на конец, количество",
    "Остаток на конец, сумма",
)

REPORT_GROUP_HEADERS = (
    ("F7:G7", "F7", "Остаток на начало"),
    ("H7:I7", "H7", "Приход"),
    ("J7:K7", "J7", "Остаток на конец"),
)
REPORT_REQUIRED_MERGES = (
    f"A1:{REPORT_LAST_COLUMN}1",
    "A3:B3",
    *(item[0] for item in REPORT_GROUP_HEADERS),
)
TOTAL_COLUMNS = ("F", "G", "H", "I", "J", "K")
QUANTITY_COLUMNS = ("F", "H", "J")
AMOUNT_COLUMNS = ("G", "I", "K")
NUMERIC_COLUMNS = ("A", "C", *TOTAL_COLUMNS)
WRAPPED_TEXT_COLUMNS = ("B", "D", "E")

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_REL_NS = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
PACKAGE_REL_NS = (
    "http://schemas.openxmlformats.org/package/2006/relationships"
)


class WorkbookContractError(ValueError):
    """The workbook does not satisfy the permanent report contract."""


@dataclass(frozen=True)
class InventoryWorkbookState:
    requested_start: date
    requested_end: date
    loaded_start: date
    loaded_end: date
    last_successful_update: datetime


def table_end_row(data_row_count: int) -> int:
    if data_row_count < 0:
        raise ValueError("Количество строк отчёта не может быть отрицательным.")
    return REPORT_HEADER_ROW + max(data_row_count, 1)


def total_row(data_row_count: int) -> int:
    return table_end_row(data_row_count) + 1


def subtotal_formulas(data_row_count: int) -> dict[str, str]:
    end_row = table_end_row(data_row_count)
    return {
        column: (
            f"=SUBTOTAL(109,{column}{REPORT_FIRST_DATA_ROW}:"
            f"{column}{end_row})"
        )
        for column in TOTAL_COLUMNS
    }


def validate_requested_period(
    start: date,
    end: date,
    *,
    reference_date: date | None = None,
) -> None:
    if isinstance(start, datetime) or not isinstance(start, date):
        raise WorkbookContractError("Дата начала должна быть датой Excel.")
    if isinstance(end, datetime) or not isinstance(end, date):
        raise WorkbookContractError("Дата окончания должна быть датой Excel.")
    if start > end:
        raise WorkbookContractError(
            "Дата начала не может быть позже даты окончания."
        )
    today = reference_date or date.today()
    if end > today:
        raise WorkbookContractError(
            "Дата окончания не может быть в будущем."
        )


def _normalize_sheet_target(target: str) -> str:
    normalized = target.replace("\\", "/").lstrip("/")
    if normalized.startswith("xl/"):
        return posixpath.normpath(normalized)
    return posixpath.normpath(posixpath.join("xl", normalized))


def _worksheet_path(
    archive: zipfile.ZipFile,
    sheet_name: str,
) -> str:
    ns = {"m": MAIN_NS}
    rel_ns = {"r": PACKAGE_REL_NS}
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    sheets = workbook.find("m:sheets", ns)
    if sheets is None:
        raise WorkbookContractError("В XLSX отсутствует список листов.")

    sheet = next(
        (
            item
            for item in sheets
            if item.attrib.get("name") == sheet_name
        ),
        None,
    )
    if sheet is None:
        raise WorkbookContractError(
            f"В XLSX отсутствует лист «{sheet_name}»."
        )

    relationship_id = sheet.attrib.get(f"{{{OFFICE_REL_NS}}}id")
    relationships = ET.fromstring(
        archive.read("xl/_rels/workbook.xml.rels")
    )
    target = next(
        (
            item.attrib.get("Target")
            for item in relationships.findall("r:Relationship", rel_ns)
            if item.attrib.get("Id") == relationship_id
        ),
        None,
    )
    if not target:
        raise WorkbookContractError(
            f"В XLSX не найден XML листа «{sheet_name}»."
        )
    return _normalize_sheet_target(target)


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    ns = {"m": MAIN_NS}
    shared_xml = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.findall(".//m:t", ns))
        for item in shared_xml.findall("m:si", ns)
    ]


def _worksheet_cells(
    archive: zipfile.ZipFile,
    sheet_name: str,
) -> dict[str, tuple[str | None, str, int | None]]:
    ns = {"m": MAIN_NS}
    sheet_xml = ET.fromstring(
        archive.read(_worksheet_path(archive, sheet_name))
    )
    shared = _shared_strings(archive)
    cells: dict[str, tuple[str | None, str, int | None]] = {}
    for cell in sheet_xml.findall(".//m:c", ns):
        ref = cell.attrib.get("r")
        if not ref:
            continue
        cell_type = cell.attrib.get("t")
        if cell_type == "inlineStr":
            value = "".join(
                node.text or "" for node in cell.findall(".//m:t", ns)
            )
        else:
            value_node = cell.find("m:v", ns)
            value = (
                value_node.text
                if value_node is not None and value_node.text is not None
                else ""
            )
            if cell_type == "s" and value:
                try:
                    value = shared[int(value)]
                except (IndexError, ValueError) as error:
                    raise WorkbookContractError(
                        f"Ячейка {sheet_name}!{ref} содержит неверную ссылку shared string."
                    ) from error
        style_index = (
            int(cell.attrib["s"])
            if "s" in cell.attrib
            else None
        )
        cells[ref] = (cell_type, value, style_index)
    return cells


def _number_format(
    archive: zipfile.ZipFile,
    style_index: int | None,
) -> str | None:
    if style_index is None:
        return None
    ns = {"m": MAIN_NS}
    styles = ET.fromstring(archive.read("xl/styles.xml"))
    cell_xfs = styles.findall(".//m:cellXfs/m:xf", ns)
    try:
        number_format_id = int(cell_xfs[style_index].attrib["numFmtId"])
    except (IndexError, KeyError, ValueError) as error:
        raise WorkbookContractError(
            "XLSX содержит неверную ссылку на стиль даты."
        ) from error
    custom_formats = {
        int(item.attrib["numFmtId"]): item.attrib["formatCode"]
        for item in styles.findall(".//m:numFmts/m:numFmt", ns)
    }
    return custom_formats.get(number_format_id, str(number_format_id))


def _excel_datetime(
    cells: dict[str, tuple[str | None, str, int | None]],
    ref: str,
    label: str,
) -> datetime:
    cell_type, value, _ = cells.get(ref, (None, "", None))
    if not value:
        raise WorkbookContractError(f"Не заполнено поле «{label}».")
    if cell_type in {"s", "str", "inlineStr"}:
        raise WorkbookContractError(
            f"Поле «{label}» должно быть настоящей датой Excel, а не текстом."
        )
    if cell_type == "d":
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(
                tzinfo=None
            )
        except ValueError as error:
            raise WorkbookContractError(
                f"Поле «{label}» содержит некорректную дату."
            ) from error
    try:
        return datetime(1899, 12, 30) + timedelta(days=float(value))
    except (TypeError, ValueError, OverflowError) as error:
        raise WorkbookContractError(
            f"Поле «{label}» содержит некорректную дату."
        ) from error


def read_inventory_workbook_state(
    workbook_path: Path,
    *,
    reference_date: date | None = None,
) -> InventoryWorkbookState:
    path = Path(workbook_path)
    try:
        with zipfile.ZipFile(path) as archive:
            cells = _worksheet_cells(archive, PARAMETERS_SHEET_NAME)
            date_formats = {
                ref: _number_format(
                    archive,
                    cells.get(ref, (None, "", None))[2],
                )
                for ref in (
                    REQUESTED_START_CELL,
                    REQUESTED_END_CELL,
                    LOADED_START_CELL,
                    LOADED_END_CELL,
                    LAST_SUCCESSFUL_UPDATE_CELL,
                )
            }
    except WorkbookContractError:
        raise
    except (FileNotFoundError, PermissionError, zipfile.BadZipFile, KeyError, ET.ParseError) as error:
        raise WorkbookContractError(
            "Не удалось прочитать параметры из XLSX."
        ) from error

    requested_start = _excel_datetime(
        cells,
        REQUESTED_START_CELL,
        "Дата начала",
    ).date()
    requested_end = _excel_datetime(
        cells,
        REQUESTED_END_CELL,
        "Дата окончания",
    ).date()
    loaded_start = _excel_datetime(
        cells,
        LOADED_START_CELL,
        "Начало загруженного периода",
    ).date()
    loaded_end = _excel_datetime(
        cells,
        LOADED_END_CELL,
        "Конец загруженного периода",
    ).date()
    last_successful_update = _excel_datetime(
        cells,
        LAST_SUCCESSFUL_UPDATE_CELL,
        "Последнее успешное обновление",
    )

    for ref in (
        REQUESTED_START_CELL,
        REQUESTED_END_CELL,
        LOADED_START_CELL,
        LOADED_END_CELL,
    ):
        if date_formats[ref] != DATE_NUMBER_FORMAT:
            raise WorkbookContractError(
                f"Ячейка {PARAMETERS_SHEET_NAME}!{ref} не имеет формата даты."
            )
    if date_formats[LAST_SUCCESSFUL_UPDATE_CELL] != DATETIME_NUMBER_FORMAT:
        raise WorkbookContractError(
            f"Ячейка {PARAMETERS_SHEET_NAME}!{LAST_SUCCESSFUL_UPDATE_CELL} "
            "не имеет формата даты и времени."
        )

    validate_requested_period(
        requested_start,
        requested_end,
        reference_date=reference_date,
    )
    if loaded_start > loaded_end:
        raise WorkbookContractError(
            "Начало загруженного периода позже его окончания."
        )

    return InventoryWorkbookState(
        requested_start=requested_start,
        requested_end=requested_end,
        loaded_start=loaded_start,
        loaded_end=loaded_end,
        last_successful_update=last_successful_update,
    )


def workbook_contract_payload(
    *,
    data_row_count: int,
) -> dict[str, Any]:
    return {
        "parametersSheet": PARAMETERS_SHEET_NAME,
        "reportSheet": REPORT_SHEET_NAME,
        "requestedStartCell": REQUESTED_START_CELL,
        "requestedEndCell": REQUESTED_END_CELL,
        "loadedStartCell": LOADED_START_CELL,
        "loadedEndCell": LOADED_END_CELL,
        "lastSuccessfulUpdateCell": LAST_SUCCESSFUL_UPDATE_CELL,
        "dateNumberFormat": DATE_NUMBER_FORMAT,
        "dateTimeNumberFormat": DATETIME_NUMBER_FORMAT,
        "reportLoadedStartCell": REPORT_LOADED_START_CELL,
        "reportLoadedEndCell": REPORT_LOADED_END_CELL,
        "headerRow": REPORT_HEADER_ROW,
        "firstDataRow": REPORT_FIRST_DATA_ROW,
        "tableEndRow": table_end_row(data_row_count),
        "totalRow": total_row(data_row_count),
        "tableName": REPORT_TABLE_NAME,
        "lastColumn": REPORT_LAST_COLUMN,
        "totalLabelEndColumn": REPORT_TOTAL_LABEL_END_COLUMN,
        "headers": list(REPORT_HEADERS),
        "groupHeaders": [
            {"range": range_ref, "cell": cell_ref, "label": label}
            for range_ref, cell_ref, label in REPORT_GROUP_HEADERS
        ],
        "totalColumns": list(TOTAL_COLUMNS),
        "quantityColumns": list(QUANTITY_COLUMNS),
        "amountColumns": list(AMOUNT_COLUMNS),
        "wrappedTextColumns": list(WRAPPED_TEXT_COLUMNS),
        "totalFormulas": subtotal_formulas(data_row_count),
    }
