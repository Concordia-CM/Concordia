"""Agent de recherche juridique fondé sur les passages indexés."""

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


class LegalPolicyAgent:
    """Retrouve les sources et répond par extraits cités, sans conclusion générée."""

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

    def answer(
        self,
        question: str,
        retrieval_mode: RetrievalMode = "fts",
        use_llm: bool = False,
        source_scope: SourceScope = "legal_texts",
    ) -> dict[str, Any]:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("La question ne peut pas être vide.")
        hits = self.knowledge_base.search(
            question,
            limit=self.top_k,
            retrieval_mode=retrieval_mode,
            source_scope=source_scope,
        )
        answer_modes = {
            "fts": "extractive_full_text_search",
            "vector": "extractive_vector_search",
            "hybrid": "extractive_hybrid_search",
        }
        answer = format_documentary_answer(question, hits)
        mode = answer_modes[retrieval_mode]
        source_references = tuple(
            SourceReference(
                record_id=hit.record_id,
                section_id=hit.section_id,
                citation=hit.citation,
                text=hit.text,
            )
            for hit in hits
        )
        claims = ()
        if use_llm and source_references:
            ollama_client = self.ollama_client or OllamaClient(self.settings)
            claims = ollama_client.generate_claims(question, source_references)
            if claims:
                answer = "Synthèse générée en attente du contrôle de provenance."
                mode = "ollama_rag"
            else:
                answer = (
                    "Les passages retrouvés ne permettent pas de formuler une "
                    "affirmation sourcée. Vérifiez le corpus et reformulez la question."
                )
                mode = "ollama_insufficient_sources"
        agent_result = AgentResult(
            role="legal_search",
            status="completed" if hits and (not use_llm or claims) else "needs_review",
            summary=answer,
            sources=source_references,
            claims=claims,
            uncertainties=(
                "La pertinence, la version en vigueur et l'applicabilité doivent "
                "être vérifiées par une personne qualifiée.",
            ),
        )
        policy = LegalPolicyGuard(self.knowledge_base).evaluate(agent_result)
        if policy.decision == "blocked":
            answer = (
                "Réponse retenue par le contrôle Policy : une citation ou un passage "
                "ne correspond pas au contenu vérifié de l'index."
            )
            hits = []
            mode = "policy_blocked"
        elif claims:
            source_by_key = {source.key: source for source in source_references}
            answer = "\n\n".join(
                f"- {claim.text}\n  Sources : "
                + "; ".join(
                    source_by_key[source_ref].citation
                    for source_ref in claim.source_refs
                )
                for claim in claims
            )
        return {
            "question": question,
            "answer": answer,
            "answer_mode": mode,
            "source_scope": source_scope,
            "sources": [hit.to_dict() for hit in hits],
            "policy": policy.to_dict(),
        }