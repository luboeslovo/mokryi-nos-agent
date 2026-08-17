import asyncio
import csv
import os
import sys
from html.parser import HTMLParser

from playwright.async_api import async_playwright


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

AUTH_FILE = os.path.join(
    PROJECT_DIR,
    "auth.json"
)

CHECKS_FILE = os.path.join(
    PROJECT_DIR,
    "checks_raw.csv"
)

BASE_URL = "https://it.mokryinos.ru"
CHECKS_URL = BASE_URL + "/checkKkm/index"

PAGE_SIZE = 500


class ChecksParser(HTMLParser):

    def __init__(self):
        super().__init__()

        self.rows = []

        self.in_row = False
        self.current_row = None

        self.in_td = False
        self.current_td = ""

    def handle_starttag(self, tag, attrs):

        attrs = dict(attrs)

        if tag == "tr" and "data-key" in attrs:

            self.in_row = True

            self.current_row = {
                "check_id": attrs["data-key"],
                "cells": [],
            }

        elif self.in_row and tag == "td":

            self.in_td = True
            self.current_td = ""

    def handle_data(self, data):

        if self.in_row and self.in_td:
            self.current_td += data

    def handle_endtag(self, tag):

        if (
            self.in_row
            and tag == "td"
            and self.in_td
        ):

            text = " ".join(
                self.current_td.split()
            )

            self.current_row["cells"].append(
                text
            )

            self.in_td = False
            self.current_td = ""

        elif (
            self.in_row
            and tag == "tr"
        ):

            self.rows.append(
                self.current_row
            )

            self.in_row = False
            self.current_row = None


def load_existing_checks():

    if not os.path.exists(
        CHECKS_FILE
    ):

        print(
            "Не найден checks_raw.csv"
        )

        sys.exit(1)

    with open(
        CHECKS_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(
            file
        )

        fieldnames = (
            reader.fieldnames
        )

        rows = list(
            reader
        )

    if not fieldnames:

        print(
            "В checks_raw.csv "
            "нет заголовков."
        )

        sys.exit(1)

    existing_ids = {
        str(
            row["check_id"]
        ).strip()
        for row in rows
        if row.get(
            "check_id"
        )
    }

    return (
        fieldnames,
        rows,
        existing_ids,
    )


def check_auth_response(
    response
):

    actual_url = (
        response.url.lower()
    )

    if "/login" in actual_url:

        raise RuntimeError(
            "AUTH_EXPIRED"
        )


async def fetch_page(
    context,
    page_number
):

    url = (
        f"{CHECKS_URL}"
        f"?pageSize={PAGE_SIZE}"
        f"&CheckKkm_page={page_number}"
    )

    response = (
        await context.request.get(
            url,
            timeout=30000
        )
    )

    check_auth_response(
        response
    )

    if response.status != 200:

        raise RuntimeError(
            f"HTTP {response.status}"
        )

    html = await response.text()

    parser = ChecksParser()

    parser.feed(
        html
    )

    return parser.rows


def convert_row(row):

    cells = row["cells"]

    if len(cells) < 9:
        return None

    return {
        "check_id": str(
            row["check_id"]
        ).strip(),

        "date": cells[1],

        "number": cells[2],

        "customer": cells[3],

        "type": cells[4],

        "organization": cells[5],

        "branch": cells[6],

        "user": cells[7],

        "amount": cells[8],
    }


def save_checks(
    fieldnames,
    old_rows,
    new_rows
):

    combined = (
        new_rows
        + old_rows
    )

    with open(
        CHECKS_FILE,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for row in combined:

            output = {
                field: row.get(
                    field,
                    ""
                )
                for field
                in fieldnames
            }

            writer.writerow(
                output
            )


async def main():

    (
        fieldnames,
        old_rows,
        existing_ids,
    ) = load_existing_checks()

    print()
    print("=" * 70)

    print(
        f"Чеков локально: "
        f"{len(old_rows)}"
    )

    if old_rows:

        print(
            "Самый новый локальный чек:"
        )

        print(
            f"{old_rows[0].get('date', '')}"
            f" | "
            f"{old_rows[0].get('number', '')}"
        )

    print("=" * 70)

    if not os.path.exists(
        AUTH_FILE
    ):

        print()
        print("=" * 70)

        print(
            "Не найден auth.json."
        )

        print(
            "Обновление CRM невозможно."
        )

        print("=" * 70)

        sys.exit(2)

    async with async_playwright() as p:

        browser = (
            await p.chromium.launch(
                headless=True
            )
        )

        context = (
            await browser.new_context(
                storage_state=AUTH_FILE
            )
        )

        try:

            new_checks = []

            page_number = 1

            found_old_check = False

            print()

            print(
                "Проверяю новые чеки "
                "в CRM..."
            )

            while True:

                rows = (
                    await fetch_page(
                        context,
                        page_number
                    )
                )

                print(
                    f"Страница "
                    f"{page_number}: "
                    f"{len(rows)} чеков"
                )

                if not rows:
                    break

                for raw_row in rows:

                    check_id = str(
                        raw_row[
                            "check_id"
                        ]
                    ).strip()

                    if (
                        check_id
                        in existing_ids
                    ):

                        found_old_check = True
                        break

                    row = convert_row(
                        raw_row
                    )

                    if row is not None:

                        new_checks.append(
                            row
                        )

                if found_old_check:
                    break

                if (
                    len(rows)
                    < PAGE_SIZE
                ):
                    break

                page_number += 1

            print()
            print("=" * 70)

            if not new_checks:

                print(
                    "Новых чеков нет."
                )

                print(
                    f"Всего локально: "
                    f"{len(old_rows)}"
                )

            else:

                save_checks(
                    fieldnames,
                    old_rows,
                    new_checks
                )

                print(
                    f"Новых чеков: "
                    f"{len(new_checks)}"
                )

                print()

                print(
                    "Самый новый:"
                )

                print(
                    f"{new_checks[0]['date']}"
                    f" | "
                    f"{new_checks[0]['number']}"
                    f" | "
                    f"{new_checks[0]['customer']}"
                    f" | "
                    f"{new_checks[0]['amount']}"
                )

                print()

                print(
                    "Самый старый "
                    "из новых:"
                )

                print(
                    f"{new_checks[-1]['date']}"
                    f" | "
                    f"{new_checks[-1]['number']}"
                    f" | "
                    f"{new_checks[-1]['customer']}"
                    f" | "
                    f"{new_checks[-1]['amount']}"
                )

                print()

                print(
                    "Теперь в "
                    "checks_raw.csv: "
                    f"{len(old_rows) + len(new_checks)}"
                    " чеков"
                )

            print("=" * 70)

        except RuntimeError as error:

            if (
                str(error)
                == "AUTH_EXPIRED"
            ):

                print()
                print("=" * 70)

                print(
                    "Авторизация CRM истекла."
                )

                print(
                    "Файлы не изменены."
                )

                print(
                    "Обновление остановлено."
                )

                print("=" * 70)

                # ВАЖНО:
                # ненулевой код возврата.
                # update_all.py увидит ошибку
                # и не продолжит pipeline.
                sys.exit(2)

            raise

        finally:

            await context.close()

            await browser.close()


if __name__ == "__main__":

    asyncio.run(
        main()
    )