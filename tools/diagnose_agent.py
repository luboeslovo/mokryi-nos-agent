import json
import os
import sys
import traceback

from agent_core import answer_question
from agent_tools import (
    compact_result,
    get_tool_names,
    run_tool,
)
from memory_tools import (
    clear_conversation,
)


PROJECT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

REPORT_PATH = os.path.join(
    PROJECT_DIR,
    "diagnostic_report.txt",
)


class TeeStream:
    def __init__(
        self,
        console,
        file_handle,
    ):
        self.console = console
        self.file_handle = file_handle

    @property
    def encoding(self):
        return getattr(
            self.console,
            "encoding",
            None,
        )

    def write(self, text):
        text = str(
            text
        )

        self.file_handle.write(
            text
        )

        self.file_handle.flush()

        try:
            self.console.write(
                text
            )

        except UnicodeEncodeError:
            encoding = (
                getattr(
                    self.console,
                    "encoding",
                    None,
                )
                or "cp1251"
            )

            safe_text = (
                text
                .encode(
                    encoding,
                    errors="replace",
                )
                .decode(
                    encoding,
                    errors="replace",
                )
            )

            self.console.write(
                safe_text
            )

    def flush(self):
        self.file_handle.flush()

        try:
            self.console.flush()
        except Exception:
            pass


def separator(title):
    print()
    print(
        "=" * 90
    )
    print(
        title
    )
    print(
        "=" * 90
    )
    print()


def print_json(value):
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


def safe_tool(
    name,
    arguments,
    conversation_id="__diagnostic_tools__",
):
    try:
        result = run_tool(
            name,
            arguments,
            conversation_id=conversation_id,
        )

        return {
            "ok":
                True,

            "result":
                result,
        }

    except Exception as error:
        return {
            "ok":
                False,

            "error_type":
                type(error).__name__,

            "error":
                str(error),

            "traceback":
                traceback.format_exc(),
        }


def print_tool_result(
    name,
    arguments,
):
    print(
        f"TOOL: {name}"
    )

    print(
        f"ARGS: {arguments}"
    )

    result = safe_tool(
        name,
        arguments,
    )

    if result["ok"]:
        print_json(
            result["result"]
        )

    else:
        print(
            "ОШИБКА:"
        )

        print_json(
            result
        )

    print()

    return result


def diagnose_registered_tools():
    separator(
        "1. ЗАРЕГИСТРИРОВАННЫЕ ИНСТРУМЕНТЫ"
    )

    names = get_tool_names()

    for index, name in enumerate(
        names,
        start=1,
    ):
        print(
            f"{index}. {name}"
        )

    print()
    print(
        f"Всего инструментов: {len(names)}"
    )


def diagnose_sales_coverage():
    separator(
        "2. КАКИЕ МЕСЯЦЫ ПРОДАЖ РЕАЛЬНО ДОСТУПНЫ"
    )

    years = [
        2025,
        2026,
    ]

    summary = []

    for year in years:
        print(
            f"ГОД {year}"
        )
        print(
            "-" * 40
        )

        max_month = (
            8
            if year == 2026
            else 12
        )

        for month in range(
            1,
            max_month + 1,
        ):
            result = safe_tool(
                "get_month_summary",
                {
                    "year":
                        year,

                    "month":
                        month,
                },
            )

            if not result["ok"]:
                status = (
                    "EXCEPTION"
                )

                print(
                    f"{month:02d}.{year}: "
                    f"{status} - "
                    f"{result['error']}"
                )

                summary.append(
                    {
                        "year":
                            year,

                        "month":
                            month,

                        "status":
                            status,
                    }
                )

                continue

            value = result[
                "result"
            ]

            status = value.get(
                "status"
            )

            if status == "ok":
                print(
                    f"{month:02d}.{year}: OK | "
                    f"{value.get('start_date')} - "
                    f"{value.get('end_date')} | "
                    f"дней: "
                    f"{value.get('days_with_data')} | "
                    f"выручка: "
                    f"{value.get('total_revenue')}"
                )

            else:
                print(
                    f"{month:02d}.{year}: "
                    f"{status}"
                )

            summary.append(
                {
                    "year":
                        year,

                    "month":
                        month,

                    "status":
                        status,

                    "start_date":
                        value.get(
                            "start_date"
                        ),

                    "end_date":
                        value.get(
                            "end_date"
                        ),

                    "days_with_data":
                        value.get(
                            "days_with_data"
                        ),

                    "total_revenue":
                        value.get(
                            "total_revenue"
                        ),
                }
            )

        print()

    print(
        "СВОДКА ПО ДОСТУПНОСТИ:"
    )

    print_json(
        summary
    )


