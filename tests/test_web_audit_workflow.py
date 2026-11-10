from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.knowledge.index import KnowledgeBase
from src.web.audit_workflow import audit_fingerprint, create_audit_report
from src.web.document_extraction import ExtractedDocument


class WebAuditWorkflowTests(unittest.TestCase):
    def test_fingerprint_changes_when_generation_setting_changes(self) -> None:
        documents = [ExtractedDocument("statuts.pdf", "Capital social", 1)]
        inputs = (documents, ["Le capital est-il indiqué ?"], ["Capital social"], "")

        extractive_fingerprint = audit_fingerprint(*inputs, use_llm=False)
        generated_fingerprint = audit_fingerprint(*inputs, use_llm=True)

        self.assertNotEqual(extractive_fingerprint, generated_fingerprint)

    def test_report_discloses_ollama_data_and_disambiguates_duplicate_names(self) -> None:
        class FakeAuditor:
            def __init__(self) -> None:
                self.calls: list[tuple[dict[str, object], dict[str, object]]] = []

            def assess_check(
                self, check: dict[str, object], **kwargs: object
            ) -> dict[str, object]:
                self.calls.append((check, kwargs))
                return {"question": check["question"], "sources": []}

        auditor = FakeAuditor()
        documents = [
            ExtractedDocument("statuts.pdf", "Capital social", 1),
            ExtractedDocument("statuts.pdf", "Autre version", 2),
        ]
        with (
            patch("src.web.audit_workflow.LegalPolicyAgent"),
            patch("src.web.audit_workflow.AuditorAgent", return_value=auditor),
        ):
            report = create_audit_report(
                MagicMock(spec=KnowledgeBase),
                documents,
                ["Le capital est-il indiqué ?"],
                [["Capital social"]],
                ["Capital déclaré à 10 000 000 FCFA."],
                use_llm=True,
            )

        self.assertEqual(
            [document["name"] for document in report["documents"]],
            ["statuts.pdf", "statuts.pdf (2)"],
        )
        self.assertIn("serveur configuré", report["limitations"][1])
        self.assertIn("texte intégral", report["limitations"][1])
        self.assertEqual(report["audit_trace"][0]["step"], "documents_extracted")
        self.assertEqual(
            report["audit_trace"][1]["checks"][0]["question"],
            "Le capital est-il indiqué ?",
        )
        self.assertEqual(auditor.calls[0][1]["documents_received"], [
            "statuts.pdf",
            "statuts.pdf (2)",
        ])
        self.assertIs(auditor.calls[0][1]["use_llm"], True)


if __name__ == "__main__":
    unittest.main()
