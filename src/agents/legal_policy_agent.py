"""Agent de recherche juridique fondé sur les passages indexés."""

from __future__ import annotations

from typing import Any

from src.knowledge.index import KnowledgeBase, RetrievalMode, format_documentary_answer


class LegalPolicyAgent:
    """Retrouve les sources et répond par extraits cités, sans conclusion générée."""

    def __init__(self, knowledge_base: KnowledgeBase, top_k: int = 5) -> None:
        self.knowledge_base = knowledge_base
        self.top_k = top_k

    def answer(
        self,
        question: str,
        retrieval_mode: RetrievalMode = "fts",
    ) -> dict[str, Any]:
        hits = self.knowledge_base.search(
            question,
            limit=self.top_k,
            retrieval_mode=retrieval_mode,
        )
        answer_modes = {
            "fts": "extractive_full_text_search",
            "vector": "extractive_vector_search",
            "hybrid": "extractive_hybrid_search",
        }
        return {
            "question": question,
            "answer": format_documentary_answer(question, hits),
            "answer_mode": answer_modes[retrieval_mode],
            "sources": [hit.to_dict() for hit in hits],
        }