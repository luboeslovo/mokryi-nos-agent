import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import agent_prompts
import agent_tools
from agent_response import AgentResponse


class InventoryReportAgentRegistrationTests(unittest.TestCase):
    def test_inventory_tool_is_only_in_request_registry(self):
        text_names = [spec.name for spec in agent_tools.TEXT_FUNCTION_SPECS]
        request_names = [spec.name for spec in agent_tools.REQUEST_FUNCTION_SPECS]

        self.assertEqual(len(text_names), 27)
        self.assertEqual(len(request_names), 28)
        self.assertNotIn("generate_inventory_movement_report", text_names)
        self.assertEqual(
            request_names.count("generate_inventory_movement_report"),
            1,
        )
        self.assertIs(agent_tools.FUNCTION_SPECS, agent_tools.TEXT_FUNCTION_SPECS)
        self.assertIs(agent_tools.TOOLS, agent_tools.TEXT_TOOLS)

    def test_inventory_tool_schema_is_exactly_scoped(self):
        specification = agent_tools.INVENTORY_MOVEMENT_REPORT_SPEC
        parameters = specification.parameters
        properties = parameters["properties"]

        self.assertEqual(specification.name, "generate_inventory_movement_report")
        self.assertEqual(parameters["required"], ["period_kind"])
        self.assertEqual(
            properties["period_kind"]["enum"],
            [
                "explicit_range",
                "named_month",
                "previous_month",
                "current_month",
                "day_range_in_month",
            ],
        )
        self.assertEqual(properties["start_day"]["minimum"], 1)
        self.assertEqual(properties["start_day"]["maximum"], 31)
        self.assertEqual(properties["end_day"]["minimum"], 1)
        self.assertEqual(properties["end_day"]["maximum"], 31)
        self.assertEqual(properties["month"]["maximum"], 12)
        self.assertEqual(properties["year"]["maximum"], 9999)
        self.assertEqual(
            set(properties),
            {
                "period_kind",
                "start_date",
                "end_date",
                "start_day",
                "end_day",
                "month",
                "year",
                "brand",
                "category",
            },
        )

    def test_run_tool_returns_adapter_response_and_preserves_arguments(self):
        arguments = {
            "period_kind": "named_month",
            "month": 8,
        }
        expected = AgentResponse(text="Документ подготовлен.")

        with patch.object(
            agent_tools,
            "run_inventory_report_agent_tool",
            return_value=expected,
        ) as adapter_mock:
            actual = agent_tools.run_tool(
                "generate_inventory_movement_report",
                arguments,
                conversation_id="test:inventory",
            )

        self.assertIs(actual, expected)
        adapter_mock.assert_called_once_with(arguments)

    def test_prompt_routes_named_month_report_without_inventing_year(self):
        prompt = agent_prompts.build_main_system_prompt("03.09.2026")

        self.assertIn("отчёт движения товара за август", prompt)
        self.assertIn("period_kind=named_month", prompt)
        self.assertIn("year передавай только когда пользователь явно", prompt)
        self.assertIn("В запросах аналитики продаж", prompt)

    def test_prompt_routes_day_range_and_previous_month(self):
        prompt = agent_prompts.build_main_system_prompt("03.09.2026")

        self.assertIn("с 1 по 18 августа", prompt)
        self.assertIn("period_kind=day_range_in_month", prompt)
        self.assertIn("period_kind=previous_month", prompt)
        self.assertIn("period_kind=current_month", prompt)

    def test_prompt_forbids_llm_owned_period_and_path_fields(self):
        prompt = agent_prompts.build_main_system_prompt("03.09.2026")

        self.assertIn("Не придумывай отсутствующий год или границу периода", prompt)
        self.assertIn("не превращай day_range_in_month в полные даты", prompt)
        self.assertIn("не передавай output_path или reference_date", prompt)
        self.assertIn("Конкретные границы определяет Python resolver", prompt)

    def test_prompt_does_not_route_ordinary_intake_question_to_document(self):
        prompt = agent_prompts.build_main_system_prompt("03.09.2026")

        self.assertIn("сколько товара пришло в августе?", prompt)
        self.assertIn("не означает создание файла", prompt)


if __name__ == "__main__":
    unittest.main()
