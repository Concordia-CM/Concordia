from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.app import main
from src.orchestrator.intent_router import (
    AmbiguousIntentError,
    DocumentAuditRequest,
    InstitutionalAnalysisRequest,
    LegalSearchRequest,
    RoutingInputError,
    UnsupportedIntentError,
    route_request,
)


class IntentRouterTests(unittest.TestCase):
    def test_routes_clear_legal_search(self) -> None:
        result = route_request("Quels articles parlent de l'immatriculation ?")

        self.assertEqual(result, LegalSearchRequest(
            intent="legal_search",
            question="Quels articles parlent de l'immatriculation ?",
        ))

    def test_routes_audit_when_scenario_is_provided(self) -> None:
        scenario_path = Path("data/scenarios/example.json")

        result = route_request(
            "Lancer un audit de conformité",
            scenario_path=scenario_path,
        )

        self.assertEqual(
            result,
            DocumentAuditRequest(
                intent="document_audit",
                request="Lancer un audit de conformité",
                scenario_path=scenario_path,
            ),
        )

    def test_explicit_intent_resolves_a_lexically_ambiguous_request(self) -> None:
        result = route_request(
            "Auditer ce dossier et rechercher les articles applicables",
            intent="legal_search",
        )

        self.assertIsInstance(result, LegalSearchRequest)

    def test_rejects_ambiguous_request(self) -> None:
        with self.assertRaises(AmbiguousIntentError):
            route_request("Auditer ce dossier et rechercher les articles applicables")

    def test_rejects_unsupported_request(self) -> None:
        with self.assertRaises(UnsupportedIntentError):
            route_request("Bonjour, comment allez-vous ?")

    def test_requires_scenario_for_audit(self) -> None:
        with self.assertRaisesRegex(RoutingInputError, "nécessite un fichier de scénario"):
            route_request("Audit de conformité")

    def test_rejects_unknown_intent_and_empty_request(self) -> None:
        with self.assertRaisesRegex(RoutingInputError, "Intention inconnue"):
            route_request("question", intent="unknown")
        with self.assertRaisesRegex(RoutingInputError, "ne peut pas être vide"):
            route_request("  ", intent="legal_search")

    def test_routes_institutional_analysis_with_explicit_scope(self) -> None:
        result = route_request(
            "Examiner les obligations de déclaration",
            intent="institutional_analysis",
            institution="Autorité de supervision",
            mandate="Examiner les obligations de déclaration.",
            jurisdiction="Cameroun",
        )

        self.assertEqual(
            result,
            InstitutionalAnalysisRequest(
                intent="institutional_analysis",
                question="Examiner les obligations de déclaration",
                institution="Autorité de supervision",
                mandate="Examiner les obligations de déclaration.",
                jurisdiction="Cameroun",
            ),
        )

    def test_institutional_route_requires_institution_and_mandate(self) -> None:
        with self.assertRaisesRegex(RoutingInputError, "--institution"):
            route_request(
                "Examiner les obligations",
                intent="institutional_analysis",
                mandate="Contrôler les obligations.",
            )
        with self.assertRaisesRegex(RoutingInputError, "--mandate"):
            route_request(
                "Examiner les obligations",
                intent="institutional_analysis",
                institution="Autorité",
            )

    @patch("src.app.KnowledgeBase")
    @patch("src.app.InstitutionalAgent")
    def test_cli_executes_institutional_route_with_explicit_configuration(
        self,
        institutional_agent_class: MagicMock,
        knowledge_base_class: MagicMock,
    ) -> None:
        institutional_agent_class.return_value.analyze.return_value = {
            "agent_result": {"summary": "Analyse institutionnelle sourcée"},
            "policy": {"decision": "human_review_required"},
        }
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(
                [
                    "route",
                    "Examiner les obligations de déclaration",
                    "--intent",
                    "institutional_analysis",
                    "--institution",
                    "Autorité de supervision",
                    "--mandate",
                    "Examiner les obligations de déclaration.",
                    "--jurisdiction",
                    "Cameroun",
                    "--db",
                    "unused",
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("Analyse institutionnelle sourcée", output.getvalue())
        self.assertIn("human_review_required", output.getvalue())
        institutional_agent_class.return_value.analyze.assert_called_once_with(
            "Examiner les obligations de déclaration",
            institution="Autorité de supervision",
            mandate="Examiner les obligations de déclaration.",
            jurisdiction="Cameroun",
            retrieval_mode="fts",
            use_llm=False,
            source_scope="legal_texts",
        )
        knowledge_base_class.assert_called_once()

    @patch("src.app.KnowledgeBase")
    @patch("src.app.LegalPolicyAgent")
    def test_cli_executes_a_clear_legal_route(
        self,
        legal_agent_class: MagicMock,
        knowledge_base_class: MagicMock,
    ) -> None:
        legal_agent_class.return_value.answer.return_value = {
            "answer": "Réponse sourcée",
            "policy": {"decision": "human_review_required"},
        }
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main(["route", "Quels articles parlent du RCCM ?", "--db", "unused"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Réponse sourcée", output.getvalue())
        knowledge_base_class.assert_called_once()

    @patch("src.app.KnowledgeBase")
    def test_cli_rejects_ambiguous_route_before_opening_the_database(
        self,
        knowledge_base_class: MagicMock,
    ) -> None:
        error_output = io.StringIO()

        with redirect_stderr(error_output):
            exit_code = main(
                [
                    "route",
                    "Auditer ce dossier et rechercher les articles applicables",
                    "--db",
                    "unused",
                ]
            )

        self.assertEqual(exit_code, 2)
        self.assertIn("demande peut relever", error_output.getvalue())
        knowledge_base_class.assert_not_called()


if __name__ == "__main__":
    unittest.main()
