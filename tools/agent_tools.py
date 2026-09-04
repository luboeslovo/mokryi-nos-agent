from gigachat.models import (
    ChatFunctionSpecification,
    ChatTool,
)

from customer_tools import (
    find_customer_by_name,
    get_customer_profile,
    get_top_customers,
)

from sales_tools import (
    compare_sales_days,
    compare_sales_months,
    get_daily_sales,
    get_latest_sales_day,
    get_month_summary,
    get_recent_sales,
)

from live_sales_tools import (
    compare_current_sales_with_yesterday,
    get_current_sales,
)

from sales_analytics import (
    compare_sales_periods,
    compare_sales_years,
    get_available_sales_coverage,
    get_period_summary,
    get_year_summary,
    rank_sales_periods,
)

from finance_tools import (
    compare_finance_periods,
    get_finance_metric,
    get_finance_period,
    rank_finance_months,
)

from rfm_tools import (
    get_contact_candidates,
    get_rfm_segment,
    get_rfm_summary,
)

from call_tools import (
    get_customer_call_assessment,
    get_next_call_candidate,
)

from memory_tools import (
    get_today_suggested_customer_ids,
)


TEXT_FUNCTION_SPECS = [
    # ========================================================
    # КЛИЕНТЫ
    # ========================================================

    ChatFunctionSpecification(
        name="get_customer_profile",
        description=(
            "Получает фактический профиль конкретного клиента "
            "по customer_id."
        ),
        parameters={
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": (
                        "ID клиента в CRM"
                    ),
                },
            },
            "required": [
                "customer_id",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="get_top_customers",
        description=(
            "Возвращает самых ценных клиентов магазина "
            "по общей сумме покупок."
        ),
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": (
                        "Сколько клиентов вернуть"
                    ),
                },
            },
            "required": [
                "limit",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="find_customer_by_name",
        description=(
            "Ищет клиента по имени, фамилии "
            "или полному имени. "
            "Используй, когда пользователь называет "
            "конкретного человека."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Имя, фамилия или полное имя клиента"
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        "Максимальное количество совпадений"
                    ),
                },
            },
            "required": [
                "query",
            ],
        },
    ),

    # ========================================================
    # LIVE-ПРОДАЖИ
    # ========================================================

    ChatFunctionSpecification(
        name="get_current_sales",
        description=(
            "Возвращает текущие продажи за сегодняшний "
            "незакрытый день. "
            "Используй для вопросов 'сегодня', 'сейчас', "
            "'на текущий момент', 'сколько чеков сегодня', "
            "'какая выручка сейчас'. "
            "Дата определяется Python по часовому поясу магазина. "
            "Не подменяй сегодняшний live-день "
            "последним закрытым днём. "
            "Если пользователь просит сравнить сегодня и вчера, "
            "НЕ используй этот инструмент отдельно: используй "
            "compare_current_sales_with_yesterday. "
            "Live-сумма пока включает чеки CRM и не включает "
            "внешние заказы и продажи без чека."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
    ),

    ChatFunctionSpecification(
        name="compare_current_sales_with_yesterday",
        description=(
            "Сравнивает сегодняшний незакрытый день "
            "со вчерашним днём ДО ОДИНАКОВОГО ВРЕМЕНИ "
            "по одной чековой базе checks_raw.csv. "
            "ОБЯЗАТЕЛЬНО используй для запросов "
            "'сравни сегодня и вчера', "
            "'сегодня против вчера', "
            "'как сегодня относительно вчера', "
            "'сегодня лучше или хуже вчера'. "
            "Не вызывай отдельно get_current_sales и "
            "полный закрытый вчерашний день для такого сравнения. "
            "Инструмент сам определяет сегодняшний день, вчера, "
            "актуальный cutoff и рассчитывает изменения. "
            "Внешние заказы и продажи без чека сюда не входят, "
            "поэтому возвращаемая выручка является чековой/кассовой, "
            "а не полной управленческой выручкой магазина."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
    ),

    # ========================================================
    # ПОКРЫТИЕ ДАННЫХ
    # ========================================================

    ChatFunctionSpecification(
        name="get_sales_data_coverage",
        description=(
            "Возвращает только точные границы доступности данных "
            "о продажах и их детализацию. "
            "ОБЯЗАТЕЛЬНО используй, если пользователь спрашивает "
            "'за какие даты есть данные', "
            "'с какого числа есть статистика', "
            "'можешь ли сравнить такую дату', "
            "'какие периоды доступны' или похожий вопрос. "
            "Не используй этот инструмент для расчёта выручки, "
            "чеков, среднего чека или других показателей "
            "за весь период. Для показателей 'за весь период', "
            "'за всё время' или 'с открытия' используй "
            "get_sales_overall_summary. "
            "Не утверждай самостоятельно, что дневные данные "
            "доступны с открытия магазина. "
            "Исторические данные до начала точной дневной "
            "аналитики могут существовать только по полным месяцам, "
            "а январь-февраль 2025 могут быть доступны "
            "только единым объединённым периодом."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
    ),

    # ========================================================
    # ЗАКРЫТЫЕ ДНИ
    # ========================================================

    ChatFunctionSpecification(
        name="get_latest_sales_day",
        description=(
            "Возвращает последний закрытый день магазина "
            "и сравнение с предыдущим закрытым днём. "
            "Не используй для сегодняшнего незакрытого дня: "
            "для него есть get_current_sales."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
    ),

    ChatFunctionSpecification(
        name="get_daily_sales",
        description=(
            "Возвращает продажи за одну конкретную "
            "закрытую дату в формате ДД.ММ.ГГГГ. "
            "Точные дневные данные доступны не за всю историю. "
            "Если пользователь спрашивает, за какие даты "
            "есть дневные данные, используй "
            "get_sales_data_coverage. "
            "Не используй для сегодняшнего незакрытого дня."
        ),
        parameters={
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": (
                        "Дата ДД.ММ.ГГГГ или latest"
                    ),
                },
            },
            "required": [
                "date",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="compare_sales_days",
        description=(
            "Сравнивает два конкретных закрытых дня продаж. "
            "Используй только для двух отдельных дат. "
            "Точные дневные данные доступны не за всю историю. "
            "Если одна из дат недоступна, не придумывай "
            "дневные показатели из месячного итога."
        ),
        parameters={
            "type": "object",
            "properties": {
                "date_a": {
                    "type": "string",
                    "description": (
                        "Первая дата ДД.ММ.ГГГГ"
                    ),
                },
                "date_b": {
                    "type": "string",
                    "description": (
                        "Вторая дата ДД.ММ.ГГГГ"
                    ),
                },
            },
            "required": [
                "date_a",
                "date_b",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="get_recent_sales",
        description=(
            "Возвращает несколько последних "
            "закрытых дней продаж."
        ),
        parameters={
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": (
                        "Количество последних дней"
                    ),
                },
            },
            "required": [
                "days",
            ],
        },
    ),

    # ========================================================
    # МЕСЯЦЫ ПРОДАЖ
    # ========================================================

    ChatFunctionSpecification(
        name="get_month_summary",
        description=(
            "Возвращает показатели одного календарного "
            "месяца продаж. "
            "Для текущего месяца возвращает доступную часть "
            "по последнему закрытому дню."
        ),
        parameters={
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": (
                        "Год"
                    ),
                },
                "month": {
                    "type": "integer",
                    "description": (
                        "Месяц от 1 до 12"
                    ),
                },
            },
            "required": [
                "year",
                "month",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="compare_sales_months",
        description=(
            "Сравнивает два календарных месяца "
            "по показателям продаж. "
            "Для текущего незавершённого месяца Python делает "
            "сопоставимое like-for-like сравнение "
            "одинакового числа дней. "
            "Используй для выручки, чеков, среднего чека, "
            "КТЧ, внешних заказов и других показателей продаж. "
            "Для прибыли, маржинальности, рентабельности, EBITDA, "
            "роялти и расходов используй финансовые инструменты."
        ),
        parameters={
            "type": "object",
            "properties": {
                "year_a": {
                    "type": "integer",
                    "description": (
                        "Год первого месяца"
                    ),
                },
                "month_a": {
                    "type": "integer",
                    "description": (
                        "Первый месяц от 1 до 12"
                    ),
                },
                "year_b": {
                    "type": "integer",
                    "description": (
                        "Год второго месяца"
                    ),
                },
                "month_b": {
                    "type": "integer",
                    "description": (
                        "Второй месяц от 1 до 12"
                    ),
                },
            },
            "required": [
                "year_a",
                "month_a",
                "year_b",
                "month_b",
            ],
        },
    ),

    # ========================================================
    # ПРОИЗВОЛЬНЫЕ ПЕРИОДЫ ПРОДАЖ
    # ========================================================

    ChatFunctionSpecification(
        name="get_sales_period_summary",
        description=(
            "Возвращает показатели продаж за конкретный "
            "диапазон дат. "
            "Используй для выручки, чеков, среднего чека, "
            "КТЧ, внешних заказов и других показателей продаж, "
            "когда пользователь явно задаёт начало и конец "
            "периода. "
            "Если пользователь назвал обе границы, обязательно "
            "передай обе даты без изменения. "
            "Не используй этот инструмент для запросов "
            "'за весь период', 'за всё время' или 'с открытия': "
            "для них используй get_sales_overall_summary. "
            "Для финансовых показателей ОПиУ используй "
            "get_finance_period_summary или get_finance_metric."
        ),
        parameters={
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": (
                        "Начальная дата ДД.ММ.ГГГГ"
                    ),
                },
                "end_date": {
                    "type": "string",
                    "description": (
                        "Конечная дата ДД.ММ.ГГГГ"
                    ),
                },
            },
            "required": [
                "start_date",
                "end_date",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="get_sales_overall_summary",
        description=(
            "Возвращает показатели продаж за весь доступный "
            "период работы: от начала доступной управленческой "
            "истории до последнего закрытого дня. "
            "ОБЯЗАТЕЛЬНО используй для запросов вроде "
            "'за весь период', 'за всё время', "
            "'за всё время работы', 'с открытия', "
            "'какой средний чек за весь период', "
            "'сколько всего было выручки за всё время'. "
            "У инструмента нет дат: Python сам определяет "
            "корректные границы. "
            "Не используй get_sales_data_coverage для расчёта "
            "таких показателей."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
    ),

    ChatFunctionSpecification(
        name="compare_sales_periods",
        description=(
            "Сравнивает два произвольных диапазона дат "
            "по показателям продаж: выручке, чекам, "
            "среднему чеку, КТЧ, внешним заказам "
            "и другим доступным метрикам. "
            "Для прибыли, маржинальности, рентабельности, "
            "EBITDA, роялти, себестоимости и расходов "
            "используй compare_finance_periods."
        ),
        parameters={
            "type": "object",
            "properties": {
                "start_a": {
                    "type": "string",
                    "description": (
                        "Начало первого периода ДД.ММ.ГГГГ"
                    ),
                },
                "end_a": {
                    "type": "string",
                    "description": (
                        "Конец первого периода ДД.ММ.ГГГГ"
                    ),
                },
                "start_b": {
                    "type": "string",
                    "description": (
                        "Начало второго периода ДД.ММ.ГГГГ"
                    ),
                },
                "end_b": {
                    "type": "string",
                    "description": (
                        "Конец второго периода ДД.ММ.ГГГГ"
                    ),
                },
            },
            "required": [
                "start_a",
                "end_a",
                "start_b",
                "end_b",
            ],
        },
    ),

    # ========================================================
    # ГОДЫ ПРОДАЖ
    # ========================================================

    ChatFunctionSpecification(
        name="get_sales_year_summary",
        description=(
            "Возвращает сводку продаж за календарный год. "
            "Используй для выручки, чеков и других "
            "показателей продаж. "
            "Если вопрос про прибыль, маржинальность, "
            "рентабельность или расходы года, "
            "используй финансовые инструменты."
        ),
        parameters={
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": (
                        "Календарный год"
                    ),
                },
            },
            "required": [
                "year",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="compare_sales_years",
        description=(
            "Сравнивает два календарных года по продажам. "
            "Для прибыли, рентабельности и расходов "
            "используй compare_finance_periods "
            "с диапазонами месяцев."
        ),
        parameters={
            "type": "object",
            "properties": {
                "year_a": {
                    "type": "integer",
                    "description": (
                        "Первый год"
                    ),
                },
                "year_b": {
                    "type": "integer",
                    "description": (
                        "Второй год"
                    ),
                },
            },
            "required": [
                "year_a",
                "year_b",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="rank_sales_periods",
        description=(
            "Ранжирует дни, месяцы или годы только "
            "по показателям продаж: total_revenue, "
            "average_check, checks, items, ktch, "
            "check_revenue_net, external_total, external_orders. "
            "Не используй этот инструмент для прибыли, маржи, "
            "маржинальности, рентабельности, EBITDA, роялти "
            "или расходов: это финансовые показатели ОПиУ."
        ),
        parameters={
            "type": "object",
            "properties": {
                "granularity": {
                    "type": "string",
                    "enum": [
                        "day",
                        "month",
                        "year",
                    ],
                    "description": (
                        "day, month или year"
                    ),
                },
                "metric": {
                    "type": "string",
                    "description": (
                        "total_revenue, average_check, checks, "
                        "items, ktch, check_revenue_net, "
                        "external_total или external_orders"
                    ),
                },
                "date_from": {
                    "type": "string",
                    "description": (
                        "Необязательная дата от ДД.ММ.ГГГГ"
                    ),
                },
                "date_to": {
                    "type": "string",
                    "description": (
                        "Необязательная дата до ДД.ММ.ГГГГ"
                    ),
                },
                "order": {
                    "type": "string",
                    "enum": [
                        "desc",
                        "asc",
                    ],
                    "description": (
                        "desc — максимум, asc — минимум"
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        "Сколько периодов вернуть"
                    ),
                },
                "min_checks": {
                    "type": "integer",
                    "description": (
                        "Минимальное количество чеков"
                    ),
                },
                "include_partial": {
                    "type": "boolean",
                    "description": (
                        "Включать незавершённые месяцы или годы. "
                        "По умолчанию false."
                    ),
                },
            },
            "required": [
                "granularity",
                "metric",
            ],
        },
    ),

    # ========================================================
    # ФИНАНСЫ / ОПиУ
    # ========================================================

    ChatFunctionSpecification(
        name="rank_finance_months",
        description=(
            "Строит рейтинг месяцев по финансовому показателю "
            "из управленческого ОПиУ. "
            "Используй для вопросов вроде "
            "«какой месяц был самым маржинальным?», "
            "«топ месяцев по чистой прибыли», "
            "«худший месяц по EBITDA», "
            "«в каком месяце была самая высокая рентабельность продаж?». "
            "По умолчанию незакрытые месяцы исключаются. "
            "Не используй rank_sales_periods для рейтингов "
            "по прибыли, маржинальности, EBITDA, рентабельности, "
            "роялти, себестоимости или другим показателям ОПиУ."
        ),
        parameters={
            "type":
                "object",

            "properties": {
                "metric": {
                    "type":
                        "string",

                    "description":
                        (
                            "Финансовый показатель. "
                            "Можно передавать естественное русское название "
                            "или внутреннее имя, например: "
                            "маржинальность, gross_margin_pct, "
                            "чистая прибыль, net_profit, "
                            "EBITDA, ebitda_margin_pct, "
                            "рентабельность продаж, sales_margin_pct, "
                            "чистая рентабельность, net_margin_pct, "
                            "роялти, royalty_share_pct, "
                            "торговая наценка."
                        ),
                },

                "start_month": {
                    "type":
                        "string",

                    "description":
                        (
                            "Необязательный первый месяц рейтинга "
                            "в формате YYYY-MM."
                        ),
                },

                "end_month": {
                    "type":
                        "string",

                    "description":
                        (
                            "Необязательный последний месяц рейтинга "
                            "в формате YYYY-MM."
                        ),
                },

                "order": {
                    "type":
                        "string",

                    "description":
                        (
                            "Порядок рейтинга: "
                            "desc — от большего к меньшему, "
                            "asc — от меньшего к большему. "
                            "Для «самый высокий» используй desc, "
                            "для «самый низкий» или «худший» — asc."
                        ),
                },

                "limit": {
                    "type":
                        "integer",

                    "description":
                        (
                            "Сколько месяцев вернуть. "
                            "Для вопроса про один лучший месяц — 1."
                        ),
                },

                "include_partial": {
                    "type":
                        "boolean",

                    "description":
                        (
                            "Включать ли незакрытые месяцы. "
                            "Обычно false. "
                            "Ставь true только если пользователь "
                            "явно просит учитывать текущий незакрытый месяц."
                        ),
                },
            },

            "required": [
                "metric",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="get_finance_metric",
        description=(
            "Возвращает один финансовый показатель "
            "из управленческого ОПиУ за диапазон целых месяцев "
            "или за весь доступный закрытый период. "
            "ОБЯЗАТЕЛЬНО используй для вопросов про прибыль, "
            "маржу, маржинальность, рентабельность, "
            "себестоимость, валовую прибыль, EBITDA, "
            "чистую прибыль, роялти, аренду, зарплату, "
            "эквайринг, комиссии доставок, рекламу, налоги "
            "и долю расходов в выручке. "
            "Если start_month и end_month не переданы, "
            "считается весь доступный период; "
            "текущий незакрытый месяц по умолчанию исключается. "
            "Простое слово 'рентабельность' неоднозначно: "
            "Python вернёт варианты, не выбирай один вид сам. "
            "Периоды задаются целыми месяцами, например 2026-01. "
            "Нельзя молча рассчитывать финансовые показатели "
            "для части месяца: в ОПиУ нет дневной "
            "детализации расходов."
        ),
        parameters={
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "description": (
                        "Название показателя обычным языком: "
                        "маржинальность, чистая рентабельность, "
                        "EBITDA, роялти, аренда, налоги, "
                        "себестоимость и т.д."
                    ),
                },
                "start_month": {
                    "type": "string",
                    "description": (
                        "Необязательный первый месяц периода: "
                        "YYYY-MM, MM.YYYY или название месяца и год"
                    ),
                },
                "end_month": {
                    "type": "string",
                    "description": (
                        "Необязательный последний месяц периода: "
                        "YYYY-MM, MM.YYYY или название месяца и год"
                    ),
                },
                "include_partial": {
                    "type": "boolean",
                    "description": (
                        "Включать текущий незакрытый месяц. "
                        "По умолчанию false. "
                        "При true результат предварительный."
                    ),
                },
            },
            "required": [
                "metric",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="get_finance_period_summary",
        description=(
            "Возвращает полный финансовый отчёт ОПиУ "
            "за диапазон целых месяцев: выручку, себестоимость, "
            "валовую прибыль, маржинальность, наценку, "
            "коммерческие расходы, аренду, банковские расходы, "
            "эквайринг, комиссии доставок, роялти, зарплату, "
            "рекламу, списания, прибыль от продаж, EBITDA, "
            "финансовую деятельность, прибыль до налогов, "
            "налоги, чистую прибыль и рассчитанные "
            "рентабельности. "
            "Если месяцы не указаны, возвращает весь "
            "доступный закрытый период. "
            "Текущий месяц по умолчанию исключается. "
            "Используй, когда пользователь просит финансовый "
            "отчёт, ОПиУ, все финансовые показатели "
            "или структуру расходов. "
            "Не используй для части месяца: "
            "финансовые данные месячные."
        ),
        parameters={
            "type": "object",
            "properties": {
                "start_month": {
                    "type": "string",
                    "description": (
                        "Необязательный первый месяц: "
                        "YYYY-MM, MM.YYYY или название месяца и год"
                    ),
                },
                "end_month": {
                    "type": "string",
                    "description": (
                        "Необязательный последний месяц: "
                        "YYYY-MM, MM.YYYY или название месяца и год"
                    ),
                },
                "include_partial": {
                    "type": "boolean",
                    "description": (
                        "Включать текущий незакрытый месяц. "
                        "По умолчанию false."
                    ),
                },
            },
        },
    ),

    ChatFunctionSpecification(
        name="compare_finance_periods",
        description=(
            "Сравнивает два финансовых периода "
            "по управленческому ОПиУ. "
            "Сравнивает не только выручку, но и себестоимость, "
            "валовую прибыль, маржинальность, наценку, роялти, "
            "аренду, зарплату, эквайринг, комиссии доставок, "
            "рекламу, списания, прибыль от продаж, EBITDA, "
            "прибыль до налогов, налоги, чистую прибыль "
            "и рентабельности. "
            "Используй для запросов вроде "
            "'сравни I и II квартал по финансам' "
            "или 'сравни январь-март с апрелем-июнем "
            "по маржинальности и прибыли'. "
            "Границы задаются целыми месяцами. "
            "Не округляй запрос с частичных дат "
            "до полных месяцев без явного согласия."
        ),
        parameters={
            "type": "object",
            "properties": {
                "start_a": {
                    "type": "string",
                    "description": (
                        "Первый месяц периода A, например 2026-01"
                    ),
                },
                "end_a": {
                    "type": "string",
                    "description": (
                        "Последний месяц периода A, например 2026-03"
                    ),
                },
                "start_b": {
                    "type": "string",
                    "description": (
                        "Первый месяц периода B, например 2026-04"
                    ),
                },
                "end_b": {
                    "type": "string",
                    "description": (
                        "Последний месяц периода B, например 2026-06"
                    ),
                },
                "include_partial": {
                    "type": "boolean",
                    "description": (
                        "Включать текущий незакрытый месяц. "
                        "По умолчанию false."
                    ),
                },
            },
            "required": [
                "start_a",
                "end_a",
                "start_b",
                "end_b",
            ],
        },
    ),

    # ========================================================
    # RFM
    # ========================================================

    ChatFunctionSpecification(
        name="get_rfm_summary",
        description=(
            "Возвращает общую RFM-структуру "
            "клиентской базы."
        ),
        parameters={
            "type": "object",
            "properties": {},
        },
    ),

    ChatFunctionSpecification(
        name="get_rfm_segment",
        description=(
            "Возвращает клиентов конкретного RFM-сегмента."
        ),
        parameters={
            "type": "object",
            "properties": {
                "segment": {
                    "type": "string",
                    "description": (
                        "Название RFM-сегмента"
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": (
                        "Количество клиентов"
                    ),
                },
                "sort_by": {
                    "type": "string",
                    "description": (
                        "monetary, recency, frequency или overdue"
                    ),
                },
            },
            "required": [
                "segment",
            ],
        },
    ),

    # ========================================================
    # ОБЗВОН
    # ========================================================

    ChatFunctionSpecification(
        name="get_contact_candidates",
        description=(
            "Возвращает список клиентов для удержания "
            "или возврата. "
            "Используй, если нужен список или топ "
            "нескольких клиентов."
        ),
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": (
                        "Количество клиентов"
                    ),
                },
                "mode": {
                    "type": "string",
                    "description": (
                        "retain или reactivate"
                    ),
                },
            },
            "required": [
                "limit",
                "mode",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="get_next_call_candidate",
        description=(
            "Выбирает одного следующего клиента для звонка. "
            "Клиенты, уже предложенные сегодня "
            "в этом разговоре, автоматически исключаются "
            "Python-кодом. "
            "Используй для 'кому сейчас позвонить', "
            "'а кому ещё', 'кто следующий'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "description": (
                        "retain — удержание; "
                        "reactivate — возврат потерянного"
                    ),
                },
            },
            "required": [
                "mode",
            ],
        },
    ),

    ChatFunctionSpecification(
        name="get_customer_call_assessment",
        description=(
            "Оценивает, стоит ли звонить конкретному клиенту "
            "и насколько он приоритетен для обзвона. "
            "Приоритет рассчитывается Python-кодом."
        ),
        parameters={
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": (
                        "ID конкретного клиента в CRM"
                    ),
                },
            },
            "required": [
                "customer_id",
            ],
        },
    ),
]


