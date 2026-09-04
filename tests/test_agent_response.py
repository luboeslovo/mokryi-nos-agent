import sys
import unittest
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from agent_response import AgentResponse, DocumentArtifact


class AgentResponseContractTests(unittest.TestCase):
    def test_document_artifact_preserves_transport_metadata(self):
        path = Path(r"C:\secret\private\report.xlsx")

        artifact = DocumentArtifact(
            path=path,
            filename="report.xlsx",
            mime_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )

        self.assertIsInstance(artifact.path, Path)
        self.assertEqual(artifact.path, path)
        self.assertEqual(artifact.filename, "report.xlsx")
        self.assertEqual(
            artifact.mime_type,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertTrue(artifact.delete_after_send)

    def test_agent_response_preserves_text_and_document_tuple(self):
        artifact = DocumentArtifact(
            path=Path(r"C:\secret\private\report.pdf"),
            filename="report.pdf",
            mime_type="application/pdf",
            delete_after_send=False,
        )

        response = AgentResponse(
            text="Документ подготовлен.",
            documents=(artifact,),
        )

        self.assertEqual(response.text, "Документ подготовлен.")
        self.assertIsInstance(response.documents, tuple)
        self.assertEqual(response.documents, (artifact,))
        self.assertFalse(response.documents[0].delete_after_send)

    def test_agent_response_defaults_to_no_documents(self):
        response = AgentResponse(text="Обычный ответ.")

        self.assertEqual(response.documents, ())


if __name__ == "__main__":
    unittest.main()
