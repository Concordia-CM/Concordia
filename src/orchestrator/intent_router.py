"""Routage déterministe des demandes vers les parcours actuellement disponibles."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

Intent: TypeAlias = Literal["legal_search", "document_audit"]

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
SUPPORTED_INTENTS = ("legal_search", "document_audit")


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


RoutedRequest: TypeAlias = LegalSearchRequest | DocumentAuditRequest


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

    if legal_search and document_audit:
        raise AmbiguousIntentError(
            "La demande peut relever de la recherche juridique comme de l'audit. "
            "Précisez --intent legal_search ou --intent document_audit."
        )
    if legal_search:
        return "legal_search"
    if document_audit:
        return "document_audit"
    raise UnsupportedIntentError(
        "Aucun parcours disponible ne correspond clairement à la demande. "
        "Précisez --intent legal_search ou --intent document_audit."
    )


def route_request(
    request: str,
    *,
    intent: str | None = None,
    scenario_path: str | Path | None = None,
) -> RoutedRequest:
    """Valide et route une recherche juridique ou un audit documentaire."""
    if not isinstance(request, str) or not request.strip():
        raise RoutingInputError("La demande ne peut pas être vide.")

    selected_intent = _infer_intent(request) if intent is None else intent
    if selected_intent not in SUPPORTED_INTENTS:
        supported = ", ".join(SUPPORTED_INTENTS)
        raise RoutingInputError(
            f"Intention inconnue {selected_intent!r}. Intentions disponibles : {supported}."
        )

    if selected_intent == "legal_search":
        if scenario_path is not None:
            raise RoutingInputError(
                "Un scénario ne peut pas être fourni pour une recherche juridique."
            )
        return LegalSearchRequest(intent="legal_search", question=request.strip())

    if scenario_path is None:
        raise RoutingInputError(
            "Le parcours d'audit nécessite un fichier de scénario (--scenario)."
        )
    scenario_value = str(scenario_path)
    if not scenario_value.strip():
        raise RoutingInputError("Le chemin du scénario ne peut pas être vide.")
    path = Path(scenario_value)
    return DocumentAuditRequest(
        intent="document_audit",
        request=request.strip(),
        scenario_path=path,
    )