from datetime import datetime

from customer_tools import (
    get_customer_profile,
)


def first_value(
    data,
    *keys,
):
    if not isinstance(
        data,
        dict,
    ):
        return None

    for key in keys:
        value = data.get(
            key
        )

        if value not in (
            None,
            "",
        ):
            return value

    return None


def to_float(
    value,
):
    if value in (
        None,
        "",
    ):
        return None

    try:
        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return None


def format_money(
    value,
):
    number = to_float(
        value
    )

    if number is None:
        return "нет данных"

    rounded = round(
        number,
        2,
    )

    if abs(
        rounded
        - round(
            rounded
        )
    ) < 0.005:
        text = (
            f"{int(round(rounded)):,}"
        )

    else:
        text = (
            f"{rounded:,.2f}"
        )

    return (
        text
        .replace(
            ",",
            " ",
        )
        .replace(
            ".",
            ",",
        )
        + " ₽"
    )


def format_number(
    value,
    digits=2,
):
    number = to_float(
        value
    )

    if number is None:
        return "нет данных"

    if abs(
        number
        - round(
            number
        )
    ) < 1e-9:
        return str(
            int(
                round(
                    number
                )
            )
        )

    text = (
        f"{number:.{digits}f}"
        .rstrip(
            "0"
        )
        .rstrip(
            "."
        )
    )

    return text.replace(
        ".",
        ",",
    )


def format_date(
    value,
):
    if not value:
        return "нет данных"

    text = str(
        value
    ).strip()

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            parsed = datetime.strptime(
                text,
                fmt,
            )

            if (
                parsed.hour
                or parsed.minute
                or parsed.second
            ):
                return parsed.strftime(
                    "%d.%m.%Y %H:%M"
                )

            return parsed.strftime(
                "%d.%m.%Y"
            )

        except ValueError:
            pass

    return text


def format_phone(
    value,
):
    if not value:
        return "нет данных"

    digits = "".join(
        char
        for char in str(
            value
        )
        if char.isdigit()
    )

    if (
        len(
            digits
        )
        == 11
        and digits[0]
        in {
            "7",
            "8",
        }
    ):
        return (
            "+7 "
            f"({digits[1:4]}) "
            f"{digits[4:7]}-"
            f"{digits[7:9]}-"
            f"{digits[9:11]}"
        )

    return str(
        value
    )


def get_customer_name(
    customer,
):
    if not isinstance(
        customer,
        dict,
    ):
        return "Клиент"

    name = first_value(
        customer,
        "name",
        "first_name",
    )

    lastname = first_value(
        customer,
        "lastname",
        "last_name",
    )

    parts = [
        str(
            value
        ).strip()
        for value in (
            lastname,
            name,
        )
        if value
    ]

    if parts:
        return " ".join(
            parts
        )

    check_name = first_value(
        customer,
        "check_name",
        "full_name",
    )

    if check_name:
        return str(
            check_name
        ).strip()

    customer_id = first_value(
        customer,
        "customer_id",
        "id",
    )

    if customer_id:
        return (
            f"Клиент {customer_id}"
        )

    return "Клиент"


def render_product(
    product,
    position,
):
    if not isinstance(
        product,
        dict,
    ):
        return (
            f"{position}. "
            "Нет данных о товаре"
        )

    name = first_value(
        product,
        "product_name",
        "name",
    )

    if not name:
        name = "Товар без названия"

    quantity = first_value(
        product,
        "quantity",
    )

    purchase_lines = first_value(
        product,
        "purchase_lines",
        "purchases",
    )

    total_rubles = first_value(
        product,
        "total_rubles",
        "amount",
        "sum",
    )

    details = []

    if quantity not in (
        None,
        "",
    ):
        details.append(
            "количество: "
            + format_number(
                quantity
            )
        )

    if purchase_lines not in (
        None,
        "",
    ):
        details.append(
            "покупок/строк: "
            + format_number(
                purchase_lines
            )
        )

    if total_rubles not in (
        None,
        "",
    ):
        details.append(
            "на сумму "
            + format_money(
                total_rubles
            )
        )

    if details:
        return (
            f"{position}. {name} — "
            + ", ".join(
                details
            )
        )

    return (
        f"{position}. {name}"
    )