REQUEST_FUNCTION_SPECS = [
    *TEXT_FUNCTION_SPECS,
]


# Backward-compatible aliases for existing text-only callers.
FUNCTION_SPECS = TEXT_FUNCTION_SPECS


TEXT_TOOLS = [
    ChatTool(
        functions={
            "specifications":
                TEXT_FUNCTION_SPECS,
        }
    )
]


REQUEST_TOOLS = [
    ChatTool(
        functions={
            "specifications":
                REQUEST_FUNCTION_SPECS,
        }
    )
]


TOOLS = TEXT_TOOLS


def build_sales_data_coverage():
    return get_available_sales_coverage()


def build_latest_day_report():
    latest = get_latest_sales_day()

    if latest.get(
        "status"
    ) != "ok":
        return latest

    result = {
        "status":
            "ok",

        "day":
            latest[
                "day"
            ],
    }

    recent = get_recent_sales(
        2
    )

    days = recent.get(
        "days",
        [],
    )

    if len(
        days
    ) >= 2:
        result[
            "previous_day"
        ] = days[
            -2
        ]

        result[
            "comparison_with_previous_day"
        ] = compare_sales_days(
            days[-2][
                "date"
            ],
            days[-1][
                "date"
            ],
        )

    return result


def build_sales_period_summary(
    start_date=None,
    end_date=None,
):
    def clean_optional_date(
        value,
    ):
        if value is None:
            return None

        value = str(
            value
        ).strip()

        if not value:
            return None

        return value

    start_date = clean_optional_date(
        start_date
    )

    end_date = clean_optional_date(
        end_date
    )

    if (
        start_date is None
        or end_date is None
    ):
        coverage = (
            get_available_sales_coverage()
        )

        if (
            coverage.get(
                "status"
            )
            != "ok"
        ):
            return {
                "status":
                    "coverage_error",

                "message":
                    (
                        "Не удалось определить "
                        "границы доступного "
                        "периода продаж."
                    ),

                "coverage":
                    coverage,
            }

        historical = coverage.get(
            "historical",
            {},
        )

        daily_full = (
            coverage.get(
                "daily_full_management"
            )
            or coverage.get(
                "daily"
            )
            or {}
        )

        daily_checks = coverage.get(
            "daily_checks",
            {},
        )

        if start_date is None:
            start_date = (
                historical.get(
                    "start_date"
                )
                or daily_checks.get(
                    "start_date"
                )
                or daily_full.get(
                    "start_date"
                )
            )

        if end_date is None:
            end_date = (
                daily_full.get(
                    "end_date"
                )
                or coverage.get(
                    "daily",
                    {},
                ).get(
                    "end_date"
                )
                or daily_checks.get(
                    "end_date"
                )
            )

    if (
        start_date is None
        or end_date is None
    ):
        return {
            "status":
                "coverage_error",

            "message":
                (
                    "Не удалось определить "
                    "полные границы периода "
                    "для расчёта продаж."
                ),
        }

    return get_period_summary(
        start_date,
        end_date,
    )


