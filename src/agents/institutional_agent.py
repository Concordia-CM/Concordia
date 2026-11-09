"""Analyse documentaire selon un mandat institutionnel explicitement fourni."""

from __future__ import annotations

from typing import Any

from config.settings import Settings
from src.agents.contracts import AgentResult, SourceReference
from src.knowledge.index import (
    KnowledgeBase,
    RetrievalMode,
    SourceScope,
    format_documentary_answer,
)
from src.llm.ollama_client import OllamaClient
from src.policy.legal_policy import LegalPolicyGuard


class InstitutionalAgent:
    """Prépare une perspective institutionnelle sourcée, pas une position officielle."""

    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        top_k: int = 5,
        settings: Settings | None = None,
        ollama_client: OllamaClient | None = None,
    ) -> None:
        if top_k < 1:
            raise ValueError("top_k doit être positif.")
        self.knowledge_base = knowledge_base
        self.top_k = top_k
        self.settings = settings
        self.ollama_client = ollama_client

    def analyze(
        self,
        question: str,
        institution: str,
        mandate: str,
        jurisdiction: str | None = None,
        retrieval_mode: RetrievalMode = "fts",
        use_llm: bool = False,
        source_scope: SourceScope = "legal_texts",
    ) -> dict[str, Any]:
        for field, value in (
            ("question", question),
            ("institution", institution),
            ("mandate", mandate),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} ne peut pas être vide.")
        if jurisdiction is not None and (
            not isinstance(jurisdiction, str) or not jurisdiction.strip()
        ):
            raise ValueError("jurisdiction doit être omise ou non vide.")

        hits = self.knowledge_base.search(
            question,
            limit=self.top_k,
            retrieval_mode=retrieval_mode,
            source_scope=source_scope,
        )
        sources = tuple(
            SourceReference(
                record_id=hit.record_id,
                section_id=hit.section_id,
                citation=hit.citation,
                text=hit.text,
            )
            for hit in hits
        )
        claims = ()
        if use_llm and sources:
            institutional_prompt = (
                f"Perspective demandée : {institution}.\n"
                f"Mandat déclaré pour cet exercice : {mandate}.\n"
                f"Juridiction : {jurisdiction or 'non précisée'}.\n"
                "Il s'agit d'une simulation documentaire, pas d'une position officielle. "
                "Signale les limites du corpus et ne déduis pas de pouvoir ou de règle "
                "qui ne figure pas dans les passages.\n"
                f"Question : {question}"
            )
            client = self.ollama_client or OllamaClient(self.settings)
            claims = client.generate_claims(institutional_prompt, sources)

        summary = (
            format_documentary_answer(question, hits)
            if hits
            else "Aucun passage correspondant n'a été retrouvé dans l'index."
        )
        result = AgentResult(
            role="institutional",
            status="completed" if hits and (not use_llm or claims) else "needs_review",
            summary=summary,
            sources=sources,
            claims=claims,
            uncertainties=(
                "Cette analyse applique uniquement le mandat fourni comme contexte de "
                "recherche ; elle ne constitue pas une position officielle de l'institution.",
                "La couverture du corpus, la compétence institutionnelle, la version "
                "des textes et leur applicabilité doivent être vérifiées par une personne.",
            ),
        )
        policy = LegalPolicyGuard(self.knowledge_base).evaluate(result)

        if policy.decision == "blocked":
            result = AgentResult(
                role="institutional",
                status="failed",
                summary="La proposition a été retenue par le contrôle de provenance.",
                uncertainties=(
                    "Vérifier les sources et les affirmations avant toute utilisation.",
                ),
            )
        elif claims:
            source_by_key = {source.key: source for source in sources}
            result = AgentResult(
                role="institutional",
                status=result.status,
                summary="\n\n".join(
                    f"- {claim.text}\n  Sources : "
                    + "; ".join(
                        source_by_key[source_ref].citation
                        for source_ref in claim.source_refs
                    )
                    for claim in claims
                ),
                sources=sources,
                claims=claims,
                uncertainties=result.uncertainties,
            )
        return {
            "institution": institution.strip(),
            "mandate": mandate.strip(),
            "jurisdiction": jurisdiction.strip() if jurisdiction else None,
            "source_scope": source_scope,
            "agent_result": result.to_dict(),
            "policy": policy.to_dict(),
        }