def render_customer_profile(
    result,
):
    if not isinstance(
        result,
        dict,
    ):
        return (
            "Не получилось получить "
            "профиль клиента."
        )

    if result.get(
        "error"
    ):
        return (
            "Не получилось получить "
            "профиль клиента."
        )

    customer = result.get(
        "customer",
        {},
    )

    statistics = result.get(
        "statistics",
        {},
    )

    top_products = result.get(
        "top_products",
        [],
    )

    if not customer:
        return (
            "Клиент не найден "
            "или профиль пуст."
        )

    name = get_customer_name(
        customer
    )

    customer_id = first_value(
        customer,
        "customer_id",
        "id",
    )

    phone = first_value(
        customer,
        "phone",
    )

    purchases = first_value(
        statistics,
        "purchases",
        "frequency",
        "check_count",
    )

    total_rubles = first_value(
        statistics,
        "total_rubles",
        "monetary",
        "purchase_sum",
    )

    average_check = first_value(
        statistics,
        "average_check_rubles",
        "average_check",
    )

    first_purchase = first_value(
        statistics,
        "first_purchase",
    )

    last_purchase = first_value(
        statistics,
        "last_purchase",
    )

    lines = [
        name,
    ]

    if customer_id:
        lines.append(
            f"ID: {customer_id}"
        )

    if phone:
        lines.append(
            "Телефон: "
            + format_phone(
                phone
            )
        )

    lines.extend(
        [
            "",
            "СТАТИСТИКА",
        ]
    )

    if purchases not in (
        None,
        "",
    ):
        lines.append(
            "• Покупок: "
            + format_number(
                purchases
            )
        )

    if total_rubles not in (
        None,
        "",
    ):
        lines.append(
            "• Общая сумма: "
            + format_money(
                total_rubles
            )
        )

    if average_check not in (
        None,
        "",
    ):
        lines.append(
            "• Средний чек: "
            + format_money(
                average_check
            )
        )

    if first_purchase:
        lines.append(
            "• Первая покупка: "
            + format_date(
                first_purchase
            )
        )

    if last_purchase:
        lines.append(
            "• Последняя покупка: "
            + format_date(
                last_purchase
            )
        )

    if top_products:
        lines.extend(
            [
                "",
                "ТОП ТОВАРОВ ИЗ ИСТОРИИ",
            ]
        )

        for index, product in enumerate(
            top_products[:5],
            start=1,
        ):
            lines.append(
                render_product(
                    product,
                    index,
                )
            )

    lines.extend(
        [
            "",
            (
                "Важно: это только факты из истории "
                "покупок. По ним нельзя достоверно "
                "определить количество, возраст или "
                "состояние питомцев, причину изменения "
                "покупок или текущую потребность клиента."
            ),
        ]
    )

    return "\n".join(
        lines
    )


def render_customer_search_result(
    result,
):
    if not isinstance(
        result,
        dict,
    ):
        return (
            "Не получилось выполнить "
            "поиск клиента."
        )

    status = result.get(
        "status"
    )

    if status == "unique_match":
        profile = result.get(
            "profile",
            {},
        )

        return render_customer_profile(
            profile
        )

    candidates = result.get(
        "candidates",
        result.get(
            "customers",
            [],
        ),
    )

    if candidates:
        lines = [
            (
                "Нашлось несколько клиентов. "
                "Нужно выбрать конкретного:"
            ),
            "",
        ]

        for index, customer in enumerate(
            candidates,
            start=1,
        ):
            name = get_customer_name(
                customer
            )

            customer_id = first_value(
                customer,
                "customer_id",
                "id",
            )

            phone = first_value(
                customer,
                "phone",
            )

            parts = [
                f"{index}. {name}",
            ]

            if customer_id:
                parts.append(
                    f"ID {customer_id}"
                )

            if phone:
                parts.append(
                    format_phone(
                        phone
                    )
                )

            lines.append(
                " — ".join(
                    parts
                )
            )

        lines.extend(
            [
                "",
                (
                    "По одной только фамилии или имени "
                    "не буду угадывать, какой именно "
                    "клиент имеется в виду."
                ),
            ]
        )

        return "\n".join(
            lines
        )

    return (
        "По этому запросу клиент "
        "не найден."
    )


def demo():
    print()
    print("=" * 70)
    print(
        "CUSTOMER RENDERER — TEST"
    )
    print("=" * 70)
    print()

    result = get_customer_profile(
        "844016"
    )

    print(
        render_customer_profile(
            result
        )
    )


if __name__ == "__main__":
    demo()