def run_tool(
    name,
    arguments,
    conversation_id="console",
):
    if name == "get_customer_profile":
        return get_customer_profile(
            arguments[
                "customer_id"
            ]
        )

    if name == "get_top_customers":
        return get_top_customers(
            arguments.get(
                "limit",
                5,
            )
        )

    if name == "find_customer_by_name":
        return find_customer_by_name(
            arguments[
                "query"
            ],
            arguments.get(
                "limit",
                10,
            ),
        )

    if name == "get_current_sales":
        return get_current_sales()

    if name == "compare_current_sales_with_yesterday":
        return compare_current_sales_with_yesterday()

    if name == "get_sales_data_coverage":
        return build_sales_data_coverage()

    if name == "get_latest_sales_day":
        return build_latest_day_report()

    if name == "get_daily_sales":
        return get_daily_sales(
            arguments.get(
                "date",
                "latest",
            )
        )

    if name == "compare_sales_days":
        return compare_sales_days(
            arguments[
                "date_a"
            ],
            arguments[
                "date_b"
            ],
        )

    if name == "get_recent_sales":
        return get_recent_sales(
            arguments.get(
                "days",
                7,
            )
        )

    if name == "get_month_summary":
        return get_month_summary(
            arguments[
                "year"
            ],
            arguments[
                "month"
            ],
        )

    if name == "compare_sales_months":
        return compare_sales_months(
            arguments[
                "year_a"
            ],
            arguments[
                "month_a"
            ],
            arguments[
                "year_b"
            ],
            arguments[
                "month_b"
            ],
        )

    if name == "get_sales_period_summary":
        return get_period_summary(
            arguments[
                "start_date"
            ],
            arguments[
                "end_date"
            ],
        )

    if name == "get_sales_overall_summary":
        return build_sales_period_summary()

    if name == "compare_sales_periods":
        return compare_sales_periods(
            arguments[
                "start_a"
            ],
            arguments[
                "end_a"
            ],
            arguments[
                "start_b"
            ],
            arguments[
                "end_b"
            ],
        )

    if name == "get_sales_year_summary":
        return get_year_summary(
            arguments[
                "year"
            ]
        )

    if name == "compare_sales_years":
        return compare_sales_years(
            arguments[
                "year_a"
            ],
            arguments[
                "year_b"
            ],
        )

    if name == "rank_sales_periods":
        return rank_sales_periods(
            granularity=arguments[
                "granularity"
            ],
            metric=arguments[
                "metric"
            ],
            date_from=arguments.get(
                "date_from"
            ),
            date_to=arguments.get(
                "date_to"
            ),
            order=arguments.get(
                "order",
                "desc",
            ),
            limit=arguments.get(
                "limit",
                5,
            ),
            min_checks=arguments.get(
                "min_checks",
                0,
            ),
            include_partial=arguments.get(
                "include_partial",
                False,
            ),
        )

    if name == "rank_finance_months":
        return rank_finance_months(
            metric=arguments[
                "metric"
            ],
            start_month=arguments.get(
                "start_month"
            ),
            end_month=arguments.get(
                "end_month"
            ),
            order=arguments.get(
                "order",
                "desc",
            ),
            limit=arguments.get(
                "limit",
                5,
            ),
            include_partial=arguments.get(
                "include_partial",
                False,
            ),
        )

    if name == "get_finance_metric":
        return get_finance_metric(
            metric=arguments[
                "metric"
            ],
            start_month=arguments.get(
                "start_month"
            ),
            end_month=arguments.get(
                "end_month"
            ),
            include_partial=arguments.get(
                "include_partial",
                False,
            ),
        )

    if name == "get_finance_period_summary":
        return get_finance_period(
            start_month=arguments.get(
                "start_month"
            ),
            end_month=arguments.get(
                "end_month"
            ),
            include_partial=arguments.get(
                "include_partial",
                False,
            ),
        )

    if name == "compare_finance_periods":
        return compare_finance_periods(
            start_a=arguments[
                "start_a"
            ],
            end_a=arguments[
                "end_a"
            ],
            start_b=arguments[
                "start_b"
            ],
            end_b=arguments[
                "end_b"
            ],
            include_partial=arguments.get(
                "include_partial",
                False,
            ),
        )

    if name == "get_rfm_summary":
        return get_rfm_summary()

    if name == "get_rfm_segment":
        return get_rfm_segment(
            segment=arguments[
                "segment"
            ],
            limit=arguments.get(
                "limit",
                10,
            ),
            sort_by=arguments.get(
                "sort_by",
                "monetary",
            ),
        )

    if name == "get_contact_candidates":
        return get_contact_candidates(
            limit=arguments.get(
                "limit",
                10,
            ),
            mode=arguments.get(
                "mode",
                "retain",
            ),
        )

    if name == "get_next_call_candidate":
        mode = arguments.get(
            "mode",
            "retain",
        )

        excluded = (
            get_today_suggested_customer_ids(
                conversation_id,
                mode=mode,
            )
        )

        return get_next_call_candidate(
            mode=mode,
            exclude_customer_ids=excluded,
        )

    if name == "get_customer_call_assessment":
        return get_customer_call_assessment(
            arguments[
                "customer_id"
            ]
        )

    return {
        "error":
            "unknown_tool",

        "tool":
            name,
    }


