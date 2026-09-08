import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

with patch("keyring.get_password", return_value="test-secret"), patch(
    "gigachat.GigaChat"
):
    import telegram_bot

from agent_response import AgentResponse, DocumentArtifact


class FakeHttpResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(
            self.payload,
            ensure_ascii=False,
        ).encode("utf-8")


class TelegramDocumentTransportTests(unittest.TestCase):
    @staticmethod
    def artifact(
        path,
        *,
        filename="inventory.xlsx",
        mime_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        delete_after_send=True,
    ):
        return DocumentArtifact(
            path=Path(path),
            filename=filename,
            mime_type=mime_type,
            delete_after_send=delete_after_send,
        )

    def test_text_only_agent_response_uses_send_message(self):
        response = AgentResponse(
            text="Обычный ответ",
        )

        with patch.object(telegram_bot, "send_message") as send_message, patch.object(
            telegram_bot,
            "send_document",
        ) as send_document:
            telegram_bot.send_agent_response(
                123,
                response,
            )

        send_message.assert_called_once_with(
            123,
            "Обычный ответ",
        )
        send_document.assert_not_called()

    def test_one_document_sends_text_then_document(self):
        artifact = self.artifact(
            Path("unused.xlsx")
        )
        response = AgentResponse(
            text="Документ подготовлен.",
            documents=(artifact,),
        )
        events = []

        with patch.object(
            telegram_bot,
            "send_message",
            side_effect=lambda chat_id, text: events.append(
                ("text", chat_id, text)
            ),
        ) as send_message, patch.object(
            telegram_bot,
            "send_document",
            side_effect=lambda chat_id, document: events.append(
                ("document", chat_id, document)
            ),
        ) as send_document:
            telegram_bot.send_agent_response(
                456,
                response,
            )

        send_message.assert_called_once_with(
            456,
            "Документ подготовлен.",
        )
        send_document.assert_called_once_with(
            456,
            artifact,
        )
        self.assertEqual(
            events,
            [
                (
                    "text",
                    456,
                    "Документ подготовлен.",
                ),
                (
                    "document",
                    456,
                    artifact,
                ),
            ],
        )

    def test_multiple_documents_are_sent_in_order(self):
        first = self.artifact(
            Path("first.xlsx"),
            filename="first.xlsx",
        )
        second = self.artifact(
            Path("second.pdf"),
            filename="second.pdf",
            mime_type="application/pdf",
        )
        response = AgentResponse(
            text="Документы подготовлены.",
            documents=(
                first,
                second,
            ),
        )
        send_document = Mock()

        with patch.object(telegram_bot, "send_message"), patch.object(
            telegram_bot,
            "send_document",
            send_document,
        ):
            telegram_bot.send_agent_response(
                789,
                response,
            )

        self.assertEqual(
            send_document.call_args_list,
            [
                call(
                    789,
                    first,
                ),
                call(
                    789,
                    second,
                ),
            ],
        )

    def test_multipart_contains_fields_metadata_and_file_bytes(self):
        dummy_bytes = b"dummy xlsx bytes\x00\x01"

        with tempfile.TemporaryDirectory() as temp_root:
            path = (
                Path(temp_root)
                / "private-source.bin"
            )
            path.write_bytes(
                dummy_bytes
            )
            artifact = self.artifact(
                path,
                delete_after_send=False,
            )
            urlopen = Mock(
                return_value=FakeHttpResponse(
                    {
                        "ok": True,
                        "result": {
                            "message_id": 10,
                        },
                    }
                )
            )

            with patch.object(
                telegram_bot.urllib.request,
                "urlopen",
                urlopen,
            ):
                result = telegram_bot.send_document(
                    12345,
                    artifact,
                    caption="Тестовый документ",
                )

            request = urlopen.call_args.args[0]
            body = request.data
            content_type = request.get_header(
                "Content-type"
            )
            boundary = content_type.split(
                "boundary=",
                1,
            )[1]

            self.assertEqual(
                result,
                {
                    "message_id": 10,
                },
            )
            self.assertIn(
                b'name="chat_id"',
                body,
            )
            self.assertIn(
                b"\r\n12345\r\n",
                body,
            )
            self.assertIn(
                b'name="caption"',
                body,
            )
            self.assertIn(
                "Тестовый документ".encode("utf-8"),
                body,
            )
            self.assertIn(
                b'name="document"; filename="inventory.xlsx"',
                body,
            )
            self.assertIn(
                artifact.mime_type.encode("utf-8"),
                body,
            )
            self.assertIn(
                dummy_bytes,
                body,
            )
            self.assertIn(
                ("--" + boundary).encode("ascii"),
                body,
            )
            self.assertNotIn(
                str(path).encode("utf-8"),
                body,
            )
            self.assertNotIn(
                path.name.encode("utf-8"),
                body,
            )

    def test_success_deletes_file_and_empty_parent(self):
        with tempfile.TemporaryDirectory() as temp_root:
            parent = (
                Path(temp_root)
                / "artifact"
            )
            parent.mkdir()
            path = parent / "source.xlsx"
            path.write_bytes(b"xlsx")

            with patch.object(
                telegram_bot,
                "telegram_multipart_request",
                return_value={"message_id": 11},
            ):
                telegram_bot.send_document(
                    1,
                    self.artifact(path),
                )

            self.assertFalse(path.exists())
            self.assertFalse(parent.exists())

    def test_success_keeps_nonempty_parent(self):
        with tempfile.TemporaryDirectory() as temp_root:
            parent = Path(temp_root) / "artifact"
            parent.mkdir()
            path = parent / "source.xlsx"
            path.write_bytes(b"xlsx")
            sibling = parent / "keep.txt"
            sibling.write_text(
                "keep",
                encoding="utf-8",
            )

            with patch.object(
                telegram_bot,
                "telegram_multipart_request",
                return_value={"message_id": 13},
            ):
                telegram_bot.send_document(
                    1,
                    self.artifact(path),
                )

            self.assertFalse(path.exists())
            self.assertTrue(parent.is_dir())
            self.assertTrue(sibling.is_file())

    def test_success_preserves_file_when_delete_is_false(self):
        with tempfile.TemporaryDirectory() as temp_root:
            path = Path(temp_root) / "source.xlsx"
            path.write_bytes(b"xlsx")

            with patch.object(
                telegram_bot,
                "telegram_multipart_request",
                return_value={"message_id": 12},
            ):
                telegram_bot.send_document(
                    1,
                    self.artifact(
                        path,
                        delete_after_send=False,
                    ),
                )

            self.assertTrue(path.is_file())

    def test_transport_exception_preserves_file_and_parent(self):
        with tempfile.TemporaryDirectory() as temp_root:
            parent = Path(temp_root) / "artifact"
            parent.mkdir()
            path = parent / "source.xlsx"
            path.write_bytes(b"xlsx")

            with patch.object(
                telegram_bot,
                "telegram_multipart_request",
                side_effect=RuntimeError(
                    "synthetic Telegram error"
                ),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "synthetic Telegram error",
                ):
                    telegram_bot.send_document(
                        1,
                        self.artifact(path),
                    )

            self.assertTrue(path.is_file())
            self.assertTrue(parent.is_dir())

    def test_telegram_ok_false_preserves_file_and_parent(self):
        with tempfile.TemporaryDirectory() as temp_root:
            parent = Path(temp_root) / "artifact"
            parent.mkdir()
            path = parent / "source.xlsx"
            path.write_bytes(b"xlsx")

            with patch.object(
                telegram_bot.urllib.request,
                "urlopen",
                return_value=FakeHttpResponse(
                    {
                        "ok": False,
                        "description": "synthetic failure",
                    }
                ),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "Telegram API error",
                ):
                    telegram_bot.send_document(
                        1,
                        self.artifact(path),
                    )

            self.assertTrue(path.is_file())
            self.assertTrue(parent.is_dir())

    def test_missing_file_does_not_call_transport(self):
        with tempfile.TemporaryDirectory() as temp_root:
            path = Path(temp_root) / "missing.xlsx"
            transport = Mock()

            with patch.object(
                telegram_bot,
                "telegram_multipart_request",
                transport,
            ):
                with self.assertRaisesRegex(
                    FileNotFoundError,
                    "Файл документа не найден",
                ) as raised:
                    telegram_bot.send_document(
                        1,
                        self.artifact(path),
                    )

            transport.assert_not_called()
            self.assertNotIn(
                str(path),
                str(raised.exception),
            )

    def test_access_error_does_not_become_missing_file(self):
        with tempfile.TemporaryDirectory() as temp_root:
            path = Path(temp_root) / "restricted.xlsx"
            path.write_bytes(b"xlsx")
            transport = Mock()

            with patch.object(
                Path,
                "stat",
                side_effect=PermissionError(
                    "synthetic access denied"
                ),
            ), patch.object(
                telegram_bot,
                "telegram_multipart_request",
                transport,
            ):
                with self.assertRaisesRegex(
                    PermissionError,
                    "Нет доступа к файлу документа",
                ):
                    telegram_bot.send_document(
                        1,
                        self.artifact(path),
                    )

            transport.assert_not_called()
            self.assertTrue(path.is_file())

    def test_empty_file_does_not_call_transport(self):
        with tempfile.TemporaryDirectory() as temp_root:
            path = Path(temp_root) / "empty.xlsx"
            path.touch()
            transport = Mock()

            with patch.object(
                telegram_bot,
                "telegram_multipart_request",
                transport,
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "Файл документа пуст",
                ):
                    telegram_bot.send_document(
                        1,
                        self.artifact(path),
                    )

            transport.assert_not_called()
            self.assertTrue(path.is_file())

    def test_directory_and_invalid_metadata_do_not_call_transport(self):
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            path = root / "source.xlsx"
            path.write_bytes(b"xlsx")
            cases = [
                (
                    self.artifact(root),
                    "не является файлом",
                ),
                (
                    self.artifact(
                        path,
                        filename="",
                    ),
                    "Имя документа не указано",
                ),
                (
                    self.artifact(
                        path,
                        mime_type="",
                    ),
                    "MIME type документа не указан",
                ),
            ]

            for artifact, error_pattern in cases:
                with self.subTest(
                    error_pattern=error_pattern
                ):
                    transport = Mock()

                    with patch.object(
                        telegram_bot,
                        "telegram_multipart_request",
                        transport,
                    ):
                        with self.assertRaisesRegex(
                            ValueError,
                            error_pattern,
                        ):
                            telegram_bot.send_document(
                                1,
                                artifact,
                            )

                    transport.assert_not_called()

    def test_local_path_is_not_added_to_text_caption_or_filename(self):
        private_path = Path(
            r"C:\secret\private\inventory.xlsx"
        )
        private_artifact = self.artifact(
            private_path,
            filename="public-inventory.xlsx",
            delete_after_send=False,
        )
        response = AgentResponse(
            text="Документ подготовлен.",
            documents=(private_artifact,),
        )

        with patch.object(
            telegram_bot,
            "send_message",
        ) as send_message, patch.object(
            telegram_bot,
            "send_document",
        ) as send_document:
            telegram_bot.send_agent_response(
                1,
                response,
            )

        self.assertNotIn(
            str(private_path),
            send_message.call_args.args[1],
        )
        self.assertEqual(
            send_document.call_args,
            call(
                1,
                private_artifact,
            ),
        )
        self.assertNotIn(
            str(private_path),
            private_artifact.filename,
        )

        with tempfile.TemporaryDirectory() as temp_root:
            path = Path(temp_root) / "private-inventory.xlsx"
            path.write_bytes(b"xlsx")
            artifact = self.artifact(
                path,
                filename="public-inventory.xlsx",
                delete_after_send=False,
            )
            with patch.object(
                telegram_bot,
                "telegram_multipart_request",
            ) as transport:
                with self.assertRaisesRegex(
                    ValueError,
                    "не должна содержать локальный путь",
                ):
                    telegram_bot.send_document(
                        1,
                        artifact,
                        caption=(
                            "Файл: "
                            + str(path)
                        ),
                    )

            transport.assert_not_called()

    def test_dedicated_start_handler_does_not_call_agent(self):
        message = {
            "chat": {
                "id": 100,
            },
            "from": {
                "first_name": "Test",
            },
            "text": "/start",
        }

        with patch.object(
            telegram_bot,
            "answer_request",
        ) as answer_request, patch.object(
            telegram_bot,
            "send_message",
        ) as send_message:
            telegram_bot.handle_message(
                message
            )

        answer_request.assert_not_called()
        send_message.assert_called_once()

    def test_natural_language_uses_answer_request_and_chat_conversation(self):
        response = AgentResponse(
            text="Ответ агента.",
        )
        message = {
            "chat": {
                "id": 200,
            },
            "from": {
                "first_name": "Test",
            },
            "text": "Как идут продажи?",
        }

        with patch.object(
            telegram_bot,
            "answer_request",
            return_value=response,
        ) as answer_request, patch.object(
            telegram_bot,
            "send_chat_action",
        ), patch.object(
            telegram_bot,
            "send_agent_response",
        ) as send_agent_response:
            telegram_bot.handle_message(
                message
            )

        answer_request.assert_called_once_with(
            "Как идут продажи?",
            conversation_id="telegram:200",
        )
        send_agent_response.assert_called_once_with(
            200,
            response,
        )


if __name__ == "__main__":
    unittest.main()
