from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.knowledge.index import KnowledgeBase
from src.web.policy_gap_workflow import (
    create_policy_gap_report,
    policy_gap_fingerprint,
)


class WebPolicyGapWorkflowTests(unittest.TestCase):
    def test_fingerprint_changes_with_analysis_inputs(self) -> None:
        fingerprint = policy_gap_fingerprint(
            "Gouvernance des données",
            "Manque de coordination",
            ["Coordination"],
            False,
        )

        self.assertNotEqual(
            fingerprint,
            policy_gap_fingerprint(
                "Gouvernance des données",
                "Manque de coordination",
                ["Coordination"],
                True,
            ),
        )

    def test_report_searches_for_global_comparators_and_records_trace(self) -> None:
        source = {
            "record_id": "record-1",
            "section_id": "section-1",
            "citation": "Texte de référence",
            "text": "Passage pertinent.",
        }
        legal_agent = MagicMock()
        legal_agent.answer.return_value = {
            "answer": "Analyse documentaire à valider.",
            "answer_mode": "extractive_full_text_search",
            "sources": [source],
            "doctrine_sources": [],
            "retrieval_results": [
                {
                    "query": "Gouvernance des données",
                    "source_scope": "all",
                    "sources": [source],
                    "doctrine_sources": [],
                },
                {
                    "query": "Gouvernance des données international",
                    "source_scope": "global_policy",
                    "sources": [source],
                    "doctrine_sources": [],
                },
            ],
            "policy": {"decision": "human_review_required"},
        }
        with patch(
            "src.web.policy_gap_workflow.LegalPolicyAgent",
            return_value=legal_agent,
        ):
            report = create_policy_gap_report(
                MagicMock(spec=KnowledgeBase),
                "Gouvernance des données",
                "Les responsabilités sont-elles clairement définies ?",
                ["Responsabilités et mandats", "Coordination"],
            )

        call = legal_agent.answer.call_args
        self.assertEqual(
            call.args[0],
            "Gouvernance des données : Les responsabilités sont-elles clairement définies ?",
        )
        self.assertEqual(call.kwargs["retrieval_query"], "Gouvernance des données")
        self.assertIn(
            "international global policy frameworks standards",
            call.kwargs["additional_retrieval_queries"][0],
        )
        self.assertEqual(call.kwargs["source_scope"], "all")
        self.assertIn("OHADA-CEMAC", call.kwargs["analysis_context"])
        self.assertIn("sources internationales", call.kwargs["analysis_context"])
        self.assertEqual(call.kwargs["additional_source_scope"], "global_policy")
        self.assertIn(
            "Ne formule pas de recommandation propre à un pays.",
            call.kwargs["analysis_context"],
        )
        self.assertEqual(report["audit_trace"][1]["source_count"], 1)
        self.assertEqual(report["audit_trace"][2]["decision"], "human_review_required")
        self.assertEqual(
            [group["purpose"] for group in report["retrieval_groups"]],
            ["domain_context", "international_comparison_candidates"],
        )
        self.assertEqual(report["global_comparator_count"], 1)

    def test_rejects_missing_domain_issue_or_gap_categories(self) -> None:
        knowledge_base = MagicMock(spec=KnowledgeBase)
        with self.assertRaisesRegex(ValueError, "domaine"):
            create_policy_gap_report(knowledge_base, " ", "Problème", ["Coordination"])
        with self.assertRaisesRegex(ValueError, "problématique"):
            create_policy_gap_report(knowledge_base, "Domaine", " ", ["Coordination"])
        with self.assertRaisesRegex(ValueError, "catégorie"):
            create_policy_gap_report(knowledge_base, "Domaine", "Problème", [])


if __name__ == "__main__":
    unittest.main()
