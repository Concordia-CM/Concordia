"""Routage déterministe des demandes vers les parcours actuellement disponibles."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

Intent: TypeAlias = Literal["legal_search", "document_audit", "institutional_analysis"]

LEGAL_SEARCH_MARKERS = frozenset(
    {
        "article",
        "articles",
        "acte",
        "disposition",
        "dispositions",
        "jurisprudence",
        "loi",
        "lois",
        "recherche",
        "rechercher",
        "cherche",
        "trouve",
        "retrouve",
        "texte",
        "textes",
    }
)
DOCUMENT_AUDIT_MARKERS = frozenset(
    {
        "audit",
        "auditer",
        "audite",
        "conformite",
        "conforme",
        "controle",
        "dossier",
        "evaluer",
        "piece",
        "pieces",
        "risque",
        "risques",
        "scenario",
        "verifier",
    }
)
INSTITUTIONAL_ANALYSIS_MARKERS = frozenset(
    {
        "institutionnel",
        "institutionnelle",
        "institutionnels",
        "institutionnelles",
        "mandat",
        "regulateur",
        "regulatrice",
        "supervision",
    }
)
SUPPORTED_INTENTS = ("legal_search", "document_audit", "institutional_analysis")


class AmbiguousIntentError(ValueError):
    """La demande correspond à plusieurs parcours disponibles."""


class UnsupportedIntentError(ValueError):
    """La demande ne correspond à aucun parcours disponible."""


class RoutingInputError(ValueError):
    """Les entrées nécessaires au parcours choisi sont absentes ou invalides."""


@dataclass(frozen=True)
class LegalSearchRequest:
    intent: Literal["legal_search"]
    question: str


@dataclass(frozen=True)
class DocumentAuditRequest:
    intent: Literal["document_audit"]
    request: str
    scenario_path: Path


@dataclass(frozen=True)
class InstitutionalAnalysisRequest:
    intent: Literal["institutional_analysis"]
    question: str
    institution: str
    mandate: str
    jurisdiction: str | None = None


RoutedRequest: TypeAlias = (
    LegalSearchRequest | DocumentAuditRequest | InstitutionalAnalysisRequest
)


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    without_accents = "".join(
        character for character in decomposed if unicodedata.category(character) != "Mn"
    )
    return re.sub(r"[^\w]+", " ", without_accents, flags=re.UNICODE)


def _infer_intent(request: str) -> Intent:
    tokens = set(_normalize(request).split())
    legal_search = bool(tokens & LEGAL_SEARCH_MARKERS)
    document_audit = bool(tokens & DOCUMENT_AUDIT_MARKERS)
    institutional_analysis = bool(tokens & INSTITUTIONAL_ANALYSIS_MARKERS)

    matched_intents = sum((legal_search, document_audit, institutional_analysis))
    if matched_intents > 1:
        raise AmbiguousIntentError(
            "La demande peut relever de plusieurs parcours. "
            "Précisez --intent legal_search, --intent document_audit ou "
            "--intent institutional_analysis."
        )
    if institutional_analysis:
        return "institutional_analysis"
    if legal_search:
        return "legal_search"
    if document_audit:
        return "document_audit"
    raise UnsupportedIntentError(
        "Aucun parcours disponible ne correspond clairement à la demande. "
        "Précisez --intent legal_search, --intent document_audit ou "
        "--intent institutional_analysis."
    )


def route_request(
    request: str,
    *,
    intent: str | None = None,
    scenario_path: str | Path | None = None,
    institution: str | None = None,
    mandate: str | None = None,
    jurisdiction: str | None = None,
) -> RoutedRequest:
    """Valide et route une recherche, un audit ou une analyse institutionnelle."""
    if not isinstance(request, str) or not request.strip():
        raise RoutingInputError("La demande ne peut pas être vide.")

    selected_intent = _infer_intent(request) if intent is None else intent
    if selected_intent not in SUPPORTED_INTENTS:
        supported = ", ".join(SUPPORTED_INTENTS)
        raise RoutingInputError(
            f"Intention inconnue {selected_intent!r}. Intentions disponibles : {supported}."
        )

    if selected_intent == "legal_search":
        if any(value is not None for value in (scenario_path, institution, mandate, jurisdiction)):
            raise RoutingInputError(
                "Les paramètres d'audit ou institutionnels ne sont pas valides "
                "pour une recherche juridique."
            )
        return LegalSearchRequest(intent="legal_search", question=request.strip())

    if selected_intent == "document_audit":
        if any(value is not None for value in (institution, mandate, jurisdiction)):
            raise RoutingInputError(
                "Les paramètres institutionnels ne sont pas valides pour un audit."
            )
        if scenario_path is None:
            raise RoutingInputError(
                "Le parcours d'audit nécessite un fichier de scénario (--scenario)."
            )
        scenario_value = str(scenario_path)
        if not scenario_value.strip():
            raise RoutingInputError("Le chemin du scénario ne peut pas être vide.")
        return DocumentAuditRequest(
            intent="document_audit",
            request=request.strip(),
            scenario_path=Path(scenario_value),
        )

    if scenario_path is not None:
        raise RoutingInputError(
            "Un fichier scénario ne peut pas être fourni pour une analyse institutionnelle."
        )
    if institution is None or not institution.strip():
        raise RoutingInputError(
            "L'analyse institutionnelle nécessite --institution avec le nom du rôle visé."
        )
    if mandate is None or not mandate.strip():
        raise RoutingInputError(
            "L'analyse institutionnelle nécessite --mandate avec un mandat explicite."
        )
    if jurisdiction is not None and not jurisdiction.strip():
        raise RoutingInputError("--jurisdiction doit être omise ou non vide.")
    return InstitutionalAnalysisRequest(
        intent="institutional_analysis",
        question=request.strip(),
        institution=institution.strip(),
        mandate=mandate.strip(),
        jurisdiction=jurisdiction.strip() if jurisdiction else None,
    )