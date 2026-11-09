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
            route_request("question", intent="institutional_analysis")
        with self.assertRaisesRegex(RoutingInputError, "ne peut pas être vide"):
            route_request("  ", intent="legal_search")

    @patch("src.app.KnowledgeBase")
    @patch("src.app.LegalPolicyAgent")
    def test_cli_executes_a_clear_legal_route(
        self,
        legal_agent_class: MagicMock,
        knowledge_base_class: MagicMock,
    ) -> None:
        legal_agent_class.return_value.answer.return_value = {"answer": "Réponse sourcée"}
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
