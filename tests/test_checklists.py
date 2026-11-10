from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.web.checklists import load_accounting_checklist


class AccountingChecklistTests(unittest.TestCase):
    @staticmethod
    def _control_payload(control: object, control_id: str | None = None) -> dict[str, object]:
        return {
            "id": control_id or control.control_id,
            "category": control.category,
            "question": control.question,
            "expected_evidence": list(control.expected_evidence),
            "validation_status": "indicative",
            "basis": "Thème de préparation sans référence juridique validée.",
            "legal_sources": [],
        }

    @staticmethod
    def _template_payload(source: object, status: str | None = None) -> dict[str, object]:
        return {
            "checklist_id": source.checklist_id,
            "title": source.title,
            "status": status or source.status,
            "jurisdiction": source.jurisdiction,
            "disclaimer": source.disclaimer,
            "source_note": source.source_note,
            "validation_policy": source.validation_policy,
        }

    def test_loads_complete_unvalidated_preparation_template(self) -> None:
        checklist = load_accounting_checklist()

        self.assertEqual(checklist.status, "draft_unvalidated")
        self.assertEqual(len(checklist.controls), 8)
        self.assertTrue(all(control.expected_evidence for control in checklist.controls))
        self.assertTrue(
            all(control.validation_status == "indicative" for control in checklist.controls)
        )
        self.assertTrue(all(not control.legal_sources for control in checklist.controls))
        self.assertIn("non validé", checklist.disclaimer)
        self.assertIn("pas une source normative", checklist.source_note)

    def test_rejects_checklist_not_marked_as_unvalidated(self) -> None:
        source = load_accounting_checklist()
        payload = self._template_payload(source, status="validated")
        payload["controls"] = [
            self._control_payload(control) for control in source.controls
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "checklist.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "draft_unvalidated"):
                load_accounting_checklist(path)

    def test_rejects_duplicate_control_ids(self) -> None:
        source = load_accounting_checklist()
        payload = self._template_payload(source)
        payload["controls"] = [
            self._control_payload(control, control_id="duplicate")
            for control in source.controls[:2]
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "checklist.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "dupliqué"):
                load_accounting_checklist(path)

    def test_rejects_expert_validated_control_without_review_and_official_sources(self) -> None:
        source = load_accounting_checklist()
        payload = self._template_payload(source, status="expert_validated")
        control = self._control_payload(source.controls[0])
        control["validation_status"] = "expert_validated"
        payload["controls"] = [control]

        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "checklist.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "réviseur, une date et des sources"):
                load_accounting_checklist(path)

    def test_accepts_a_control_only_with_recorded_source_verification_metadata(self) -> None:
        source = load_accounting_checklist()
        payload = self._template_payload(source, status="expert_validated")
        control = self._control_payload(source.controls[0])
        control.update(
            validation_status="expert_validated",
            reviewed_by="Réviseur désigné",
            reviewed_at="2026-11-09",
            legal_sources=[
                {
                    "authority": "Autorité identifiée lors de la revue",
                    "citation": "Article 1",
                    "jurisdiction": "Cameroun",
                    "source_uri": "https://example.org/legal-text",
                    "record_id": "law-1",
                    "section_id": "article-1",
                    "source_file": "law.pdf",
                    "source_sha256": "0" * 64,
                    "version": "2026",
                    "version_status": "in_force",
                    "verification_status": "official_source_verified",
                    "verified_by": "Réviseur désigné",
                    "verified_at": "2026-11-09",
                }
            ],
        )
        payload["controls"] = [control]

        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "checklist.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            checklist = load_accounting_checklist(path)

        self.assertEqual(checklist.status, "expert_validated")
        self.assertEqual(checklist.controls[0].validation_status, "expert_validated")
        self.assertEqual(checklist.controls[0].legal_sources[0].record_id, "law-1")
        report_metadata = checklist.report_metadata([checklist.controls[0].control_id])
        applied_control = report_metadata["controls_applied"][0]
        self.assertEqual(applied_control["reviewed_by"], "Réviseur désigné")
        self.assertEqual(
            applied_control["legal_sources"][0]["verification_status"],
            "official_source_verified",
        )
        self.assertEqual(
            checklist.report_metadata([])["controls_applied"],
            [],
        )

    def test_rejects_source_without_explicit_officiality_verification(self) -> None:
        source = load_accounting_checklist()
        payload = self._template_payload(source, status="expert_validated")
        control = self._control_payload(source.controls[0])
        control.update(
            validation_status="expert_validated",
            reviewed_by="Réviseur désigné",
            reviewed_at="2026-11-09",
            legal_sources=[
                {
                    "authority": "Autorité identifiée lors de la revue",
                    "citation": "Article 1",
                    "jurisdiction": "Cameroun",
                    "source_uri": "https://example.org/legal-text",
                    "record_id": "law-1",
                    "section_id": "article-1",
                    "source_file": "law.pdf",
                    "source_sha256": "0" * 64,
                    "version": "2026",
                    "version_status": "in_force",
                    "verification_status": "not_checked",
                    "verified_by": "Réviseur désigné",
                    "verified_at": "2026-11-09",
                }
            ],
        )
        payload["controls"] = [control]

        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "checklist.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "caractère officiel"):
                load_accounting_checklist(path)


if __name__ == "__main__":
    unittest.main()
