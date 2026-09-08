"""Generate the read-only CRM inventory movement report as an Excel workbook."""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse
from xml.etree import ElementTree as ET

from playwright.async_api import BrowserContext, Error as PlaywrightError, Page, async_playwright


BASE_URL = "https://it.mokryinos.ru/"
REPO_ROOT = Path(__file__).resolve().parents[1]
AUTH_FILE = REPO_ROOT / "auth.json"
AUTO_LOGIN = REPO_ROOT / "tools" / "auto_login_crm.py"

# These identifiers and names were verified in the CRM before implementation.
ORGANIZATION_ID = "473"
ORGANIZATION_NAME = "ИП Калашникова Т.А."
FILIAL_ID = "770"
FILIAL_NAME = "Ф_Наташи Ковшовой, д. 8 к.1"
SHOP_ID = "1181"
MAIN_STORE_ID = "1667"
MAIN_STORE_NAME = "Склад Ф_Наташи Ковшовой, д. 8 к.1"
MAIN_STORE_TYPE_ID = "1"

NODE_EXE_ENV = "CODEX_ARTIFACT_NODE"
NODE_MODULES_ENV = "CODEX_ARTIFACT_NODE_MODULES"
DEFAULT_NODE_EXE = (
    Path.home()
    / ".cache"
    / "codex-runtimes"
    / "codex-primary-runtime"
    / "dependencies"
    / "node"
    / "bin"
    / "node.exe"
)
DEFAULT_NODE_MODULES = DEFAULT_NODE_EXE.parents[1] / "node_modules"

ZERO = Decimal("0")
PROCUREMENT_TOTAL_TOLERANCE = Decimal("0.01")
DATE_RE = re.compile(r"\b(\d{2}\.\d{2}\.\d{4})\b")
CARD_LINK_RE = re.compile(r"/nomenclatureFranchisee/(\d+)")
INTAKE_LINK_RE = re.compile(r"/intake/(\d+)(?:\D|$)")
PROVIDER_NAME_RE = re.compile(r"^NomenclatureProviderNew\[(\d+)]\[provider_id]$")
PROVIDER_FIELD_RE = re.compile(
    r"^NomenclatureProviderNew\[(\d+)]\[(articul|cities|filials)](?:\[\])?$"
)
NMI_ID_RE = re.compile(r"^NomenclatureMeasureItem\[(\d+)]\[id]$")


class ReportError(RuntimeError):
    """A clear, user-facing report generation failure."""


class AuthExpired(ReportError):
    """The CRM session is absent or expired."""


@dataclass
class BalanceValue:
    quantity: Decimal = ZERO
    amount: Decimal = ZERO
    nomenclature_id: int | None = None


@dataclass
class ProductMeta:
    nomenclature_id: int
    nmi_ids: set[int]
    parent_id: int
    parent_name: str
    brand: str
    suppliers: list[str]
    has_supplier_restrictions: bool = False
    category: str = ""


@dataclass
class IntakeDocument:
    document_id: int
    document_date: date
    status: str
    store: str
    organization: str


@dataclass
class IntakeAggregate:
    values: dict[int, BalanceValue] = field(default_factory=dict)
    line_count: int = 0
    document_count: int = 0


@dataclass(frozen=True)
class ProcurementControl:
    item_rows_amount: Decimal
    item_row_count: int
    server_total: Decimal | None


@dataclass(frozen=True)
class InventoryMovementReportResult:
    output_path: Path
    start_date: date
    end_date: date
    brand: str | None
    category: str | None
    row_count: int
    intake_document_count: int
    intake_quantity: Decimal
    intake_amount: Decimal
    procurement_item_rows_amount: Decimal | None
    procurement_server_total: Decimal | None
    verified: bool


@dataclass(frozen=True)
class ReportControls:
    opening_item_count: int
    intake_item_count: int
    ending_item_count: int
    union_item_count: int
    row_count: int
    intake_document_count: int
    intake_line_count: int
    intake_quantity: Decimal
    intake_amount: Decimal
    opening_amount: Decimal
    ending_amount: Decimal
    procurement_item_row_count: int | None
    procurement_item_rows_amount: Decimal | None
    procurement_server_total: Decimal | None
    procurement_difference: Decimal | None


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def parse_decimal(value: Any, *, field_name: str) -> Decimal:
    if value is None or value == "":
        return ZERO
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    normalized = str(value).replace("\xa0", " ").replace(" ", "").replace(",", ".")
    normalized = re.sub(r"[^0-9.\-]", "", normalized)
    try:
        return Decimal(normalized)
    except InvalidOperation as error:
        raise ReportError(f"CRM вернула некорректное число в поле {field_name}: {value!r}") from error


def crm_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("ожидается дата в формате YYYY-MM-DD") from error


def route_url(route: str, params: list[tuple[str, str]] | None = None) -> str:
    url = urljoin(BASE_URL, route)
    if urlparse(url).netloc != urlparse(BASE_URL).netloc:
        raise ReportError(f"Запрещён внешний URL: {url}")
    if params:
        url += "?" + urlencode(params, doseq=True)
    return url


def unwrap_ajax_body(body: str) -> str:
    stripped = body.lstrip()
    if not stripped.startswith(("{", "[")):
        return body
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body
    if isinstance(payload, dict):
        content = payload.get("content")
        if isinstance(content, str):
            return content
    return body


def ensure_not_login(url: str, body: str = "") -> None:
    lower_url = url.lower()
    lower_body = body[:15000].lower()
    if "/login" in lower_url or "name=\"loginform[password]\"" in lower_body:
        raise AuthExpired("Сессия CRM истекла.")