def compact_result(
    tool_name,
    result,
):
    if tool_name == "get_top_customers":
        customers = []

        for customer in result.get(
            "customers",
            [],
        ):
            customers.append(
                {
                    "position":
                        customer.get(
                            "position"
                        ),

                    "customer_id":
                        customer.get(
                            "customer_id"
                        ),

                    "name":
                        customer.get(
                            "name"
                        ),

                    "lastname":
                        customer.get(
                            "lastname"
                        ),

                    "purchases":
                        customer.get(
                            "purchases"
                        ),

                    "total_rubles":
                        customer.get(
                            "total_rubles"
                        ),

                    "average_check_rubles":
                        customer.get(
                            "average_check_rubles"
                        ),

                    "first_purchase":
                        customer.get(
                            "first_purchase"
                        ),

                    "last_purchase":
                        customer.get(
                            "last_purchase"
                        ),
                }
            )

        return {
            "ranking":
                result.get(
                    "ranking"
                ),

            "customers":
                customers,
        }

    if tool_name == "get_customer_profile":
        return {
            "customer":
                result.get(
                    "customer"
                ),

            "statistics":
                result.get(
                    "statistics"
                ),

            "top_products":
                result.get(
                    "top_products",
                    [],
                )[:5],
        }

    if tool_name == "find_customer_by_name":
        if result.get(
            "status"
        ) == "unique_match":
            profile = result.get(
                "profile",
                {},
            )

            return {
                "status":
                    "unique_match",

                "query":
                    result.get(
                        "query"
                    ),

                "profile": {
                    "customer":
                        profile.get(
                            "customer"
                        ),

                    "statistics":
                        profile.get(
                            "statistics"
                        ),

                    "top_products":
                        profile.get(
                            "top_products",
                            [],
                        )[:5],
                },
            }

    if tool_name == "get_finance_period_summary":
        if result.get(
            "status"
        ) != "ok":
            return result

        nonzero_line_items = [
            item
            for item in result.get(
                "line_items",
                [],
            )
            if abs(
                float(
                    item.get(
                        "amount",
                        0,
                    )
                    or 0
                )
            ) > 0.000001
        ]

        return {
            "status":
                result.get(
                    "status"
                ),

            "source":
                result.get(
                    "source"
                ),

            "requested_period":
                result.get(
                    "requested_period"
                ),

            "actual_period":
                result.get(
                    "actual_period"
                ),

            "months_count":
                result.get(
                    "months_count"
                ),

            "contains_partial_month":
                result.get(
                    "contains_partial_month"
                ),

            "excluded_partial_months":
                result.get(
                    "excluded_partial_months"
                ),

            "metrics":
                result.get(
                    "metrics"
                ),

            "line_items":
                nonzero_line_items,

            "warnings":
                result.get(
                    "warnings"
                ),

            "calculation_notes":
                result.get(
                    "calculation_notes"
                ),
        }

    if tool_name == "compare_finance_periods":
        if result.get(
            "status"
        ) != "ok":
            return result

        period_a = result.get(
            "period_a",
            {},
        )

        period_b = result.get(
            "period_b",
            {},
        )

        return {
            "status":
                result.get(
                    "status"
                ),

            "source":
                result.get(
                    "source"
                ),

            "period_a": {
                "actual_period":
                    period_a.get(
                        "actual_period"
                    ),

                "months_count":
                    period_a.get(
                        "months_count"
                    ),

                "contains_partial_month":
                    period_a.get(
                        "contains_partial_month"
                    ),

                "metrics":
                    period_a.get(
                        "metrics"
                    ),

                "warnings":
                    period_a.get(
                        "warnings"
                    ),
            },

            "period_b": {
                "actual_period":
                    period_b.get(
                        "actual_period"
                    ),

                "months_count":
                    period_b.get(
                        "months_count"
                    ),

                "contains_partial_month":
                    period_b.get(
                        "contains_partial_month"
                    ),

                "metrics":
                    period_b.get(
                        "metrics"
                    ),

                "warnings":
                    period_b.get(
                        "warnings"
                    ),
            },

            "comparison":
                result.get(
                    "comparison"
                ),
        }

    return result


