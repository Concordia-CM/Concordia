"""Recherche documentaire pour une analyse thématique des lacunes de politique."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from src.agents.legal_policy_agent import LegalPolicyAgent
from src.knowledge.index import KnowledgeBase


def policy_gap_fingerprint(
    domain: str,
    issue: str,
    gap_categories: list[str],
    use_llm: bool,
) -> str:
    payload = {
        "domain": domain,
        "issue": issue,
        "gap_categories": gap_categories,
        "use_llm": use_llm,
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def create_policy_gap_report(
    knowledge_base: KnowledgeBase,
    domain: str,
    issue: str,
    gap_categories: list[str],
    use_llm: bool = False,
) -> dict[str, object]:
    if not isinstance(domain, str) or not domain.strip():
        raise ValueError("Le domaine de politique ne peut pas être vide.")
    if not isinstance(issue, str) or not issue.strip():
        raise ValueError("La problématique ne peut pas être vide.")
    if not isinstance(gap_categories, list) or not gap_categories or not all(
        isinstance(category, str) and category.strip() for category in gap_categories
    ):
        raise ValueError("Sélectionnez au moins une catégorie de lacune.")
    if not isinstance(use_llm, bool):
        raise ValueError("use_llm doit être booléen.")

    domain = domain.strip()
    issue = issue.strip()
    started_at = datetime.now(timezone.utc).isoformat()
    question = f"{domain} : {issue}"
    comparative_query = (
        f"{domain} international global policy frameworks standards "
        f"politiques mondiales cadres internationaux normes {issue}"
    )
    analysis_context = (
        "Type de tâche : analyse des lacunes de politique centrée sur un domaine, "
        "dans le périmètre juridique OHADA-CEMAC, en commençant par le Cameroun. "
        "La géographie n'est pas l'objet des recommandations.\n"
        f"Domaine : {domain}\n"
        f"Problématique à examiner : {issue}\n"
        f"Catégories de lacunes demandées : {', '.join(gap_categories)}\n"
        "Analyse les lacunes de responsabilités, politiques, stratégies, normes, "
        "capacités technologiques, cadre législatif, coordination et conflits "
        "d'objectifs selon les sources disponibles. Compare avec des politiques, "
        "cadres ou standards mondiaux pertinents retrouvés dans la base. Distingue "
        "les sources OHADA-CEMAC/Cameroun des sources internationales d'après leurs "
        "citations et métadonnées ; n'invente aucune source ni portée géographique. "
        "Si aucun comparateur mondial pertinent n'est récupéré, indique cette limite. "
        "Ne formule pas de recommandation propre à un pays."
    )
    result = LegalPolicyAgent(knowledge_base).answer(
        question,
        use_llm=use_llm,
        source_scope="all",
        include_doctrine=True,
        analysis_context=analysis_context,
        retrieval_query=domain,
        additional_retrieval_queries=[comparative_query],
        additional_source_scope="global_policy",
    )
    completed_at = datetime.now(timezone.utc).isoformat()
    sources = result.get("sources", [])
    doctrine_sources = result.get("doctrine_sources", [])
    policy = result.get("policy", {})
    retrieval_groups = [
        {
            "purpose": (
                "domain_context"
                if index == 0
                else "international_comparison_candidates"
            ),
            **retrieval_group,
        }
        for index, retrieval_group in enumerate(result.get("retrieval_results", []))
        if isinstance(retrieval_group, dict)
    ]
    comparator_group = next(
        (
            group
            for group in retrieval_groups
            if group["purpose"] == "international_comparison_candidates"
        ),
        {"sources": [], "doctrine_sources": []},
    )
    global_comparator_count = len(comparator_group["sources"]) + len(
        comparator_group["doctrine_sources"]
    )
    limitations = [
        "La recherche de comparateurs mondiaux utilise les sources présentes dans "
        "l'index ; la couverture internationale actuelle est limitée.",
        "Les textes nationaux ou régionaux retrouvés servent de contexte "
        "documentaire, pas de base à des recommandations propres à un pays.",
        "La pertinence, la version, la portée et l'applicabilité de chaque source "
        "doivent être vérifiées par une personne qualifiée.",
        (
            "La génération Ollama a été demandée ; selon la configuration, le "
            "serveur reçoit le domaine, la problématique et les extraits retrouvés."
            if use_llm
            else "Aucun contenu n'est transmis à Ollama pour cette recherche."
        ),
    ]
    if not global_comparator_count:
        limitations.append(
            "Aucun comparateur mondial portant une portée globale ou internationale "
            "explicite n'a été récupéré pour cette recherche."
        )
    return {
        "analysis_id": str(uuid4()),
        "analysis_type": "domain_policy_gap_analysis",
        "domain": domain,
        "issue": issue,
        "gap_categories": list(gap_categories),
        "answer": result.get("answer", ""),
        "answer_mode": result.get("answer_mode", "unknown"),
        "sources": sources,
        "doctrine_sources": doctrine_sources,
        "retrieval_groups": retrieval_groups,
        "global_comparator_count": global_comparator_count,
        "policy": policy,
        "limitations": limitations,
        "started_at": started_at,
        "completed_at": completed_at,
        "audit_trace": [
            {
                "step": "request_structured",
                "timestamp": started_at,
                "domain": domain,
                "gap_categories": list(gap_categories),
            },
            {
                "step": "knowledge_base_searched",
                "timestamp": completed_at,
                "source_scope": "all",
                "retrieval_queries": result.get("retrieval_queries", []),
                "retrieval_groups": [
                    {
                        "purpose": group["purpose"],
                        "query": group["query"],
                        "source_count": len(group["sources"]),
                        "doctrine_source_count": len(group["doctrine_sources"]),
                    }
                    for group in retrieval_groups
                ],
                "source_count": len(sources),
                "doctrine_source_count": len(doctrine_sources),
                "source_keys": [
                    {
                        "record_id": source.get("record_id"),
                        "section_id": source.get("section_id"),
                        "citation": source.get("citation"),
                    }
                    for source in [*sources, *doctrine_sources]
                    if isinstance(source, dict)
                ],
            },
            {
                "step": "provenance_policy_checked",
                "timestamp": completed_at,
                "decision": policy.get("decision") if isinstance(policy, dict) else None,
            },
        ],
    }