def extract_localdata(body: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"localdata\s*:\s*", body, re.IGNORECASE):
        start = match.end()
        while start < len(body) and body[start].isspace():
            start += 1
        if start >= len(body) or body[start] not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(body[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            return [value]
    raise ReportError("CRM-карточка не содержит ожидаемый массив строк localdata.")


class ProductCardParser(HTMLParser):
    """Single-pass parser for the relevant controls in a large CRM product form."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.div_depth = 0
        self.groups: list[tuple[int, list[str]]] = []
        self.in_label = False
        self.label_group: list[str] | None = None
        self.select: dict[str, Any] | None = None
        self.option: dict[str, Any] | None = None
        self.nmi_ids: set[int] = set()
        self.parent_id: int | None = None
        self.parent_name = ""
        self.brand = ""
        self.providers: dict[int, dict[str, Any]] = defaultdict(
            lambda: {"provider": "", "articul": "", "cities": [], "filials": []}
        )

    def current_label(self) -> str:
        if not self.groups:
            return ""
        return clean_text("".join(self.groups[-1][1]))

    def handle_starttag(self, tag: str, attrs_raw: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_raw}
        if tag == "div":
            self.div_depth += 1
            classes = set(attrs.get("class", "").split())
            if "form-group" in classes:
                self.groups.append((self.div_depth, []))
            return
        if tag == "label":
            self.in_label = True
            self.label_group = self.groups[-1][1] if self.groups else None
            return
        if tag == "input":
            self._record_input(attrs)
            return
        if tag == "select":
            self.select = {
                "name": attrs.get("name", ""),
                "id": attrs.get("id", ""),
                "label": self.current_label(),
                "selected": [],
            }
            return
        if tag == "option" and self.select is not None:
            self.option = {
                "selected": "selected" in attrs,
                "value": attrs.get("value", ""),
                "text": [],
            }

    def handle_data(self, data: str) -> None:
        if self.in_label and self.label_group is not None:
            self.label_group.append(data)
        if self.option is not None:
            self.option["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "label":
            self.in_label = False
            self.label_group = None
            return
        if tag == "option" and self.option is not None and self.select is not None:
            if self.option["selected"]:
                self.select["selected"].append(
                    (self.option["value"], clean_text("".join(self.option["text"])))
                )
            self.option = None
            return
        if tag == "select" and self.select is not None:
            self._record_select(self.select)
            self.select = None
            self.option = None
            return
        if tag == "div":
            if self.groups and self.groups[-1][0] == self.div_depth:
                self.groups.pop()
            self.div_depth = max(0, self.div_depth - 1)

    def _record_input(self, attrs: dict[str, str]) -> None:
        name = attrs.get("name", "")
        value = attrs.get("value", "")
        nmi_match = NMI_ID_RE.match(name)
        if nmi_match and value.isdigit():
            self.nmi_ids.add(int(value))
            return
        provider_match = PROVIDER_FIELD_RE.match(name)
        if provider_match:
            index = int(provider_match.group(1))
            field_name = provider_match.group(2)
            if field_name == "articul":
                self.providers[index]["articul"] = clean_text(value)
            elif value:
                self.providers[index][field_name].append(clean_text(value))

    def _record_select(self, select: dict[str, Any]) -> None:
        name = select["name"]
        selected = select["selected"]
        if name == "Nomenclature[parent_id]" and selected:
            value, label = selected[0]
            if value.isdigit():
                self.parent_id = int(value)
            self.parent_name = label
            return
        if clean_text(select["label"]).casefold().startswith("бренд"):
            if selected and selected[0][0] and selected[0][1].casefold() != "выбрать":
                self.brand = selected[0][1]
            else:
                # The CRM reports expose this same empty-property case as
                # the real filter value «Неизвестный бренд» (id=-1).
                self.brand = "Неизвестный бренд"
            return
        provider_match = PROVIDER_NAME_RE.match(name)
        if provider_match and selected:
            self.providers[int(provider_match.group(1))]["provider"] = selected[0][1]
            return
        provider_field = PROVIDER_FIELD_RE.match(name)
        if provider_field:
            index = int(provider_field.group(1))
            field_name = provider_field.group(2)
            if field_name in ("cities", "filials"):
                self.providers[index][field_name].extend(
                    clean_text(label) or clean_text(value) for value, label in selected
                )


class BreadcrumbParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ul_depth = 0
        self.in_breadcrumb = False
        self.in_li = False
        self.current_li: list[str] = []
        self.current: list[str] = []
        self.breadcrumbs: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs_raw: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_raw}
        if tag in {"ul", "ol"}:
            self.ul_depth += 1
            if "breadcrumb" in attrs.get("class", "").split():
                self.in_breadcrumb = True
                self.current = []
        elif tag == "li" and self.in_breadcrumb:
            self.in_li = True
            self.current_li = []

    def handle_data(self, data: str) -> None:
        if self.in_li:
            self.current_li.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "li" and self.in_li:
            text = clean_text("".join(self.current_li))
            if text:
                self.current.append(text)
            self.in_li = False
        elif tag in {"ul", "ol"}:
            if self.in_breadcrumb:
                self.breadcrumbs.append(self.current)
                self.in_breadcrumb = False
            self.ul_depth = max(0, self.ul_depth - 1)


async def install_readonly_guard(context: BrowserContext) -> None:
    async def guard(route: Any) -> None:
        if route.request.method.upper() in {"GET", "HEAD", "OPTIONS"}:
            await route.continue_()
        else:
            await route.abort("blockedbyclient")

    await context.route("**/*", guard)


async def goto_readonly(page: Page, url: str, *, timeout: int = 180_000) -> None:
    response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    if response is None:
        raise ReportError(f"CRM не вернула ответ для {urlparse(url).path}.")
    if response.status >= 400:
        raise ReportError(f"CRM вернула HTTP {response.status} для {urlparse(url).path}.")
    ensure_not_login(page.url)


async def validate_store_configuration(page: Page) -> None:
    await goto_readonly(
        page,
        route_url(
            "/reports/storeRemain/index",
            [
                ("filters[organizationGroup][]", "3"),
                ("filters[organization][]", ORGANIZATION_ID),
                ("filters[filialType][]", "1"),
                ("filters[filial][]", FILIAL_ID),
                ("filters[storeType][]", MAIN_STORE_TYPE_ID),
            ],
        ),
    )
    values = await page.evaluate(
        """
        () => ({
          organization: document.querySelector('#filters_organization option[value="473"]')?.textContent?.trim() || '',
          filial: document.querySelector('#filters_filial option[value="770"]')?.textContent?.trim() || '',
          store: document.querySelector('#filters_store option[value="1667"]')?.textContent?.trim() || '',
          storeType: document.querySelector('#filters_storeType option[value="1"]')?.textContent?.trim() || '',
          normalStores: Array.from(document.querySelectorAll('#filters_store option')).filter(o => o.value).map(o => [o.value, o.textContent.trim()]),
        })
        """
    )
    expected = {
        "organization": ORGANIZATION_NAME,
        "filial": FILIAL_NAME,
        "store": MAIN_STORE_NAME,
        "storeType": "Основной склад",
    }
    for key, expected_value in expected.items():
        if clean_text(values.get(key)) != expected_value:
            raise ReportError(
                f"Конфигурация CRM изменилась: {key}={values.get(key)!r}, ожидалось {expected_value!r}."
            )
    normal_stores = values.get("normalStores") or []
    if normal_stores != [[MAIN_STORE_ID, MAIN_STORE_NAME]]:
        raise ReportError(
            "У филиала найден неоднозначный набор обычных складов; генератор не будет угадывать способ агрегации: "
            + repr(normal_stores)
        )


def flatten_grid_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    stack = list(reversed(rows))
    while stack:
        row = stack.pop()
        result.append(row)
        children = row.get("records") or row.get("children") or []
        if isinstance(children, list):
            stack.extend(reversed([child for child in children if isinstance(child, dict)]))
    return result


async def fetch_snapshot(page: Page, snapshot_date: date, label: str) -> dict[int, BalanceValue]:
    params = [
        ("showReport", "1"),
        ("filters[dateEnd]", crm_date(snapshot_date)),
        ("filters[reportMode]", "1"),
        ("filters[reportGroupBy]", "nomenclature_item"),
        ("filters[organizationGroup][]", "3"),
        ("filters[organization][]", ORGANIZATION_ID),
        ("filters[filialType][]", "1"),
        ("filters[filial][]", FILIAL_ID),
        ("filters[storeType][]", MAIN_STORE_TYPE_ID),
        ("filters[store][]", MAIN_STORE_ID),
    ]
    try:
        async with page.expect_response(
            lambda response: "/reports/storeRemain/list" in response.url,
            timeout=180_000,
        ) as response_info:
            await goto_readonly(page, route_url("/reports/storeRemain/index", params))
        list_response = await response_info.value
        list_body = await list_response.text()
        ensure_not_login(list_response.url, list_body)
        if list_response.status >= 400:
            raise ReportError(
                f"CRM вернула HTTP {list_response.status} для {label} снимка остатков."
            )
    except ReportError:
        raise
    except Exception as error:
        raise ReportError(f"Не удалось получить {label} снимок остатков из CRM.") from error
    try:
        await page.wait_for_function(
            """
            () => {
              try {
                const rows = window.jQuery('#grid').jqxTreeGrid('getRows');
                return Array.isArray(rows);
              } catch (_) { return false; }
            }
            """,
            timeout=180_000,
        )
        await page.wait_for_timeout(500)
    except Exception as error:
        raise ReportError(f"Не удалось получить {label} снимок остатков из CRM.") from error
    raw_rows = await page.evaluate("() => window.jQuery('#grid').jqxTreeGrid('getRows')")
    result: dict[int, BalanceValue] = {}
    for row in flatten_grid_rows(raw_rows):
        if row.get("is_folder") or row.get("is_total"):
            continue
        articul = row.get("articul")
        if articul in (None, ""):
            continue
        try:
            nmi_id = int(articul)
        except (TypeError, ValueError) as error:
            raise ReportError(f"Некорректный Артикул ИТ в {label} снимке: {articul!r}") from error
        card_match = CARD_LINK_RE.search(str(row.get("group_name") or row.get("name") or ""))
        nomenclature_id = int(card_match.group(1)) if card_match else None
        value = result.setdefault(nmi_id, BalanceValue(nomenclature_id=nomenclature_id))
        if value.nomenclature_id not in (None, nomenclature_id):
            raise ReportError(f"Артикул ИТ {nmi_id} связан с разными карточками номенклатуры.")
        value.nomenclature_id = value.nomenclature_id or nomenclature_id
        value.quantity += parse_decimal(row.get("quantity"), field_name=f"{label}.quantity")
        value.amount += parse_decimal(row.get("amount"), field_name=f"{label}.amount")
    print(f"{label.capitalize()} снимок ({crm_date(snapshot_date)}): {len(result)} товаров", flush=True)
    return result


async def collect_intake_documents(page: Page, start: date, end: date) -> list[IntakeDocument]:
    base_params = [
        ("IntakeDocument[date]", f"{crm_date(start)} - {crm_date(end)}"),
        ("IntakeDocument[organizationId]", ORGANIZATION_ID),
        ("IntakeDocument[store_id_in]", MAIN_STORE_ID),
        ("IntakeDocument[status]", "2"),
        ("pageSize", "500"),
    ]
    pending = [route_url("/intake/index", base_params)]
    visited: set[str] = set()
    documents: dict[int, IntakeDocument] = {}
    headers_seen = False
    while pending:
        url = pending.pop(0)
        if url in visited:
            continue
        visited.add(url)
        await goto_readonly(page, url)
        table_headers = [clean_text(item) for item in await page.locator("table thead th").all_text_contents()]
        if "Дата" in table_headers and "Статус" in table_headers:
            headers_seen = True
        rows = await page.locator("table tbody tr[data-key]").evaluate_all(
            """
            rows => rows.map(row => ({
              cells: Array.from(row.querySelectorAll('td')).map(cell => cell.textContent.trim()),
              links: Array.from(row.querySelectorAll('a[href]')).map(link => link.getAttribute('href')),
            }))
            """
        )
        for row in rows:
            link = next((item for item in row["links"] if item and INTAKE_LINK_RE.search(item)), None)
            if not link:
                continue
            match = INTAKE_LINK_RE.search(link)
            assert match is not None
            document_id = int(match.group(1))
            cells = [clean_text(cell) for cell in row["cells"]]
            date_match = next((DATE_RE.search(cell) for cell in cells if DATE_RE.search(cell)), None)
            if date_match is None:
                raise ReportError(f"Не удалось определить дату intake-документа {document_id}.")
            document_date = datetime.strptime(date_match.group(1), "%d.%m.%Y").date()
            status = next((cell for cell in cells if cell in {"Сохранен", "Выполняется", "Проведен", "Удален"}), "")
            store = MAIN_STORE_NAME if MAIN_STORE_NAME in cells else ""
            organization = ORGANIZATION_NAME if ORGANIZATION_NAME in cells else ""
            if not (start <= document_date <= end):
                continue
            if status != "Проведен":
                continue
            if store != MAIN_STORE_NAME or organization != ORGANIZATION_NAME:
                raise ReportError(f"Intake-документ {document_id} относится не к подтверждённому магазину/складу.")
            documents[document_id] = IntakeDocument(
                document_id=document_id,
                document_date=document_date,
                status=status,
                store=store,
                organization=organization,
            )
        pager_hrefs = await page.locator(".pager a[href], ul.pagination a[href]").evaluate_all(
            "links => links.map(link => link.getAttribute('href'))"
        )
        for href in pager_hrefs:
            if not href or "IntakeDocument_page" not in href:
                continue
            next_url = urljoin(page.url, href)
            if next_url not in visited and next_url not in pending:
                pending.append(next_url)
    if not headers_seen:
        raise ReportError("Не удалось получить таблицу intake из CRM.")
    ordered = sorted(documents.values(), key=lambda item: (item.document_date, item.document_id))
    print(f"Проведённых intake-документов в периоде: {len(ordered)}", flush=True)
    return ordered


async def api_get_html(context: BrowserContext, url: str, *, ajax: bool = False) -> str:
    headers = {"X-Requested-With": "XMLHttpRequest"} if ajax else None
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            response = await context.request.get(url, headers=headers, timeout=180_000)
            body = await response.text()
            ensure_not_login(response.url, body)
            if response.status >= 500 and attempt < 4:
                await asyncio.sleep(attempt + 1)
                continue
            if response.status >= 400:
                raise ReportError(f"CRM вернула HTTP {response.status} для {urlparse(url).path}.")
            return unwrap_ajax_body(body)
        except AuthExpired:
            raise
        except ReportError:
            raise
        except PlaywrightError as error:
            last_error = error
            if attempt < 4:
                await asyncio.sleep(attempt + 1)
                continue
    raise ReportError(
        f"CRM пять раз прервала read-only GET {urlparse(url).path}; отчёт не создан."
    ) from last_error


async def fetch_intake_lines(
    context: BrowserContext, documents: list[IntakeDocument]
) -> tuple[IntakeAggregate, dict[int, int]]:
    aggregate = IntakeAggregate(document_count=len(documents))
    nmi_to_nomenclature: dict[int, int] = {}
    seen_lines: set[tuple[int, int]] = set()
    semaphore = asyncio.Semaphore(6)

    async def one(document: IntakeDocument) -> tuple[IntakeDocument, list[dict[str, Any]]]:
        async with semaphore:
            body = await api_get_html(
                context,
                route_url(f"/intake/{document.document_id}", [("_", "1")]),
                ajax=True,
            )
        if "Проведен" not in clean_text(re.sub(r"<[^>]+>", " ", body)):
            raise ReportError(f"Intake-документ {document.document_id} больше не имеет статус «Проведен».")
        return document, extract_localdata(body)

    results = await asyncio.gather(*(one(document) for document in documents))
    for document, rows in results:
        for row in rows:
            line_id_raw = row.get("id")
            nmi_raw = row.get("nomenclature_measure_item_id")
            if line_id_raw in (None, "") or nmi_raw in (None, ""):
                raise ReportError(f"В intake-документе {document.document_id} строка без устойчивого ID или NMI ID.")
            line_id = int(line_id_raw)
            nmi_id = int(nmi_raw)
            key = (document.document_id, line_id)
            if key in seen_lines:
                continue
            seen_lines.add(key)
            value = aggregate.values.setdefault(nmi_id, BalanceValue())
            value.quantity += parse_decimal(row.get("quantity"), field_name="intake.quantity")
            value.amount += parse_decimal(row.get("amount"), field_name="intake.amount")
            aggregate.line_count += 1
            match = CARD_LINK_RE.search(str(row.get("nomenclature_name_link") or ""))
            if match:
                nomenclature_id = int(match.group(1))
                existing = nmi_to_nomenclature.get(nmi_id)
                if existing not in (None, nomenclature_id):
                    raise ReportError(f"NMI {nmi_id} связан с разными карточками в intake.")
                nmi_to_nomenclature[nmi_id] = nomenclature_id
    print(f"Уникальных intake lines: {aggregate.line_count}", flush=True)
    return aggregate, nmi_to_nomenclature


def parse_product_card(body: str, nomenclature_id: int) -> ProductMeta:
    parser = ProductCardParser()
    parser.feed(body)
    if not parser.nmi_ids:
        raise ReportError(f"Карточка номенклатуры {nomenclature_id} не содержит NMI ID.")
    if parser.parent_id is None or not parser.parent_name:
        raise ReportError(f"Карточка номенклатуры {nomenclature_id} не содержит подтверждённую иерархию.")
    if not parser.brand:
        raise ReportError(f"Карточка номенклатуры {nomenclature_id} не содержит фактический бренд CRM.")
    pairs: set[str] = set()
    has_restrictions = False
    for row in parser.providers.values():
        provider = clean_text(row["provider"])
        supplier_articul = clean_text(row["articul"])
        if not provider or not supplier_articul:
            continue
        pairs.add(f"{provider} — {supplier_articul}")
        if any(clean_text(value) for value in row["cities"] + row["filials"]):
            has_restrictions = True
    return ProductMeta(
        nomenclature_id=nomenclature_id,
        nmi_ids=parser.nmi_ids,
        parent_id=parser.parent_id,
        parent_name=parser.parent_name,
        brand=parser.brand,
        suppliers=sorted(pairs, key=str.casefold),
        has_supplier_restrictions=has_restrictions,
    )


async def fetch_product_metadata(
    context: BrowserContext, nmi_to_nomenclature: dict[int, int]
) -> dict[int, ProductMeta]:
    nomenclature_ids = sorted(set(nmi_to_nomenclature.values()))
    semaphore = asyncio.Semaphore(6)
    completed = 0
    progress_lock = asyncio.Lock()

    async def one(nomenclature_id: int) -> ProductMeta:
        nonlocal completed
        async with semaphore:
            body = await api_get_html(
                context,
                route_url(f"/nomenclatureFranchisee/{nomenclature_id}", [("_", "1")]),
                ajax=True,
            )
        metadata = await asyncio.to_thread(parse_product_card, body, nomenclature_id)
        async with progress_lock:
            completed += 1
            if completed == len(nomenclature_ids) or completed % 100 == 0:
                print(f"Карточки номенклатуры: {completed}/{len(nomenclature_ids)}", flush=True)
        return metadata

    cards = await asyncio.gather(*(one(item) for item in nomenclature_ids))
    cards_by_id = {item.nomenclature_id: item for item in cards}
    result: dict[int, ProductMeta] = {}
    for nmi_id, nomenclature_id in nmi_to_nomenclature.items():
        metadata = cards_by_id[nomenclature_id]
        if nmi_id not in metadata.nmi_ids:
            raise ReportError(
                f"Карточка Nomenclature.id={nomenclature_id} не подтверждает NMI.id={nmi_id}."
            )
        result[nmi_id] = metadata
    return result


def category_from_breadcrumb(body: str, metadata: ProductMeta) -> str:
    parser = BreadcrumbParser()
    parser.feed(body)
    candidates = [items for items in parser.breadcrumbs if any(item == "Номенклатура" for item in items)]
    if not candidates:
        raise ReportError(f"Не удалось получить иерархию категории для родителя {metadata.parent_id}.")
    items = max(candidates, key=len)
    try:
        start_index = items.index("Номенклатура") + 1
    except ValueError as error:
        raise ReportError(f"Некорректная иерархия категории для родителя {metadata.parent_id}.") from error
    hierarchy = items[start_index:]
    if hierarchy and hierarchy[-1].casefold() == metadata.parent_name.casefold():
        if metadata.parent_name.casefold() == metadata.brand.casefold() and len(hierarchy) > 1:
            hierarchy = hierarchy[:-1]
    if not hierarchy:
        hierarchy = [metadata.parent_name]
    return " / ".join(hierarchy)


async def fill_categories(context: BrowserContext, metadata_by_nmi: dict[int, ProductMeta]) -> None:
    unique: dict[int, ProductMeta] = {}
    for metadata in metadata_by_nmi.values():
        unique.setdefault(metadata.parent_id, metadata)
    semaphore = asyncio.Semaphore(12)

    async def one(parent_id: int, sample: ProductMeta) -> tuple[int, str]:
        async with semaphore:
            body = await api_get_html(
                context,
                route_url("/nomenclatureFranchisee/index", [("Nomenclature[parent_id]", str(parent_id))]),
            )
        return parent_id, category_from_breadcrumb(body, sample)

    categories = dict(await asyncio.gather(*(one(parent_id, sample) for parent_id, sample in unique.items())))
    for metadata in metadata_by_nmi.values():
        metadata.category = categories[metadata.parent_id]
    print(f"Ветвей номенклатурной иерархии: {len(categories)}", flush=True)


def parse_html_number(value: Any) -> Decimal:
    text = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    return parse_decimal(clean_text(text), field_name="procurement.amount")


async def fetch_procurement_control(
    page: Page, start: date, end: date
) -> ProcurementControl | None:
    params = [
        ("showReport", "1"),
        ("filters[dateRange]", f"{crm_date(start)} - {crm_date(end)}"),
        ("filters[reportMode]", "1"),
        ("filters[periodicity]", "1"),
        ("filters[reportGroupBy]", "nomenclature_item"),
        ("filters[filial][]", FILIAL_ID),
        ("filters[organizationGroup][]", "3"),
        ("filters[organization][]", ORGANIZATION_ID),
        ("filters[shopType][]", "1"),
        ("filters[multipleShops][]", SHOP_ID),
        ("filters[reportResultBy]", "amount"),
    ]
    try:
        async with page.expect_response(
            lambda response: "/reports/procurement/list" in response.url,
            timeout=180_000,
        ) as response_info:
            await goto_readonly(page, route_url("/reports/procurement/index", params))
        list_response = await response_info.value
        if list_response.status >= 400:
            raise ReportError(f"CRM вернула HTTP {list_response.status} для контрольного отчёта закупок.")
        await page.wait_for_function(
            """
            () => {
              try { return Array.isArray(window.jQuery('#grid').jqxTreeGrid('getRows')); }
              catch (_) { return false; }
            }
            """,
            timeout=180_000,
        )
        await page.wait_for_timeout(500)
        rows = await page.evaluate("() => window.jQuery('#grid').jqxTreeGrid('getRows')")
    except AuthExpired:
        raise
    except Exception as error:
        print(f"Предупреждение: контроль /reports/procurement/index недоступен: {error}", flush=True)
        return None

    item_rows: list[dict[str, Any]] = []
    service_rows: list[dict[str, Any]] = []
    for row in flatten_grid_rows(rows):
        if row.get("articul") not in (None, ""):
            item_rows.append(row)
        else:
            service_rows.append(row)

    server_total: Decimal | None = None
    for row in service_rows:
        row_id = row.get("id")
        row_name = clean_text(html.unescape(re.sub(r"<[^>]+>", " ", str(row.get("name") or ""))))
        if str(row_id) == "-2" and row_name.casefold() == "итого" and server_total is None:
            server_total = parse_html_number(row.get("range_0"))
            continue
        identifying_fields = {
            key: row.get(key)
            for key in ("id", "name", "articul", "nomenclature_id", "group_name", "uid")
            if key in row
        }
        raise ReportError(
            "Контроль procurement вернул неожиданную нетоварную строку: "
            f"id={row_id!r}, identifying_fields={identifying_fields!r}, "
            f"available_fields={sorted(row)}."
        )

    item_rows_amount = sum(
        (parse_html_number(row.get("range_0")) for row in item_rows),
        ZERO,
    )
    if server_total is None:
        print(
            "Предупреждение: контроль procurement не вернул ожидаемую серверную строку «Итого» "
            "(id=-2); сумма рассчитана только по товарным строкам.",
            flush=True,
        )
    elif abs(item_rows_amount - server_total) > PROCUREMENT_TOTAL_TOLERANCE:
        raise ReportError(
            "Контроль procurement: сумма товарных строк не совпала с серверной строкой «Итого»: "
            f"item rows={item_rows_amount:.6f}, server total={server_total:.6f}, "
            f"tolerance={PROCUREMENT_TOTAL_TOLERANCE:.2f}."
        )
    return ProcurementControl(
        item_rows_amount=item_rows_amount,
        item_row_count=len(item_rows),
        server_total=server_total,
    )


def run_auto_login() -> None:
    if not AUTO_LOGIN.exists():
        raise ReportError(f"Не найден безопасный скрипт авторизации: {AUTO_LOGIN}")
    print("Сессия CRM отсутствует или истекла; запускаю безопасный auto_login_crm.py...", flush=True)
    completed = subprocess.run([sys.executable, str(AUTO_LOGIN)], cwd=REPO_ROOT, check=False)
    if completed.returncode != 0 or not AUTH_FILE.exists():
        raise ReportError("Не удалось обновить auth.json через tools/auto_login_crm.py.")


async def collect_once(start: date, end: date) -> dict[str, Any]:
    if not AUTH_FILE.exists():
        raise AuthExpired("Файл auth.json отсутствует.")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            context = await browser.new_context(storage_state=str(AUTH_FILE))
            await install_readonly_guard(context)
            page = await context.new_page()
            await goto_readonly(page, BASE_URL)
            await validate_store_configuration(page)

            opening_date = start - timedelta(days=1)
            opening = await fetch_snapshot(page, opening_date, "начальный")
            ending = await fetch_snapshot(page, end, "конечный")
            documents = await collect_intake_documents(page, start, end)
            intake, intake_nomenclature = await fetch_intake_lines(context, documents)

            nmi_to_nomenclature: dict[int, int] = {}
            for source in (opening, ending):
                for nmi_id, value in source.items():
                    if value.nomenclature_id is None:
                        raise ReportError(f"Снимок CRM не содержит Nomenclature.id для NMI.id={nmi_id}.")
                    existing = nmi_to_nomenclature.get(nmi_id)
                    if existing not in (None, value.nomenclature_id):
                        raise ReportError(f"NMI.id={nmi_id} связан с разными Nomenclature.id.")
                    nmi_to_nomenclature[nmi_id] = value.nomenclature_id
            for nmi_id, nomenclature_id in intake_nomenclature.items():
                existing = nmi_to_nomenclature.get(nmi_id)
                if existing not in (None, nomenclature_id):
                    raise ReportError(f"NMI.id={nmi_id} связан с разными Nomenclature.id.")
                nmi_to_nomenclature[nmi_id] = nomenclature_id

            universe = set(opening) | set(intake.values) | set(ending)
            missing_cards = sorted(universe - set(nmi_to_nomenclature))
            if missing_cards:
                raise ReportError(f"Для NMI не найдены карточки номенклатуры: {missing_cards[:20]}")

            metadata = await fetch_product_metadata(
                context, {nmi_id: nmi_to_nomenclature[nmi_id] for nmi_id in universe}
            )
            await fill_categories(context, metadata)
            procurement = await fetch_procurement_control(page, start, end)
            return {
                "opening": opening,
                "ending": ending,
                "intake": intake,
                "metadata": metadata,
                "universe": universe,
                "documents": documents,
                "procurement": procurement,
            }
        finally:
            await browser.close()


async def collect_report(start: date, end: date) -> dict[str, Any]:
    for attempt in range(2):
        try:
            return await collect_once(start, end)
        except AuthExpired:
            if attempt:
                raise ReportError("CRM снова запросила вход после обновления auth.json.")
            run_auto_login()
    raise AssertionError("unreachable")


def category_matches(actual: str, requested: str) -> bool:
    wanted = clean_text(requested).casefold()
    full = clean_text(actual).casefold()
    segments = [clean_text(item).casefold() for item in actual.split("/")]
    return wanted == full or wanted in segments


def build_rows(
    collected: dict[str, Any], brand_filter: str | None, category_filter: str | None
) -> list[dict[str, Any]]:
    opening: dict[int, BalanceValue] = collected["opening"]
    ending: dict[int, BalanceValue] = collected["ending"]
    intake: IntakeAggregate = collected["intake"]
    metadata: dict[int, ProductMeta] = collected["metadata"]
    selected: list[int] = []
    for nmi_id in collected["universe"]:
        item = metadata[nmi_id]
        if brand_filter and item.brand.casefold() != clean_text(brand_filter).casefold():
            continue
        if category_filter and not category_matches(item.category, category_filter):
            continue
        selected.append(nmi_id)
    selected.sort(key=lambda nmi_id: (metadata[nmi_id].category.casefold(), nmi_id))
    rows = []
    for number, nmi_id in enumerate(selected, 1):
        opening_value = opening.get(nmi_id, BalanceValue())
        intake_value = intake.values.get(nmi_id, BalanceValue())
        ending_value = ending.get(nmi_id, BalanceValue())
        item = metadata[nmi_id]
        rows.append(
            {
                "number": number,
                "category": item.category,
                "nmi_id": nmi_id,
                "suppliers": "\n".join(item.suppliers),
                "opening_quantity": opening_value.quantity,
                "opening_amount": opening_value.amount,
                "intake_quantity": intake_value.quantity,
                "intake_amount": intake_value.amount,
                "ending_quantity": ending_value.quantity,
                "ending_amount": ending_value.amount,
                "brand": item.brand,
                "has_supplier_restrictions": item.has_supplier_restrictions,
            }
        )
    return rows


def filter_text(brand: str | None, category: str | None) -> str:
    parts = []
    if brand:
        parts.append(f"Бренд: {brand}")
    if category:
        parts.append(f"Категория: {category}")
    return "; ".join(parts) if parts else "Все товары"


def decimal_to_json(value: Decimal) -> int | float:
    integral = value.to_integral_value()
    if value == integral:
        return int(integral)
    return float(value)


def find_artifact_runtime() -> tuple[Path, Path]:
    node = Path(os.environ.get(NODE_EXE_ENV, str(DEFAULT_NODE_EXE)))
    node_modules = Path(os.environ.get(NODE_MODULES_ENV, str(DEFAULT_NODE_MODULES)))
    if not node.exists():
        raise ReportError(
            f"Не найден Node.js runtime для @oai/artifact-tool: {node}. "
            f"Можно задать {NODE_EXE_ENV}."
        )
    if not (node_modules / "@oai" / "artifact-tool").exists():
        raise ReportError(
            f"Не найден @oai/artifact-tool в {node_modules}. "
            f"Можно задать {NODE_MODULES_ENV}."
        )
    return node, node_modules


BUILDER_SOURCE = r'''
import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [dataPath] = process.argv.slice(2);
const data = JSON.parse(await fs.readFile(dataPath, "utf8"));
const workbook = Workbook.create();
const sheet = workbook.worksheets.add("Отчет движения товара");
sheet.showGridLines = false;

sheet.getRange("A1").values = [["Отчет движения товара"]];
sheet.getRange("A1").format = {fill: "#FFFFFF", font: {bold: true, color: "#000000", size: 18}};
sheet.getRange("A3:E3").values = [["Период", "с", data.fromDisplay, "по", data.toDisplay]];
sheet.getRange("A5:C5").values = [["Фильтр", "", data.filterText]];

sheet.getRange("A8:J9").values = [
  ["№ п.п.", "Категория ИТ", "Артикул в ИТ", "Артикул поставщика", "Остаток на начало", "", "Приход", "", "Остаток на конец", ""],
  ["", "", "", "", "кв-во", "сумма", "кв-во", "сумма", "кв-во", "сумма"],
];
for (const address of ["A8:A9", "B8:B9", "C8:C9", "D8:D9", "E8:F8", "G8:H8", "I8:J8"]) {
  sheet.mergeCells(address);
}

const matrix = data.rows.map(row => [
  row.number,
  row.category,
  row.nmi_id,
  row.suppliers,
  row.opening_quantity,
  row.opening_amount,
  row.intake_quantity,
  row.intake_amount,
  row.ending_quantity,
  row.ending_amount,
]);
const lastDataRow = 9 + matrix.length;
if (matrix.length) {
  sheet.getRange(`A10:J${lastDataRow}`).values = matrix;
}

const usedEnd = Math.max(lastDataRow, 9);
sheet.getRange(`A1:J${usedEnd}`).format.fill = "#FFFFFF";
sheet.getRange(`A1:J${usedEnd}`).format.font = {color: "#000000"};
sheet.getRange("A1").format.font = {bold: true, color: "#000000", size: 18};
sheet.getRange("A3:E3").format.verticalAlignment = "center";
sheet.getRange("A3").format.font = {bold: true, color: "#000000"};
sheet.getRange("A5").format.font = {bold: true, color: "#000000"};
sheet.getRange("A8:J9").format = {
  fill: "#FFFFFF",
  font: {bold: true, color: "#000000"},
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: {preset: "all", style: "thin", color: "#000000"},
};
sheet.getRange("A8:J9").format.rowHeight = 30;
if (matrix.length) {
  const dataRange = sheet.getRange(`A10:J${lastDataRow}`);
  dataRange.format = {
    fill: "#FFFFFF",
    font: {color: "#000000"},
    verticalAlignment: "top",
    borders: {preset: "all", style: "thin", color: "#000000"},
  };
  sheet.getRange(`A10:A${lastDataRow}`).format.horizontalAlignment = "center";
  sheet.getRange(`C10:C${lastDataRow}`).format.horizontalAlignment = "center";
  sheet.getRange(`B10:B${lastDataRow}`).format.wrapText = true;
  sheet.getRange(`D10:D${lastDataRow}`).format.wrapText = true;
  for (const column of ["E", "G", "I"]) sheet.getRange(`${column}10:${column}${lastDataRow}`).format.numberFormat = "General";
  for (const column of ["F", "H", "J"]) sheet.getRange(`${column}10:${column}${lastDataRow}`).format.numberFormat = "#,##0.00";
  sheet.getRange(`C10:C${lastDataRow}`).format.numberFormat = "0";
  data.rows.forEach((row, index) => {
    const supplierLines = Math.max(1, String(row.suppliers || "").split("\n").length);
    const categoryLines = Math.max(1, Math.ceil(String(row.category || "").length / 42));
    const lines = Math.max(supplierLines, categoryLines);
    sheet.getRange(`A${10 + index}:J${10 + index}`).format.rowHeight = Math.max(19, lines * 15);
  });
}

const widths = {A: 7, B: 38, C: 15, D: 48, E: 12, F: 16, G: 12, H: 16, I: 12, J: 16};
for (const [column, width] of Object.entries(widths)) sheet.getRange(`${column}:${column}`).format.columnWidth = width;

let noteRow = lastDataRow + 2;
for (const note of data.notes) {
  sheet.mergeCells(`A${noteRow}:J${noteRow}`);
  sheet.getRange(`A${noteRow}`).values = [[note]];
  sheet.getRange(`A${noteRow}:J${noteRow}`).format = {
    fill: "#FFFFFF",
    font: {color: "#000000", italic: true},
    wrapText: true,
    verticalAlignment: "top",
  };
  sheet.getRange(`A${noteRow}:J${noteRow}`).format.rowHeight = 30;
  noteRow += 1;
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(data.outputPath);
'''


def create_runtime_junction(junction: Path, target: Path) -> None:
    completed = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ReportError(f"Не удалось подключить @oai/artifact-tool: {clean_text(completed.stderr or completed.stdout)}")


def remove_runtime_junction(junction: Path) -> None:
    if not junction.exists():
        return
    completed = subprocess.run(
        ["cmd.exe", "/d", "/c", "rmdir", str(junction)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ReportError(f"Не удалось удалить временное подключение node_modules: {junction}")


def write_workbook(
    output_path: Path,
    start: date,
    end: date,
    rows: list[dict[str, Any]],
    applied_filter: str,
    notes: list[str],
) -> None:
    node, node_modules = find_artifact_runtime()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="inventory_movement_report_"))
    junction = temp_root / "node_modules"
    exported_workbook = temp_root / output_path.name
    try:
        create_runtime_junction(junction, node_modules)
        builder = temp_root / "build_report.mjs"
        data_path = temp_root / "report_data.json"
        builder.write_text(textwrap.dedent(BUILDER_SOURCE), encoding="utf-8")
        payload = {
            "from": start.isoformat(),
            "to": end.isoformat(),
            "fromDisplay": crm_date(start),
            "toDisplay": crm_date(end),
            "filterText": applied_filter,
            "rows": [
                {
                    "number": item["number"],
                    "category": item["category"],
                    "nmi_id": item["nmi_id"],
                    "suppliers": item["suppliers"],
                    "opening_quantity": decimal_to_json(item["opening_quantity"]),
                    "opening_amount": decimal_to_json(item["opening_amount"]),
                    "intake_quantity": decimal_to_json(item["intake_quantity"]),
                    "intake_amount": decimal_to_json(item["intake_amount"]),
                    "ending_quantity": decimal_to_json(item["ending_quantity"]),
                    "ending_amount": decimal_to_json(item["ending_amount"]),
                }
                for item in rows
            ],
            "notes": notes,
            "outputPath": str(exported_workbook),
        }
        data_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        completed = subprocess.run(
            [str(node), str(builder), str(data_path)],
            cwd=temp_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise ReportError(
                "@oai/artifact-tool не смог сформировать XLSX: "
                + clean_text(completed.stderr or completed.stdout)
            )
        try:
            exported_metadata = exported_workbook.stat()
        except FileNotFoundError as error:
            raise ReportError(
                "@oai/artifact-tool не создал итоговый XLSX."
            ) from error
        if not stat.S_ISREG(
            exported_metadata.st_mode
        ):
            raise ReportError("@oai/artifact-tool не создал итоговый XLSX.")
        exported_workbook.replace(output_path)
    finally:
        remove_runtime_junction(junction)
        shutil.rmtree(temp_root)


def column_index(cell_ref: str) -> int:
    letters = re.match(r"[A-Z]+", cell_ref)
    if letters is None:
        raise ReportError(f"Некорректная ссылка Excel: {cell_ref}")
    result = 0
    for letter in letters.group(0):
        result = result * 26 + ord(letter) - 64
    return result


def reopen_and_verify_xlsx(output_path: Path, start: date, end: date, expected_rows: int) -> dict[str, Any]:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rel_ns = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
    with zipfile.ZipFile(output_path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        sheets = workbook.find("m:sheets", ns)
        if sheets is None or len(sheets) != 1:
            raise ReportError("Проверка XLSX: ожидался ровно один лист.")
        sheet_info = sheets[0]
        if sheet_info.attrib.get("name") != "Отчет движения товара":
            raise ReportError("Проверка XLSX: неверное имя листа.")
        relationship_id = sheet_info.attrib.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        )
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = next(
            (
                item.attrib["Target"]
                for item in relationships.findall("r:Relationship", rel_ns)
                if item.attrib.get("Id") == relationship_id
            ),
            None,
        )
        if target is None:
            raise ReportError("Проверка XLSX: не найден XML листа.")
        normalized_target = target.lstrip("/")
        sheet_path = (
            normalized_target
            if normalized_target.startswith("xl/")
            else "xl/" + normalized_target
        )
        sheet_xml = ET.fromstring(archive.read(sheet_path))

        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_xml = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in shared_xml.findall("m:si", ns):
                shared.append("".join(node.text or "" for node in item.findall(".//m:t", ns)))

        cells: dict[str, tuple[str | None, str]] = {}
        for cell in sheet_xml.findall(".//m:c", ns):
            ref = cell.attrib.get("r")
            if not ref:
                continue
            cell_type = cell.attrib.get("t")
            if cell_type == "inlineStr":
                value = "".join(node.text or "" for node in cell.findall(".//m:t", ns))
            else:
                value_node = cell.find("m:v", ns)
                value = value_node.text if value_node is not None and value_node.text is not None else ""
                if cell_type == "s" and value:
                    value = shared[int(value)]
            cells[ref] = (cell_type, value)

        def text_value(ref: str) -> str:
            return cells.get(ref, (None, ""))[1]

        if text_value("A1") != "Отчет движения товара":
            raise ReportError("Проверка XLSX: A1 не содержит заголовок.")

        def verify_date(ref: str, expected: date) -> None:
            cell_type, value = cells.get(ref, (None, ""))
            if cell_type in {"s", "str", "inlineStr"}:
                if value != crm_date(expected):
                    raise ReportError(
                        f"Проверка XLSX: {ref}={value!r}, ожидалось {crm_date(expected)!r}."
                    )
                return
            try:
                actual = (datetime(1899, 12, 30) + timedelta(days=float(value))).date()
            except (TypeError, ValueError) as error:
                raise ReportError(f"Проверка XLSX: {ref} не содержит корректную дату.") from error
            if actual != expected:
                raise ReportError(f"Проверка XLSX: {ref}={actual}, ожидалось {expected}.")

        verify_date("C3", start)
        verify_date("E3", end)

        merged = {
            item.attrib["ref"] for item in sheet_xml.findall(".//m:mergeCells/m:mergeCell", ns)
        }
        required_merges = {"A8:A9", "B8:B9", "C8:C9", "D8:D9", "E8:F8", "G8:H8", "I8:J8"}
        if not required_merges.issubset(merged):
            raise ReportError(f"Проверка XLSX: отсутствуют merged ranges {sorted(required_merges - merged)}")

        expected_headers = {
            "A8": "№ п.п.",
            "B8": "Категория ИТ",
            "C8": "Артикул в ИТ",
            "D8": "Артикул поставщика",
            "E8": "Остаток на начало",
            "G8": "Приход",
            "I8": "Остаток на конец",
            "E9": "кв-во",
            "F9": "сумма",
            "G9": "кв-во",
            "H9": "сумма",
            "I9": "кв-во",
            "J9": "сумма",
        }
        for ref, expected in expected_headers.items():
            if text_value(ref) != expected:
                raise ReportError(f"Проверка XLSX: {ref}={text_value(ref)!r}, ожидалось {expected!r}.")

        data_rows = 0
        for row_number in range(10, 10 + expected_rows):
            if text_value(f"A{row_number}") == "":
                raise ReportError(f"Проверка XLSX: отсутствует строка данных {row_number}.")
            data_rows += 1
            for column in ("A", "C", "E", "F", "G", "H", "I", "J"):
                cell_type, value = cells.get(f"{column}{row_number}", (None, ""))
                if cell_type in {"s", "str", "inlineStr"} or value == "":
                    raise ReportError(
                        f"Проверка XLSX: {column}{row_number} должно быть числовым полем."
                    )
                try:
                    float(value)
                except ValueError as error:
                    raise ReportError(
                        f"Проверка XLSX: {column}{row_number} содержит не число {value!r}."
                    ) from error
        if data_rows != expected_rows:
            raise ReportError("Проверка XLSX: число строк данных не совпало с universe.")
        return {
            "sheet": sheet_info.attrib["name"],
            "merged": sorted(required_merges),
            "data_rows": data_rows,
            "numeric_fields": True,
        }


def calculate_controls(
    collected: dict[str, Any], rows: list[dict[str, Any]]
) -> ReportControls:
    opening: dict[int, BalanceValue] = collected["opening"]
    ending: dict[int, BalanceValue] = collected["ending"]
    intake: IntakeAggregate = collected["intake"]
    raw_union: set[int] = collected["universe"]
    intake_quantity = sum((value.quantity for value in intake.values.values()), ZERO)
    intake_amount = sum((value.amount for value in intake.values.values()), ZERO)
    opening_amount = sum((value.amount for value in opening.values()), ZERO)
    ending_amount = sum((value.amount for value in ending.values()), ZERO)
    procurement: ProcurementControl | None = collected["procurement"]
    procurement_item_row_count = None
    procurement_item_rows_amount = None
    procurement_server_total = None
    procurement_difference = None
    if procurement is not None:
        procurement_item_row_count = procurement.item_row_count
        procurement_item_rows_amount = procurement.item_rows_amount
        procurement_server_total = procurement.server_total
        procurement_difference = procurement.item_rows_amount - intake_amount

    return ReportControls(
        opening_item_count=len(opening),
        intake_item_count=len(intake.values),
        ending_item_count=len(ending),
        union_item_count=len(raw_union),
        row_count=len(rows),
        intake_document_count=intake.document_count,
        intake_line_count=intake.line_count,
        intake_quantity=intake_quantity,
        intake_amount=intake_amount,
        opening_amount=opening_amount,
        ending_amount=ending_amount,
        procurement_item_row_count=procurement_item_row_count,
        procurement_item_rows_amount=procurement_item_rows_amount,
        procurement_server_total=procurement_server_total,
        procurement_difference=procurement_difference,
    )


def print_controls(controls: ReportControls) -> None:
    print("\nКонтрольные показатели:")
    print(f"  Товаров в начальном снимке: {controls.opening_item_count}")
    print(f"  Товаров с приходом: {controls.intake_item_count}")
    print(f"  Товаров в конечном снимке: {controls.ending_item_count}")
    print(f"  Размер UNION до фильтра: {controls.union_item_count}")
    print(f"  Строк после итогового фильтра: {controls.row_count}")
    print(f"  Проведённых intake-документов: {controls.intake_document_count}")
    print(f"  Уникальных intake lines: {controls.intake_line_count}")
    print(f"  Суммарное количество прихода: {controls.intake_quantity}")
    print(f"  Суммарная сумма прихода: {controls.intake_amount:.2f}")
    print(f"  Сумма остатков на начало: {controls.opening_amount:.2f}")
    print(f"  Сумма остатков на конец: {controls.ending_amount:.2f}")
    if controls.procurement_item_rows_amount is not None:
        server_total = (
            f"{controls.procurement_server_total:.2f}"
            if controls.procurement_server_total is not None
            else "отсутствует"
        )
        print(f"  Intake amount: {controls.intake_amount:.2f}")
        print(
            f"  Procurement item rows amount ({controls.procurement_item_row_count}): "
            f"{controls.procurement_item_rows_amount:.2f}"
        )
        print(f"  Procurement server total: {server_total}")
        print(
            "  Difference intake vs procurement: "
            f"{controls.procurement_difference:.2f}"
        )


def print_first_rows(rows: list[dict[str, Any]]) -> None:
    print("\nПервые 10 строк итоговых данных:")
    for item in rows[:10]:
        supplier_text = item["suppliers"].replace("\n", " | ") or "—"
        print(
            f"  {item['number']}. {item['category']} | ИТ {item['nmi_id']} | {supplier_text} | "
            f"начало {item['opening_quantity']} / {item['opening_amount']:.2f} | "
            f"приход {item['intake_quantity']} / {item['intake_amount']:.2f} | "
            f"конец {item['ending_quantity']} / {item['ending_amount']:.2f}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Сформировать Excel «Отчет движения товара» из CRM.")
    parser.add_argument("--from", dest="start", required=True, type=parse_iso_date, metavar="YYYY-MM-DD")
    parser.add_argument("--to", dest="end", required=True, type=parse_iso_date, metavar="YYYY-MM-DD")
    parser.add_argument("--brand", help="Фактический бренд CRM (без учёта регистра).")
    parser.add_argument("--category", help="Фактическая категория или сегмент иерархии CRM.")
    parser.add_argument("--output", type=Path, help="Путь к итоговому .xlsx.")
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("--from не может быть позже --to")
    return args


def generate_inventory_movement_report(
    start: date,
    end: date,
    output_path: Path,
    brand: str | None = None,
    category: str | None = None,
) -> InventoryMovementReportResult:
    if start > end:
        raise ReportError("Дата начала отчёта не может быть позже даты окончания.")

    output = Path(output_path).resolve()
    if output.suffix.lower() != ".xlsx":
        raise ReportError("Параметр --output должен указывать файл с расширением .xlsx.")

    collected = asyncio.run(collect_report(start, end))
    rows = build_rows(collected, brand, category)
    if (brand or category) and not rows:
        raise ReportError("После применения фактических CRM-фильтров не осталось товаров.")

    notes = [
        "Для товаров с несколькими поставщиками в колонке «Артикул поставщика» перечислены все доступные пары «поставщик — артикул»."
    ]
    if any(item["has_supplier_restrictions"] for item in rows):
        notes.append(
            "Ограничения supplier SKU по cities[]/filials[] не применялись: их семантика в CRM неоднозначна, поэтому связи не отбрасывались молча."
        )
    if end == date.today():
        notes.append("Остаток на конец текущего дня указан на момент формирования отчёта.")

    controls = calculate_controls(collected, rows)
    print_controls(controls)
    print_first_rows(rows)
    write_workbook(output, start, end, rows, filter_text(brand, category), notes)
    if not output.is_file():
        raise ReportError(f"XLSX не был создан: {output}")
    if output.stat().st_size <= 0:
        raise ReportError(f"Создан пустой XLSX: {output}")
    verification = reopen_and_verify_xlsx(output, start, end, len(rows))
    print("\nПроверка созданного XLSX через Python:")
    print(f"  Лист: {verification['sheet']}")
    print("  A1, даты, merged ranges и A8:J9: корректны")
    print(f"  Строк данных: {verification['data_rows']}")
    print("  Количества, суммы и Артикул ИТ: числовые")
    print(f"\nГотовый файл: {output}")

    return InventoryMovementReportResult(
        output_path=output,
        start_date=start,
        end_date=end,
        brand=brand,
        category=category,
        row_count=controls.row_count,
        intake_document_count=controls.intake_document_count,
        intake_quantity=controls.intake_quantity,
        intake_amount=controls.intake_amount,
        procurement_item_rows_amount=controls.procurement_item_rows_amount,
        procurement_server_total=controls.procurement_server_total,
        verified=True,
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args()
    output = args.output or Path(
        f"Отчет движения товара {crm_date(args.start)}-{crm_date(args.end)}.xlsx"
    )
    generate_inventory_movement_report(
        start=args.start,
        end=args.end,
        output_path=output,
        brand=args.brand,
        category=args.category,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ReportError, PlaywrightError, OSError, subprocess.SubprocessError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        raise SystemExit(1)