def get_tool_names():
    return [
        specification.name
        for specification in FUNCTION_SPECS
    ]


def print_short_result(
    title,
    result,
):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)
    print()

    print(
        result
    )


def demo():
    print()
    print("=" * 70)
    print(
        "AGENT TOOLS — TEST"
    )
    print("=" * 70)
    print()

    print(
        "Зарегистрированные инструменты:"
    )

    for name in get_tool_names():
        print(
            f"• {name}"
        )

    print()
    print(
        f"Всего: {len(FUNCTION_SPECS)}"
    )

    print_short_result(
        "ПОКРЫТИЕ ДАННЫХ ПРОДАЖ",
        run_tool(
            "get_sales_data_coverage",
            {},
            conversation_id=(
                "__agent_tools_test__"
            ),
        ),
    )

    print_short_result(
        "LIVE-ПРОДАЖИ ЗА СЕГОДНЯ",
        run_tool(
            "get_current_sales",
            {},
            conversation_id=(
                "__agent_tools_test__"
            ),
        ),
    )

    print_short_result(
        "МАРЖИНАЛЬНОСТЬ ЗА ВЕСЬ ЗАКРЫТЫЙ ПЕРИОД",
        run_tool(
            "get_finance_metric",
            {
                "metric":
                    "маржинальность",
            },
            conversation_id=(
                "__agent_tools_test__"
            ),
        ),
    )

    print_short_result(
        "I КВАРТАЛ 2026 VS II КВАРТАЛ 2026 — ФИНАНСЫ",
        run_tool(
            "compare_finance_periods",
            {
                "start_a":
                    "2026-01",

                "end_a":
                    "2026-03",

                "start_b":
                    "2026-04",

                "end_b":
                    "2026-06",
            },
            conversation_id=(
                "__agent_tools_test__"
            ),
        ),
    )


if __name__ == "__main__":
    demo()