def diagnose_month_comparisons():
    separator(
        "3. СРАВНЕНИЯ МЕСЯЦЕВ НАПРЯМУЮ ЧЕРЕЗ PYTHON"
    )

    comparisons = [
        {
            "label":
                "апрель 2025 против мая 2025",

            "year_a":
                2025,

            "month_a":
                4,

            "year_b":
                2025,

            "month_b":
                5,
        },
        {
            "label":
                "апрель 2026 против мая 2026",

            "year_a":
                2026,

            "month_a":
                4,

            "year_b":
                2026,

            "month_b":
                5,
        },
        {
            "label":
                "май 2026 против июня 2026",

            "year_a":
                2026,

            "month_a":
                5,

            "year_b":
                2026,

            "month_b":
                6,
        },
        {
            "label":
                "июнь 2026 против июля 2026",

            "year_a":
                2026,

            "month_a":
                6,

            "year_b":
                2026,

            "month_b":
                7,
        },
        {
            "label":
                "июль 2026 против августа 2026",

            "year_a":
                2026,

            "month_a":
                7,

            "year_b":
                2026,

            "month_b":
                8,
        },
    ]

    for item in comparisons:
        print(
            f"СРАВНЕНИЕ: "
            f"{item['label']}"
        )

        result = safe_tool(
            "compare_sales_months",
            {
                "year_a":
                    item["year_a"],

                "month_a":
                    item["month_a"],

                "year_b":
                    item["year_b"],

                "month_b":
                    item["month_b"],
            },
        )

        if result["ok"]:
            print_json(
                result["result"]
            )

        else:
            print_json(
                result
            )

        print(
            "-" * 90
        )


def diagnose_days():
    separator(
        "4. ДНИ И ПОСЛЕДНИЕ ПРОДАЖИ"
    )

    print_tool_result(
        "get_latest_sales_day",
        {},
    )

    tests = [
        (
            "05.07.2026",
            "05.08.2026",
        ),
        (
            "16.08.2026",
            "17.08.2026",
        ),
    ]

    for date_a, date_b in tests:
        print(
            f"Сравнение дней: "
            f"{date_a} vs {date_b}"
        )

        print_tool_result(
            "compare_sales_days",
            {
                "date_a":
                    date_a,

                "date_b":
                    date_b,
            },
        )


def diagnose_rfm():
    separator(
        "5. RFM"
    )

    print_tool_result(
        "get_rfm_summary",
        {},
    )

    segments = [
        "Ценный под риском",
        "Нужно удержать",
        "Под риском",
        "Остывает",
        "Потерянный ценный",
    ]

    for segment in segments:
        print(
            f"СЕГМЕНТ: {segment}"
        )

        result = safe_tool(
            "get_rfm_segment",
            {
                "segment":
                    segment,

                "limit":
                    5,

                "sort_by":
                    "monetary",
            },
        )

        if result["ok"]:
            print_json(
                result["result"]
            )

        else:
            print_json(
                result
            )

        print(
            "-" * 90
        )


def diagnose_top_customers():
    separator(
        "6. ТОП-5 КЛИЕНТОВ И CALL SCORE"
    )

    result = safe_tool(
        "get_top_customers",
        {
            "limit":
                5,
        },
    )

    if not result["ok"]:
        print_json(
            result
        )
        return

    compact = compact_result(
        "get_top_customers",
        result["result"],
    )

    print(
        "ТОП-5:"
    )

    print_json(
        compact
    )

    print()

    for customer in compact.get(
        "customers",
        [],
    ):
        customer_id = customer.get(
            "customer_id"
        )

        name = " ".join(
            part
            for part in [
                str(
                    customer.get(
                        "name",
                        "",
                    )
                    or ""
                ),
                str(
                    customer.get(
                        "lastname",
                        "",
                    )
                    or ""
                ),
            ]
            if part
        ).strip()

        print(
            f"CALL SCORE: "
            f"{name} / ID {customer_id}"
        )

        assessment = safe_tool(
            "get_customer_call_assessment",
            {
                "customer_id":
                    customer_id,
            },
        )

        if assessment["ok"]:
            print_json(
                assessment["result"]
            )

        else:
            print_json(
                assessment
            )

        print(
            "-" * 90
        )


def diagnose_control_customers():
    separator(
        "7. КОНТРОЛЬНЫЕ КЛИЕНТЫ"
    )

    customers = [
        (
            "Наталья Перечицкая",
            "1000446",
        ),
        (
            "Павел Васильев",
            "844016",
        ),
        (
            "Анастасия Евдокимова",
            "870583",
        ),
    ]

    for name, customer_id in customers:
        print(
            f"{name} / {customer_id}"
        )

        result = safe_tool(
            "get_customer_call_assessment",
            {
                "customer_id":
                    customer_id,
            },
        )

        if result["ok"]:
            print_json(
                result["result"]
            )

        else:
            print_json(
                result
            )

        print(
            "-" * 90
        )


