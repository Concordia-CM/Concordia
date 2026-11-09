"""Évaluation reproductible du rappel des sources par la recherche documentaire."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.knowledge.index import KnowledgeBase, RetrievalMode


@dataclass(frozen=True)
class ExpectedSource:
    record_id: str
    section_id: str


@dataclass(frozen=True)
class RetrievalCase:
    case_id: str
    question: str
    expected_sources: tuple[ExpectedSource, ...]


def load_retrieval_cases(path: str | Path) -> list[RetrievalCase]:
    """Charge et valide un benchmark JSON de questions et de références attendues."""
    benchmark_path = Path(path)
    try:
        payload: Any = json.loads(benchmark_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Benchmark de recherche illisible {benchmark_path}: {error}") from error

    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise ValueError("Le benchmark doit contenir une liste 'cases'.")
    cases = []
    seen_case_ids: set[str] = set()
    for index, value in enumerate(payload["cases"], start=1):
        if not isinstance(value, dict):
            raise ValueError(f"Le cas {index} du benchmark doit être un objet.")
        case_id = value.get("case_id")
        question = value.get("question")
        raw_sources = value.get("expected_sources")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"Le cas {index} doit avoir un case_id non vide.")
        if case_id in seen_case_ids:
            raise ValueError(f"Identifiant de cas dupliqué : {case_id}.")
        seen_case_ids.add(case_id)
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"La question du cas {case_id} doit être non vide.")
        if not isinstance(raw_sources, list) or not raw_sources:
            raise ValueError(f"Le cas {case_id} doit contenir des expected_sources.")

        expected_sources = []
        seen_sources: set[tuple[str, str]] = set()
        for source in raw_sources:
            if not isinstance(source, dict):
                raise ValueError(f"Chaque source attendue du cas {case_id} doit être un objet.")
            record_id = source.get("record_id")
            section_id = source.get("section_id")
            if not isinstance(record_id, str) or not record_id.strip():
                raise ValueError(f"Une source attendue du cas {case_id} n'a pas de record_id.")
            if not isinstance(section_id, str) or not section_id.strip():
                raise ValueError(f"Une source attendue du cas {case_id} n'a pas de section_id.")
            identity = (record_id, section_id)
            if identity in seen_sources:
                raise ValueError(f"Source attendue dupliquée dans le cas {case_id}.")
            seen_sources.add(identity)
            expected_sources.append(ExpectedSource(record_id, section_id))

        cases.append(
            RetrievalCase(
                case_id=case_id,
                question=question.strip(),
                expected_sources=tuple(expected_sources),
            )
        )
    if not cases:
        raise ValueError("Le benchmark doit contenir au moins un cas.")
    return cases


def evaluate_retrieval(
    knowledge_base: KnowledgeBase,
    cases: list[RetrievalCase],
    top_k: int = 5,
    retrieval_mode: RetrievalMode = "fts",
) -> dict[str, Any]:
    """Calcule hit rate, recall, MRR, couverture de citations et latence au top-k."""
    if top_k < 1:
        raise ValueError("top_k doit être positif.")
    if not cases:
        raise ValueError("Au moins un cas est requis pour évaluer la recherche.")

    case_results = []
    total_recall = 0.0
    reciprocal_rank_sum = 0.0
    hits_at_k = 0
    relevant_results = 0
    cited_relevant_results = 0
    elapsed_ms = 0.0

    for case in cases:
        started = time.perf_counter()
        results = knowledge_base.search(
            case.question,
            limit=top_k,
            retrieval_mode=retrieval_mode,
        )
        elapsed = (time.perf_counter() - started) * 1000
        elapsed_ms += elapsed

        expected = {
            (source.record_id, source.section_id) for source in case.expected_sources
        }
        retrieved = [
            (hit.record_id, hit.section_id, hit.citation)
            for hit in results
        ]
        relevant_ranks = [
            rank
            for rank, (record_id, section_id, _) in enumerate(retrieved, start=1)
            if (record_id, section_id) in expected
        ]
        retrieved_expected = {
            (record_id, section_id)
            for record_id, section_id, _ in retrieved
            if (record_id, section_id) in expected
        }
        case_recall = len(retrieved_expected) / len(expected)
        total_recall += case_recall
        if relevant_ranks:
            hits_at_k += 1
            reciprocal_rank_sum += 1 / relevant_ranks[0]
        relevant_results += len(retrieved_expected)
        cited_relevant_results += sum(
            bool(citation.strip())
            for record_id, section_id, citation in retrieved
            if (record_id, section_id) in expected
        )
        case_results.append(
            {
                "case_id": case.case_id,
                "question": case.question,
                "expected_sources": len(expected),
                "retrieved_expected_sources": len(retrieved_expected),
                "reciprocal_rank": 1 / relevant_ranks[0] if relevant_ranks else 0.0,
                "relevant_ranks": relevant_ranks,
                "top_result_citations": [citation for _, _, citation in retrieved[:3]],
                "latency_ms": round(elapsed, 3),
            }
        )

    case_count = len(cases)
    return {
        "case_count": case_count,
        "top_k": top_k,
        "retrieval_mode": retrieval_mode,
        "hit_rate_at_k": hits_at_k / case_count,
        "mean_recall_at_k": total_recall / case_count,
        "mean_reciprocal_rank": reciprocal_rank_sum / case_count,
        "citation_coverage_of_retrieved_relevant": (
            cited_relevant_results / relevant_results if relevant_results else 0.0
        ),
        "mean_latency_ms": round(elapsed_ms / case_count, 3),
        "cases": case_results,
    }
