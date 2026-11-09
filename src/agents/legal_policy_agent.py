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
    is_doctrine_hit,
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
        include_doctrine: bool = False,
        analysis_context: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("La question ne peut pas être vide.")
        if analysis_context is not None and (
            not isinstance(analysis_context, str) or not analysis_context.strip()
        ):
            raise ValueError("analysis_context doit être omis ou non vide.")
        hits = self.knowledge_base.search(
            question,
            limit=self.top_k,
            retrieval_mode=retrieval_mode,
            source_scope=source_scope,
        )
        doctrine_hits = [
            hit
            for hit in hits
            if is_doctrine_hit(hit)
        ]
        legal_hits = [
            hit
            for hit in hits
            if not is_doctrine_hit(hit)
        ]
        if source_scope == "doctrine":
            doctrine_hits = hits
            legal_hits = []
        elif include_doctrine and source_scope != "all":
            doctrine_hits = self.knowledge_base.search(
                question,
                limit=self.top_k,
                retrieval_mode=retrieval_mode,
                source_scope="doctrine",
            )
        answer_modes = {
            "fts": "extractive_full_text_search",
            "vector": "extractive_vector_search",
            "hybrid": "extractive_hybrid_search",
        }
        answer = (
            format_documentary_answer(question, legal_hits)
            if legal_hits
            else "Aucun passage de texte juridique correspondant n'a été retrouvé."
        )
        primary_label = (
            "Fondements textuels"
            if source_scope == "legal_texts"
            else "Sources hors doctrine"
        )
        if doctrine_hits:
            answer += (
                "\n\nÉclairage doctrinal — explications et pistes de réflexion, "
                "sans valeur d'obligation juridique :\n"
                + "\n\n".join(
                    f"- {hit.citation}\n  {hit.excerpt or hit.text}"
                    for hit in doctrine_hits
                )
            )
        mode = answer_modes[retrieval_mode]
        source_references = tuple(
            SourceReference(
                record_id=hit.record_id,
                section_id=hit.section_id,
                citation=hit.citation,
                text=hit.text,
            )
            for hit in legal_hits
        )
        doctrine_references = tuple(
            SourceReference(
                record_id=hit.record_id,
                section_id=hit.section_id,
                citation=hit.citation,
                text=hit.text,
            )
            for hit in doctrine_hits
        )
        claims = ()
        if use_llm and source_references:
            ollama_client = self.ollama_client or OllamaClient(self.settings)
            generation_question = question
            if analysis_context:
                generation_question += (
                    "\n\nContexte à prendre en compte, sans le traiter comme "
                    f"une source juridique :\n{analysis_context}"
                )
            claims = ollama_client.generate_claims(
                generation_question,
                source_references,
            )
            if claims:
                answer = (
                    f"{primary_label} — synthèse générée en attente du contrôle "
                    "de provenance."
                )
                mode = "ollama_rag"
            else:
                answer = (
                    "Les passages retrouvés ne permettent pas de formuler une "
                    "affirmation sourcée. Vérifiez le corpus et reformulez la question."
                )
                if doctrine_hits:
                    answer += (
                        "\n\nÉclairage doctrinal — explications et pistes de réflexion, "
                        "sans valeur d'obligation juridique :\n"
                        + "\n\n".join(
                            f"- {hit.citation}\n  {hit.excerpt or hit.text}"
                            for hit in doctrine_hits
                        )
                    )
                mode = "ollama_insufficient_sources"
        agent_result = AgentResult(
            role="legal_search",
            status="completed" if hits and (not use_llm or claims) else "needs_review",
            summary=answer,
            sources=source_references + doctrine_references,
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
            legal_hits = []
            doctrine_hits = []
            mode = "policy_blocked"
        elif claims:
            source_by_key = {source.key: source for source in source_references}
            answer = f"{primary_label} :\n\n" + "\n\n".join(
                f"{claim.text}\nSources : "
                + "; ".join(
                    source_by_key[source_ref].citation
                    for source_ref in claim.source_refs
                )
                for claim in claims
            )
            if doctrine_hits:
                answer += (
                    "\n\nÉclairage doctrinal — explications et pistes de réflexion, "
                    "sans valeur d'obligation juridique :\n"
                    + "\n\n".join(
                        f"- {hit.citation}\n  {hit.excerpt or hit.text}"
                        for hit in doctrine_hits
                    )
                )
        return {
            "question": question,
            "answer": answer,
            "answer_mode": mode,
            "source_scope": source_scope,
            "sources": [hit.to_dict() for hit in legal_hits],
            "doctrine_sources": [hit.to_dict() for hit in doctrine_hits],
            "doctrine_notice": (
                "La doctrine apporte un éclairage ou des pistes de contrôle ; "
                "elle ne constitue pas, à elle seule, une obligation juridique."
                if doctrine_hits
                else None
            ),
            "policy": policy.to_dict(),
        }