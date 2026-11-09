from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from src.agents.auditor_agent import AuditorAgent
from src.agents.legal_policy_agent import LegalPolicyAgent
from src.knowledge.index import KnowledgeBase
from src.orchestrator.coordinator import run_scenario


class AuditFlowTests(unittest.TestCase):
    def test_expected_evidence_must_be_present_in_one_received_document(self) -> None:
        class NoSourceAgent(LegalPolicyAgent):
            def __init__(self) -> None:
                pass

            def answer(self, question: str) -> dict[str, Any]:
                return {"question": question, "sources": []}

        result = AuditorAgent(NoSourceAgent()).assess_check(
            {
                "id": "rccm",
                "question": "immatriculation registre commerce",
                "expected_evidence": ["Extrait RCCM"],
            },
            facts=[],
            documents_received=["Extrait", "RCCM"],
        )

        self.assertEqual(result["finding"], "documentation_gap_to_review")
        self.assertEqual(result["missing_scenario_evidence"], ["Extrait RCCM"])

    def test_events_are_assessed_sequentially_and_logged_with_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            processed_dir = root / "processed"
            processed_dir.mkdir()
            record = {
                "record_id": "ohada-company-law",
                "document_title": "Acte uniforme de démonstration",
                "source_file": "acte-uniforme.pdf",
                "domain": "OHADA",
                "entity_type": "Legal_Document",
                "metadata": {},
                "sections": [
                    {
                        "section_id": "article-12",
                        "entity_type": "Article",
                        "title": "Article 12",
                        "article_number": "12",
                        "content": "La société est immatriculée au registre du commerce.",
                        "metadata": {"source_page_start": 4, "source_page_end": 4},
                    }
                ],
            }
            (processed_dir / "law.json").write_text(
                json.dumps(record, ensure_ascii=False),
                encoding="utf-8",
            )
            knowledge_base = KnowledgeBase(root / "index.sqlite3")
            knowledge_base.build(
                processed_dir=processed_dir,
                ccja_documents=root / "missing-decisions.jsonl",
                ccja_chunks=root / "missing-chunks.jsonl",
            )
            scenario_path = root / "scenario.json"
            scenario_path.write_text(
                json.dumps(
                    {
                        "scenario_id": "sequential-test",
                        "title": "Scénario de test",
                        "jurisdiction": "OHADA",
                        "events": [
                            {
                                "event_id": "first",
                                "title": "Dossier initial",
                                "facts": ["Dossier reçu."],
                                "documents_received": [],
                                "checks": [
                                    {
                                        "id": "rccm",
                                        "question": "immatriculation société registre commerce",
                                        "expected_evidence": ["Extrait RCCM"],
                                    }
                                ],
                            },
                            {
                                "event_id": "second",
                                "title": "Pièce reçue",
                                "facts": ["Une pièce est ajoutée."],
                                "documents_received": ["Extrait RCCM à jour"],
                                "checks": [
                                    {
                                        "id": "rccm",
                                        "question": "immatriculation société registre commerce",
                                        "expected_evidence": ["Extrait RCCM"],
                                    }
                                ],
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            report = run_scenario(scenario_path, knowledge_base, root / "audits")

            first_check = report["events"][0]["checks"][0]
            second_check = report["events"][1]["checks"][0]
            self.assertEqual(first_check["finding"], "documentation_gap_to_review")
            self.assertEqual(first_check["missing_scenario_evidence"], ["Extrait RCCM"])
            self.assertEqual(second_check["finding"], "human_review_required")
            self.assertEqual(second_check["missing_scenario_evidence"], [])
            self.assertTrue(second_check["sources"][0]["citation"].endswith("p. 4 — acte-uniforme.pdf"))
            self.assertEqual(report["assessment"], "human_review_required")

            log_records = [
                json.loads(line)
                for line in Path(report["audit_log_path"]).read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(
                [record["record_type"] for record in log_records],
                ["audit_started", "event_assessed", "event_assessed", "audit_completed"],
            )
            self.assertEqual(log_records[1]["checks"][0]["sources"][0]["section_id"], "article-12")
            self.assertTrue(log_records[1]["assessed_at"])


if __name__ == "__main__":
    unittest.main()
