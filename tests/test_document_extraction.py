from __future__ import annotations

import unittest
from io import BytesIO
from importlib.util import find_spec

import fitz

from src.agents.auditor_agent import AuditorAgent
from src.agents.legal_policy_agent import LegalPolicyAgent
from src.web.document_extraction import extract_document


class DocumentExtractionTests(unittest.TestCase):
    def test_extracts_text_pdf_in_memory(self) -> None:
        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_text((72, 72), "Statuts de la société Concordia.")
        content = pdf.tobytes()
        pdf.close()

        result = extract_document("statuts.pdf", content)

        self.assertIn("Statuts de la société Concordia.", result.text)
        self.assertEqual(result.page_count, 1)
        self.assertEqual(result.ocr_pages, ())

    @unittest.skipUnless(find_spec("docx"), "python-docx n'est pas installé")
    def test_extracts_docx_paragraphs_and_table_cells(self) -> None:
        from docx import Document

        document = Document()
        document.add_paragraph("Statuts de la société Concordia.")
        table = document.add_table(rows=1, cols=2)
        table.cell(0, 0).text = "Registre"
        table.cell(0, 1).text = "Commerce"
        stream = BytesIO()
        document.save(stream)

        result = extract_document("statuts.docx", stream.getvalue())

        self.assertIn("Statuts de la société Concordia.", result.text)
        self.assertIn("Registre | Commerce", result.text)
        self.assertEqual(result.page_count, 0)

    def test_rejects_empty_unsupported_and_invalid_files(self) -> None:
        with self.assertRaisesRegex(ValueError, "vide ou invalide"):
            extract_document("statuts.pdf", b"")
        with self.assertRaisesRegex(ValueError, "Format non pris en charge"):
            extract_document("statuts.doc", b"content")
        with self.assertRaisesRegex(ValueError, "illisible ou invalide"):
            extract_document("statuts.pdf", b"not a pdf")

    def test_auditor_checks_expected_evidence_in_extracted_text(self) -> None:
        class FakeLegalAgent(LegalPolicyAgent):
            def __init__(self) -> None:
                pass

            def answer(self, question: str, **kwargs: object) -> dict[str, object]:
                del kwargs
                return {"question": question, "sources": []}

        result = AuditorAgent(FakeLegalAgent()).assess_check(
            {
                "question": "Les statuts sont-ils présents ?",
                "expected_evidence": ["Capital social"],
            },
            facts=[],
            documents_received=["statuts.pdf"],
            document_contents={"statuts.pdf": "Les statuts mentionnent le capital social."},
        )

        self.assertEqual(result["evidence_found_in_documents"], ["Capital social"])
        self.assertEqual(result["missing_scenario_evidence"], [])
        self.assertEqual(result["finding"], "human_review_required")

    def test_auditor_passes_context_to_llm_for_audit_analysis(self) -> None:
        class FakeLegalAgent(LegalPolicyAgent):
            def __init__(self) -> None:
                self.kwargs: dict[str, object] = {}

            def answer(self, question: str, **kwargs: object) -> dict[str, object]:
                self.kwargs = kwargs
                return {
                    "question": question,
                    "sources": [],
                    "answer": "Analyse à valider.",
                    "answer_mode": "ollama_rag",
                }

        legal_agent = FakeLegalAgent()
        result = AuditorAgent(legal_agent).assess_check(
            {
                "question": "Le registre est-il à jour ?",
                "expected_evidence": ["Registre des décisions"],
            },
            facts=["Dernière mise à jour en juin."],
            documents_received=["registre.pdf"],
            use_llm=True,
        )

        self.assertIs(legal_agent.kwargs["use_llm"], True)
        self.assertIn("Dernière mise à jour en juin.", str(legal_agent.kwargs["analysis_context"]))
        self.assertEqual(result["analysis"], "Analyse à valider.")


if __name__ == "__main__":
    unittest.main()
