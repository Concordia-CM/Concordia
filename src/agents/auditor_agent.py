"""Évalue les pièces d'un scénario sans conclure automatiquement à la conformité."""

from __future__ import annotations

from typing import Any

from src.agents.legal_policy_agent import LegalPolicyAgent
from src.knowledge.index import normalize_for_comparison


class AuditorAgent:
    """Compare les pièces déclarées au périmètre du scénario et cite les règles trouvées."""

    def __init__(self, legal_agent: LegalPolicyAgent) -> None:
        self.legal_agent = legal_agent

    def assess_check(
        self,
        check: dict[str, Any],
        facts: list[str],
        documents_received: list[str],
        document_contents: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(check, dict):
            raise ValueError("Chaque contrôle doit être un objet.")
        self._validate_text_list(facts, "facts")
        self._validate_text_list(documents_received, "documents_received")
        if document_contents is not None and (
            not isinstance(document_contents, dict)
            or not all(
                isinstance(name, str)
                and name.strip()
                and isinstance(content, str)
                for name, content in document_contents.items()
            )
        ):
            raise ValueError("document_contents doit associer des noms à des textes.")
        question = str(check.get("question") or check.get("description") or "").strip()
        if not question:
            raise ValueError("Chaque contrôle doit contenir une question ou une description.")

        expected = check.get("expected_evidence", [])
        if not isinstance(expected, list) or not all(isinstance(item, str) for item in expected):
            raise ValueError("expected_evidence doit être une liste de chaînes.")
        if any(not item.strip() for item in expected):
            raise ValueError("expected_evidence ne peut pas contenir de valeurs vides.")
        received_normalized = [
            normalize_for_comparison(item) for item in documents_received
        ]
        searchable_content = [
            normalize_for_comparison(content)
            for content in (document_contents or {}).values()
        ]
        evidence_found = [
            item
            for item in expected
            if any(
                normalize_for_comparison(item) in received
                for received in received_normalized
            )
            or any(
                normalize_for_comparison(item) in content
                for content in searchable_content
            )
        ]
        missing_evidence = [
            item
            for item in expected
            if item not in evidence_found
        ]

        result = self.legal_agent.answer(question)
        sources = result["sources"]
        policy = result.get("policy")
        uncertainties = []
        if not sources:
            uncertainties.append(
                "Aucun passage correspondant trouvé ; vérifier la couverture de la base "
                "et les textes applicables."
            )
        else:
            uncertainties.append(
                "La pertinence, la version en vigueur et l'applicabilité des passages "
                "doivent être vérifiées par une personne qualifiée."
            )
        if missing_evidence:
            uncertainties.append(
                "Les pièces absentes sont définies par le scénario ; leur absence ne "
                "constitue pas, à elle seule, une preuve de non-conformité."
            )
        if isinstance(policy, dict) and policy.get("decision") == "blocked":
            uncertainties.append(
                "La politique a bloqué la transmission de la réponse ; vérifier les "
                "références avant toute utilisation."
            )

        recommendations = [
            "Faire valider les faits et les références par un responsable juridique ou conformité."
        ]
        if missing_evidence:
            recommendations.insert(
                0,
                "Demander ou vérifier les pièces attendues manquantes : "
                + ", ".join(missing_evidence)
                + ".",
            )
        elif not sources:
            recommendations.insert(
                0,
                "Compléter le corpus ou reformuler la recherche avant toute conclusion.",
            )

        assessment = {
            "check_id": str(check.get("check_id") or check.get("id") or ""),
            "question": question,
            "facts_reported": facts,
            "documents_received": documents_received,
            "expected_evidence": expected,
            "evidence_found_in_documents": evidence_found,
            "missing_scenario_evidence": missing_evidence,
            "finding": (
                "documentation_gap_to_review"
                if missing_evidence
                else "human_review_required"
            ),
            "sources": sources,
            "uncertainties": uncertainties,
            "recommendations": recommendations,
        }
        if isinstance(policy, dict):
            assessment["policy"] = policy
        return assessment

    @staticmethod
    def _validate_text_list(value: list[str], field: str) -> None:
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise ValueError(f"{field} doit être une liste de textes non vides.")