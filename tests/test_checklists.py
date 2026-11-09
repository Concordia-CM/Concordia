from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.web.checklists import load_accounting_checklist


class AccountingChecklistTests(unittest.TestCase):
    def test_loads_complete_unvalidated_preparation_template(self) -> None:
        checklist = load_accounting_checklist()

        self.assertEqual(checklist.status, "draft_unvalidated")
        self.assertEqual(len(checklist.controls), 8)
        self.assertTrue(all(control.expected_evidence for control in checklist.controls))
        self.assertIn("non validé", checklist.disclaimer)
        self.assertIn("pas une source normative", checklist.source_note)

    def test_rejects_checklist_not_marked_as_unvalidated(self) -> None:
        source = load_accounting_checklist()
        payload = {
            "checklist_id": source.checklist_id,
            "title": source.title,
            "status": "validated",
            "jurisdiction": source.jurisdiction,
            "disclaimer": source.disclaimer,
            "source_note": source.source_note,
            "controls": [
                {
                    "id": control.control_id,
                    "category": control.category,
                    "question": control.question,
                    "expected_evidence": list(control.expected_evidence),
                }
                for control in source.controls
            ],
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "checklist.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "draft_unvalidated"):
                load_accounting_checklist(path)

    def test_rejects_duplicate_control_ids(self) -> None:
        source = load_accounting_checklist()
        payload = {
            "checklist_id": source.checklist_id,
            "title": source.title,
            "status": source.status,
            "jurisdiction": source.jurisdiction,
            "disclaimer": source.disclaimer,
            "source_note": source.source_note,
            "controls": [
                {
                    "id": "duplicate",
                    "category": control.category,
                    "question": control.question,
                    "expected_evidence": list(control.expected_evidence),
                }
                for control in source.controls[:2]
            ],
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "checklist.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "dupliqué"):
                load_accounting_checklist(path)


if __name__ == "__main__":
    unittest.main()
