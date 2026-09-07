import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

with patch("keyring.get_password", return_value="test-authorization-key"), patch(
    "gigachat.GigaChat"
):
    import agent_core
    import agent_tools

from agent_response import AgentResponse, DocumentArtifact


def chat_response(content="", function_call=None):
    return SimpleNamespace(
        messages=[
            SimpleNamespace(
                content=content,
                function_call=function_call,
            )
        ]
    )


def tool_call(name, arguments=None):
    return SimpleNamespace(
        name=name,
        arguments={} if arguments is None else arguments,
    )


class AgentCoreResponseTests(unittest.TestCase):
    def setUp(self):
        patchers = [
            patch.object(agent_core, "get_recent_messages", return_value=[]),
            patch.object(agent_core, "get_last_call_suggestion", return_value=None),
            patch.object(agent_core, "get_latest_data_date", return_value=None),
            patch.object(
                agent_core,
                "is_customer_list_call_followup",
                return_value=False,
            ),
            patch.object(agent_core, "is_next_call_followup", return_value=False),
            patch.object(
                agent_core,
                "is_last_call_reason_followup",
                return_value=False,
            ),
            patch.object(agent_core, "save_message"),
        ]
        self.mocks = [patcher.start() for patcher in patchers]
        self.addCleanup(lambda: [patcher.stop() for patcher in reversed(patchers)])

        (
            self.get_recent_messages,
            self.get_last_call_suggestion,
            self.get_latest_data_date,
            self.is_customer_list_call_followup,
            self.is_next_call_followup,
            self.is_last_call_reason_followup,
            self.save_message,
        ) = self.mocks

    def test_text_and_request_registries_are_ready_to_diverge(self):
        text_names = [
            specification.name
            for specification in agent_tools.TEXT_FUNCTION_SPECS
        ]
        request_names = [
            specification.name
            for specification in agent_tools.REQUEST_FUNCTION_SPECS
        ]

        self.assertIsNot(
            agent_tools.TEXT_FUNCTION_SPECS,
            agent_tools.REQUEST_FUNCTION_SPECS,
        )
        self.assertEqual(len(text_names), 27)
        self.assertEqual(len(request_names), 28)
        self.assertNotIn("generate_inventory_movement_report", text_names)
        self.assertEqual(
            request_names.count("generate_inventory_movement_report"),
            1,
        )
        self.assertEqual(request_names[:-1], text_names)
        self.assertIs(
            agent_tools.FUNCTION_SPECS,
            agent_tools.TEXT_FUNCTION_SPECS,
        )
        self.assertIs(agent_tools.TOOLS, agent_tools.TEXT_TOOLS)

    def test_inventory_response_uses_existing_artifact_short_circuit(self):
        private_path = Path(r"C:\secret\private\inventory.xlsx")
        raw_arguments = {
            "period_kind": "day_range_in_month",
            "start_day": 1,
            "year": 2025,
        }
        grounded_arguments = {
            "period_kind": "day_range_in_month",
            "start_day": 1,
            "end_day": 18,
            "month": 8,
        }
        artifact_response = AgentResponse(
            text="Отчёт движения товара за 01.08.2026–18.08.2026 сформирован.",
            documents=(
                DocumentArtifact(
                    path=private_path,
                    filename="inventory.xlsx",
                    mime_type=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                ),
            ),
        )
        create = Mock(
            return_value=chat_response(
                function_call=tool_call(
                    "generate_inventory_movement_report",
                    raw_arguments,
                )
            )
        )

        with patch.object(agent_core.client.chat, "create", create), patch.object(
            agent_core,
            "run_tool",
            return_value=artifact_response,
        ) as run_tool_mock, patch.object(
            agent_core,
            "compact_result",
        ) as compact_result_mock, patch.object(
            agent_core.json,
            "dumps",
        ) as json_dumps_mock:
            response = agent_core.answer_request(
                "Сформируй движение товара с 1 по 18 августа.",
                conversation_id="test:inventory-artifact",
            )

        self.assertIs(response, artifact_response)
        self.assertEqual(create.call_count, 1)
        run_tool_mock.assert_called_once_with(
            "generate_inventory_movement_report",
            grounded_arguments,
            conversation_id="test:inventory-artifact",
        )
        compact_result_mock.assert_not_called()
        json_dumps_mock.assert_not_called()

        first_request = create.call_args.args[0]
        for message in first_request.messages:
            self.assertNotIn(
                str(private_path),
                str(getattr(message, "content", "")),
            )

        self.save_message.assert_has_calls(
            [
                call(
                    "test:inventory-artifact",
                    "user",
                    "Сформируй движение товара с 1 по 18 августа.",
                ),
                call(
                    "test:inventory-artifact",
                    "assistant",
                    artifact_response.text,
                ),
            ]
        )
        for saved_call in self.save_message.call_args_list:
            self.assertNotIn(str(private_path), str(saved_call.args[2]))

    def test_non_inventory_arguments_keep_existing_normalization(self):
        arguments = {
            "segment": "champions",
            "limit": 5,
        }

        normalized = agent_core.normalize_tool_arguments(
            "get_rfm_segment",
            "Покажи сегмент.",
            arguments,
            latest_data_date="17.08.2026",
        )

        self.assertEqual(normalized, arguments)

    def test_answer_question_passes_legacy_text_tools(self):
        with patch.object(
            agent_core,
            "_answer_request",
            return_value=AgentResponse(text="Текстовый ответ."),
        ) as answer_request_mock:
            answer = agent_core.answer_question(
                "Обычный вопрос.",
                conversation_id="test:text-registry",
            )

        self.assertEqual(answer, "Текстовый ответ.")
        answer_request_mock.assert_called_once_with(
            "Обычный вопрос.",
            "test:text-registry",
            agent_core.TEXT_TOOLS,
        )
        text_names = {
            specification.name
            for specification in agent_tools.TEXT_FUNCTION_SPECS
        }
        self.assertNotIn("generate_inventory_movement_report", text_names)

    def test_answer_request_without_tool_returns_agent_response(self):
        create = Mock(return_value=chat_response("Обычный ответ."))

        with patch.object(agent_core.client.chat, "create", create):
            response = agent_core.answer_request(
                "Расскажи о магазине.",
                conversation_id="test:no-tool",
            )

        self.assertIsInstance(response, AgentResponse)
        self.assertEqual(response.text, "Обычный ответ.")
        self.assertEqual(response.documents, ())
        self.assertEqual(create.call_count, 1)

    def test_existing_tool_keeps_second_llm_phase(self):
        first = chat_response(
            function_call=tool_call("get_rfm_summary")
        )
        second = chat_response("Итог по данным Python.")
        create = Mock(side_effect=[first, second])
        raw_result = {
            "status": "ok",
            "customers": 42,
        }

        with patch.object(agent_core.client.chat, "create", create), patch.object(
            agent_core,
            "run_tool",
            return_value=raw_result,
        ) as run_tool_mock, patch.object(
            agent_core,
            "compact_result",
            return_value=raw_result,
        ) as compact_result_mock:
            response = agent_core.answer_request(
                "Покажи RFM.",
                conversation_id="test:ordinary-tool",
            )

        self.assertEqual(create.call_count, 2)
        run_tool_mock.assert_called_once_with(
            "get_rfm_summary",
            {},
            conversation_id="test:ordinary-tool",
        )
        compact_result_mock.assert_called_once_with(
            "get_rfm_summary",
            raw_result,
        )
        self.assertEqual(
            response,
            AgentResponse(
                text="Итог по данным Python.",
                documents=(),
            ),
        )

    def test_agent_response_short_circuits_compaction_and_second_llm(self):
        private_path = Path(r"C:\secret\private\report.xlsx")
        artifact_response = AgentResponse(
            text="Документ подготовлен.",
            documents=(
                DocumentArtifact(
                    path=private_path,
                    filename="report.xlsx",
                    mime_type=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                ),
            ),
        )
        first = chat_response(
            function_call=tool_call("future_document_tool")
        )
        create = Mock(return_value=first)

        with patch.object(agent_core.client.chat, "create", create), patch.object(
            agent_core,
            "run_tool",
            return_value=artifact_response,
        ), patch.object(agent_core, "compact_result") as compact_result_mock, patch.object(
            agent_core.json,
            "dumps",
        ) as json_dumps_mock:
            response = agent_core.answer_request(
                "Подготовь документ.",
                conversation_id="test:artifact",
            )

        self.assertIs(response, artifact_response)
        self.assertEqual(create.call_count, 1)
        compact_result_mock.assert_not_called()
        json_dumps_mock.assert_not_called()

    def test_artifact_path_never_reaches_gigachat_messages(self):
        private_path = Path(r"C:\secret\private\report.xlsx")
        artifact_response = AgentResponse(
            text="Документ подготовлен.",
            documents=(
                DocumentArtifact(
                    path=private_path,
                    filename="report.xlsx",
                    mime_type="application/octet-stream",
                ),
            ),
        )
        create = Mock(
            return_value=chat_response(
                function_call=tool_call("future_document_tool")
            )
        )

        with patch.object(agent_core.client.chat, "create", create), patch.object(
            agent_core,
            "run_tool",
            return_value=artifact_response,
        ):
            agent_core.answer_request(
                "Подготовь документ.",
                conversation_id="test:path",
            )

        for create_call in create.call_args_list:
            request = create_call.args[0]
            for message in request.messages:
                self.assertNotIn(
                    str(private_path),
                    str(getattr(message, "content", "")),
                )

    def test_artifact_memory_contains_only_response_text(self):
        private_path = Path(r"C:\secret\private\report.xlsx")
        artifact_response = AgentResponse(
            text="Документ подготовлен.",
            documents=(
                DocumentArtifact(
                    path=private_path,
                    filename="report.xlsx",
                    mime_type="application/octet-stream",
                ),
            ),
        )

        with patch.object(
            agent_core.client.chat,
            "create",
            return_value=chat_response(
                function_call=tool_call("future_document_tool")
            ),
        ), patch.object(
            agent_core,
            "run_tool",
            return_value=artifact_response,
        ):
            agent_core.answer_request(
                "Подготовь документ.",
                conversation_id="test:memory",
            )

        self.save_message.assert_has_calls(
            [
                call(
                    "test:memory",
                    "user",
                    "Подготовь документ.",
                ),
                call(
                    "test:memory",
                    "assistant",
                    "Документ подготовлен.",
                ),
            ]
        )
        for saved_call in self.save_message.call_args_list:
            content = str(saved_call.args[2])
            self.assertNotIn(str(private_path), content)
            self.assertNotIn("DocumentArtifact", content)
            self.assertNotIn("AgentResponse", content)

    def test_answer_question_returns_str(self):
        create = Mock(return_value=chat_response("Текстовый ответ."))

        with patch.object(agent_core.client.chat, "create", create):
            answer = agent_core.answer_question(
                "Обычный вопрос.",
                conversation_id="test:legacy-text",
            )

        self.assertIsInstance(answer, str)
        self.assertEqual(answer, "Текстовый ответ.")

    def test_answer_question_existing_tool_keeps_two_llm_phases(self):
        create = Mock(
            side_effect=[
                chat_response(
                    function_call=tool_call("get_rfm_summary")
                ),
                chat_response("Старый двухфазный ответ."),
            ]
        )

        with patch.object(agent_core.client.chat, "create", create), patch.object(
            agent_core,
            "run_tool",
            return_value={"status": "ok"},
        ):
            answer = agent_core.answer_question(
                "Покажи RFM.",
                conversation_id="test:legacy-tool",
            )

        self.assertEqual(create.call_count, 2)
        self.assertIsInstance(answer, str)
        self.assertEqual(answer, "Старый двухфазный ответ.")

    def test_deterministic_early_return_supports_both_public_apis(self):
        self.is_customer_list_call_followup.return_value = True

        with patch.object(
            agent_core,
            "handle_customer_list_call_followup",
            return_value="Детерминированный ответ.",
        ), patch.object(agent_core.client.chat, "create") as create:
            response = agent_core.answer_request(
                "Продолжай.",
                conversation_id="test:rich-followup",
            )
            answer = agent_core.answer_question(
                "Продолжай.",
                conversation_id="test:text-followup",
            )

        self.assertEqual(
            response,
            AgentResponse(
                text="Детерминированный ответ.",
                documents=(),
            ),
        )
        self.assertIsInstance(answer, str)
        self.assertEqual(answer, "Детерминированный ответ.")
        create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
