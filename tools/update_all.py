import os
import subprocess
import sys
from datetime import datetime


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

TOOLS_DIR = os.path.join(
    PROJECT_DIR,
    "tools"
)


STEPS = [
    (
        "Получаю новые чеки из CRM",
        "sync_checks.py"
    ),
    (
        "Получаю товары новых чеков",
        "fetch_check_items.py"
    ),
    (
        "Экспортирую товары чеков из SQLite в CSV",
        "export_check_items.py"
    ),

    # ========================================================
    # ДНЕВНЫЕ ПРОДАЖИ
    # ========================================================

    (
        "Получаю дневные продажи ККМ",
        "sync_kkm_daily.py"
    ),
    (
        "Получаю дневные возвраты",
        "sync_returns_daily.py"
    ),
    (
        "Получаю Яндекс, Купер и внешние заказы",
        "sync_sales_sources_daily.py"
    ),
    (
        "Собираю единую дневную таблицу продаж",
        "build_daily_sales.py"
    ),
    (
        "Собираю историческую дневную таблицу чеков",
        "build_historical_daily_checks.py"
    ),

    (
        "Обновляю ПО ЧИСЛАМ и ПО ДНЯМ НЕДЕЛИ",
        "export_daily_sales_to_sheets.py"
    ),

    # ========================================================
    # КЛИЕНТСКАЯ АНАЛИТИКА
    # ========================================================

    (
        "Определяю customer_id новых клиентов",
        "resolve_new_customers.py"
    ),
    (
        "Получаю новые карточки клиентов",
        "sync_customer_cards.py"
    ),
    (
        "Пересобираю analytics.sqlite",
        "build_analytics.py"
    ),
    (
        "Пересчитываю RFM",
        "build_rfm.py"
    ),
    (
        "Строю товарные профили клиентов",
        "build_customer_products.py"
    ),
    (
        "Обновляю RFM в Google Sheets",
        "export_rfm_to_sheets.py"
    ),
    (
        "Обновляю покупки клиентов в Google Sheets",
        "export_customer_products_to_sheets.py"
    ),
    (
        "Добавляю товарный профиль в RFM",
        "enrich_rfm_products.py"
    ),

    # ========================================================
    # ОПИУ
    # ========================================================

    (
        "Обновляю PL из CRM",
        "sync_pl.py"
    ),
    (
        "Обновляю CRM PL в Google Sheets",
        "export_pl_to_sheets.py"
    ),
    (
        "Получаю продажи Яндекс Еда и Купер",
        "sync_delivery_sales.py"
    ),
    (
        "Обновляю комиссии доставок в ОПиУ",
        "export_delivery_to_opiu.py"
    ),
    (
        "Получаю списания из CRM",
        "sync_writeoffs.py"
    ),
    (
        "Обновляю списания в ОПиУ",
        "export_writeoffs_to_opiu.py"
    ),
]


def run_script(filename):

    script_path = os.path.join(
        TOOLS_DIR,
        filename
    )

    if not os.path.exists(
        script_path
    ):

        raise FileNotFoundError(
            f"Не найден файл: "
            f"{script_path}"
        )

    subprocess.run(
        [
            sys.executable,
            script_path
        ],
        cwd=PROJECT_DIR,
        check=True
    )


def refresh_crm_auth():

    print()
    print("=" * 70)
    print(
        "ОБНОВЛЯЮ АВТОРИЗАЦИЮ CRM"
    )
    print("=" * 70)
    print()

    run_script(
        "auto_login_crm.py"
    )


def run_step(
    number,
    total,
    title,
    filename
):

    print()
    print("=" * 70)

    print(
        f"[{number}/{total}] "
        f"{title}"
    )

    print(
        f"Файл: tools\\{filename}"
    )

    print("=" * 70)
    print()

    run_script(
        filename
    )


def main():

    started_at = datetime.now()

    print()
    print("=" * 70)

    print(
        "ОБНОВЛЕНИЕ АНАЛИТИКИ "
        "«МОКРЫЙ НОС»"
    )

    print("=" * 70)

    print()

    print(
        "Старт:",
        started_at.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    try:

        refresh_crm_auth()

        total = len(
            STEPS
        )

        for index, (
            title,
            filename
        ) in enumerate(
            STEPS,
            start=1
        ):

            run_step(
                index,
                total,
                title,
                filename
            )

    except subprocess.CalledProcessError as error:

        print()
        print("=" * 70)

        print(
            "ОБНОВЛЕНИЕ ОСТАНОВЛЕНО"
        )

        print("=" * 70)

        print()

        print(
            "Ошибка на одном "
            "из этапов."
        )

        print(
            "Код возврата:",
            error.returncode
        )

        print()

        print(
            "Следующие этапы специально "
            "не запускались."
        )

        sys.exit(
            error.returncode
        )

    except Exception as error:

        print()
        print("=" * 70)

        print(
            "ОБНОВЛЕНИЕ ОСТАНОВЛЕНО"
        )

        print("=" * 70)

        print()

        print(
            type(error).__name__ + ":",
            error
        )

        sys.exit(
            1
        )

    finished_at = datetime.now()

    duration = (
        finished_at
        - started_at
    )

    print()
    print("=" * 70)

    print(
        "ВСЁ ОБНОВЛЕНО"
    )

    print("=" * 70)

    print()

    print(
        "Завершено:",
        finished_at.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print(
        "Время:",
        str(
            duration
        ).split(
            "."
        )[0]
    )

    print()
    print(
        "Актуальны:"
    )

    print()
    print(
        "--- ЛОКАЛЬНЫЕ ДАННЫЕ ---"
    )

    print(
        "checks_raw.csv"
    )

    print(
        "check_items.sqlite"
    )

    print(
        "check_items.csv"
    )

    print(
        "analytics.sqlite"
    )

    print(
        "customer_metrics.csv"
    )

    print(
        "customer_rfm.csv"
    )

    print(
        "customer_products.csv"
    )

    print()
    print(
        "--- ДНЕВНЫЕ ПРОДАЖИ ---"
    )

    print(
        "kkm_daily.csv"
    )

    print(
        "returns_daily.csv"
    )

    print(
        "sales_sources_daily.csv"
    )

    print(
        "sales_manual.csv"
    )

    print(
        "daily_sales.csv"
    )

    print()
    print(
        "--- ОПИУ ---"
    )

    print(
        "pl_monthly.csv"
    )

    print(
        "delivery_sales_monthly.csv"
    )

    print(
        "writeoffs_monthly.csv"
    )

    print()
    print(
        "--- GOOGLE SHEETS ---"
    )

    print(
        "RFM"
    )

    print(
        "Покупки клиентов"
    )

    print(
        "товарные колонки RFM"
    )

    print(
        "CRM PL"
    )

    print(
        "ОПиУ"
    )

    print(
        "ПО ЧИСЛАМ"
    )

    print(
        "ПО ДНЯМ НЕДЕЛИ"
    )

    print()
    print("=" * 70)


if __name__ == "__main__":

    main()