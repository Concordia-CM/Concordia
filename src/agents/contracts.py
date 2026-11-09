"""Contrats typés communs pour les entrées et sorties des agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

AgentRole = Literal["legal_search", "case_law_graph", "institutional", "auditor"]
AgentStatus = Literal["completed", "needs_review", "failed"]
SourceKey = tuple[str, str]


@dataclass(frozen=True)
class AgentInput:
    """Contexte minimal transmis à un agent sans élargir son mandat."""

    request_id: str
    task: str
    jurisdiction: str | None = None
    facts: tuple[str, ...] = ()
    context: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id ne peut pas être vide.")
        if not self.task.strip():
            raise ValueError("task ne peut pas être vide.")
        if self.jurisdiction is not None and not self.jurisdiction.strip():
            raise ValueError("jurisdiction doit être omise ou non vide.")
        if not all(isinstance(fact, str) and fact.strip() for fact in self.facts):
            raise ValueError("facts doit contenir uniquement des chaînes non vides.")
        if self.context is not None and not isinstance(self.context, dict):
            raise ValueError("context doit être un objet ou None.")


@dataclass(frozen=True)
class SourceReference:
    """Référence contrôlable vers un passage de la base de connaissances."""

    record_id: str
    section_id: str
    citation: str
    text: str

    @property
    def key(self) -> SourceKey:
        return self.record_id, self.section_id

    def to_dict(self) -> dict[str, str]:
        return {
            "record_id": self.record_id,
            "section_id": self.section_id,
            "citation": self.citation,
            "text": self.text,
        }


@dataclass(frozen=True)
class SourcedClaim:
    """Affirmation proposée avec les références exactes qui la soutiennent."""

    text: str
    source_refs: tuple[SourceKey, ...]


@dataclass(frozen=True)
class AgentResult:
    """Résultat normalisé conservant rôle, sources, incertitudes et claims."""

    role: AgentRole
    status: AgentStatus
    summary: str
    sources: tuple[SourceReference, ...] = ()
    claims: tuple[SourcedClaim, ...] = ()
    uncertainties: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.role not in {"legal_search", "case_law_graph", "institutional", "auditor"}:
            raise ValueError(f"Rôle d'agent non pris en charge : {self.role}.")
        if self.status not in {"completed", "needs_review", "failed"}:
            raise ValueError(f"Statut d'agent non pris en charge : {self.status}.")
        if not self.summary.strip():
            raise ValueError("summary ne peut pas être vide.")
        if not all(isinstance(source, SourceReference) for source in self.sources):
            raise ValueError("sources doit contenir uniquement des SourceReference.")
        if not all(isinstance(claim, SourcedClaim) for claim in self.claims):
            raise ValueError("claims doit contenir uniquement des SourcedClaim.")
        if not all(item.strip() for item in self.uncertainties):
            raise ValueError("Les incertitudes doivent être des chaînes non vides.")
        if not all(item.strip() for item in self.recommendations):
            raise ValueError("Les recommandations doivent être des chaînes non vides.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "status": self.status,
            "summary": self.summary,
            "sources": [source.to_dict() for source in self.sources],
            "claims": [
                {
                    "text": claim.text,
                    "source_refs": [
                        {"record_id": record_id, "section_id": section_id}
                        for record_id, section_id in claim.source_refs
                    ],
                }
                for claim in self.claims
            ],
            "uncertainties": list(self.uncertainties),
            "recommendations": list(self.recommendations),
        }