def diagnose_call_candidates():
    separator(
        "8. КАНДИДАТЫ НА ОБЗВОН"
    )

    for mode in [
        "retain",
        "reactivate",
    ]:
        print(
            f"MODE: {mode}"
        )

        result = safe_tool(
            "get_contact_candidates",
            {
                "limit":
                    10,

                "mode":
                    mode,
            },
        )

        if result["ok"]:
            print_json(
                result["result"]
            )

        else:
            print_json(
                result
            )

        print(
            "-" * 90
        )


def run_agent_sequence(
    title,
    questions,
    conversation_id,
):
    separator(
        title
    )

    clear_conversation(
        conversation_id
    )

    try:
        for question in questions:
            print(
                "ПОЛЬЗОВАТЕЛЬ:"
            )

            print(
                question
            )

            print()
            print(
                "АГЕНТ:"
            )

            try:
                answer = answer_question(
                    question,
                    conversation_id=conversation_id,
                )

                print(
                    answer
                )

            except Exception as error:
                print(
                    "ОШИБКА АГЕНТА:"
                )

                print(
                    f"{type(error).__name__}: "
                    f"{error}"
                )

                print(
                    traceback.format_exc()
                )

            print()
            print(
                "-" * 90
            )
            print()

    finally:
        clear_conversation(
            conversation_id
        )


def diagnose_agent_months():
    run_agent_sequence(
        title=(
            "9. АГЕНТ: ВОПРОСЫ ПРО МЕСЯЦЫ"
        ),
        questions=[
            "сравни апрель с маем",
            "сравни апрель 2025 с маем 2025",
            "сравни июнь с июлем",
            "сравни июль с августом",
        ],
        conversation_id=(
            "__diagnostic_agent_months__"
        ),
    )


def diagnose_agent_sales():
    run_agent_sequence(
        title=(
            "10. АГЕНТ: ПРОДАЖИ И FOLLOW-UP"
        ),
        questions=[
            "как прошел последний закрытый день?",
            "сравни 5 июля и 5 августа",
            "а какой из этих дней был лучше по выручке?",
        ],
        conversation_id=(
            "__diagnostic_agent_sales__"
        ),
    )


def diagnose_agent_customer_list():
    run_agent_sequence(
        title=(
            "11. АГЕНТ: СПИСОК КЛИЕНТОВ И «НИХ»"
        ),
        questions=[
            (
                "дай список из 5 человек "
                "кто принес больше всего денег"
            ),
            (
                "а стоит кому-то из них звонить?"
            ),
        ],
        conversation_id=(
            "__diagnostic_agent_customer_list__"
        ),
    )


def diagnose_agent_specific_customer():
    run_agent_sequence(
        title=(
            "12. АГЕНТ: КОНКРЕТНЫЙ КЛИЕНТ И «ЕЙ»"
        ),
        questions=[
            "расскажи про наталью перечицкую",
            "стоит ли ей звонить?",
        ],
        conversation_id=(
            "__diagnostic_agent_customer__"
        ),
    )


def diagnose_agent_calls():
    run_agent_sequence(
        title=(
            "13. АГЕНТ: ОЧЕРЕДЬ ЗВОНКОВ"
        ),
        questions=[
            "кому мне сейчас лучше позвонить?",
            "а кому дальше?",
            "а почему именно ей?",
        ],
        conversation_id=(
            "__diagnostic_agent_calls__"
        ),
    )


def run_diagnostics():
    separator(
        "МОКРЫЙ НОС AI - ПОЛНАЯ ДИАГНОСТИКА"
    )

    print(
        "Диагностика не изменяет рабочие данные магазина."
    )

    print(
        "Для тестов памяти используются отдельные "
        "диагностические conversation_id."
    )

    diagnose_registered_tools()
    diagnose_sales_coverage()
    diagnose_month_comparisons()
    diagnose_days()
    diagnose_rfm()
    diagnose_top_customers()
    diagnose_control_customers()
    diagnose_call_candidates()
    diagnose_agent_months()
    diagnose_agent_sales()
    diagnose_agent_customer_list()
    diagnose_agent_specific_customer()
    diagnose_agent_calls()

    separator(
        "ДИАГНОСТИКА ЗАВЕРШЕНА"
    )

    print(
        f"Полный отчёт сохранён в:"
    )

    print(
        REPORT_PATH
    )


def main():
    original_stdout = sys.stdout

    with open(
        REPORT_PATH,
        "w",
        encoding="utf-8",
    ) as report_file:
        sys.stdout = TeeStream(
            original_stdout,
            report_file,
        )

        try:
            run_diagnostics()

        except Exception:
            print()
            print(
                "КРИТИЧЕСКАЯ ОШИБКА ДИАГНОСТИКИ"
            )
            print(
                traceback.format_exc()
            )

        finally:
            sys.stdout.flush()
            sys.stdout = original_stdout

    print()
    print(
        "Готово."
    )
    print(
        f"Отчёт: {REPORT_PATH}"
    )


if __name__ == "__main__":
    main()