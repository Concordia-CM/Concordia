"""Interface en ligne de commande pour la recherche et les audits documentaires."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from src.agents.legal_policy_agent import LegalPolicyAgent
from src.knowledge.index import (
    DEFAULT_CCJA_CHUNKS,
    DEFAULT_CCJA_DOCUMENTS,
    DEFAULT_DATABASE,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_PROCESSED_DIR,
    KnowledgeBase,
)
from src.knowledge.evaluation import evaluate_retrieval, load_retrieval_cases
from src.orchestrator.coordinator import run_scenario
from src.orchestrator.intent_router import (
    DocumentAuditRequest,
    LegalSearchRequest,
    SUPPORTED_INTENTS,
    route_request,
)
from src.sink.report_generator import render_markdown


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recherche sourcée et audit documentaire Concordia."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build-index", help="Construire ou reconstruire l'index local.")
    build.add_argument("--db", type=Path, default=DEFAULT_DATABASE)
    build.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    build.add_argument("--ccja-documents", type=Path, default=DEFAULT_CCJA_DOCUMENTS)
    build.add_argument("--ccja-chunks", type=Path, default=DEFAULT_CCJA_CHUNKS)
    build.add_argument(
        "--vector-model",
        help=(
            "Construire aussi l'index vectoriel avec ce modèle local "
            f"(défaut : {DEFAULT_EMBEDDING_MODEL})."
        ),
    )

    ask = commands.add_parser("ask", help="Rechercher des passages juridiques avec citations.")
    ask.add_argument("question")
    ask.add_argument("--db", type=Path, default=DEFAULT_DATABASE)
    ask.add_argument("--top-k", type=int, default=5)
    ask.add_argument("--retrieval-mode", choices=("fts", "vector", "hybrid"), default="fts")

    audit = commands.add_parser("audit", help="Exécuter les événements d'un scénario.")
    audit.add_argument("scenario", type=Path)
    audit.add_argument("--db", type=Path, default=DEFAULT_DATABASE)
    audit.add_argument("--output-dir", type=Path, default=Path("data/audits"))

    route = commands.add_parser(
        "route",
        help="Router une demande vers la recherche juridique ou l'audit documentaire.",
    )
    route.add_argument("request", help="Demande en français à traiter.")
    route.add_argument(
        "--intent",
        choices=SUPPORTED_INTENTS,
        help="Forcer le parcours au lieu de l'inférer à partir de mots-clés.",
    )
    route.add_argument("--scenario", type=Path, help="Fichier JSON requis pour un audit.")
    route.add_argument("--db", type=Path, default=DEFAULT_DATABASE)
    route.add_argument("--top-k", type=int, default=5)
    route.add_argument("--retrieval-mode", choices=("fts", "vector", "hybrid"), default="fts")
    route.add_argument("--output-dir", type=Path, default=Path("data/audits"))

    graph = commands.add_parser("graph", help="Afficher les relations CCJA indexées.")
    graph.add_argument("record_id", help="Identifiant d'une décision, par exemple OHADA-CCJA-00000.")
    graph.add_argument("--db", type=Path, default=DEFAULT_DATABASE)

    evaluate = commands.add_parser(
        "evaluate-search",
        help="Mesurer la recherche sur un benchmark de références attendues.",
    )
    evaluate.add_argument("benchmark", type=Path)
    evaluate.add_argument("--db", type=Path, default=DEFAULT_DATABASE)
    evaluate.add_argument("--top-k", type=int, default=5)
    evaluate.add_argument("--retrieval-mode", choices=("fts", "vector", "hybrid"), default="fts")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        routed_request = None
        if args.command == "route":
            routed_request = route_request(
                args.request,
                intent=args.intent,
                scenario_path=args.scenario,
            )
        knowledge_base = KnowledgeBase(args.db)
        if args.command == "build-index":
            result = knowledge_base.build(
                processed_dir=args.processed_dir,
                ccja_documents=args.ccja_documents,
                ccja_chunks=args.ccja_chunks,
            )
            if args.vector_model:
                result["vectors"] = knowledge_base.build_vectors(args.vector_model)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print(f"Index prêt : {args.db}")
        elif args.command == "ask":
            route = route_request(args.question, intent="legal_search")
            if not isinstance(route, LegalSearchRequest):
                raise RuntimeError("Le routeur n'a pas retourné une recherche juridique.")
            result = LegalPolicyAgent(knowledge_base, top_k=args.top_k).answer(
                route.question,
                retrieval_mode=args.retrieval_mode,
            )
            print(result["answer"])
        elif args.command == "audit":
            route = route_request(
                str(args.scenario),
                intent="document_audit",
                scenario_path=args.scenario,
            )
            if not isinstance(route, DocumentAuditRequest):
                raise RuntimeError("Le routeur n'a pas retourné un audit documentaire.")
            report = run_scenario(route.scenario_path, knowledge_base, args.output_dir)
            print(render_markdown(report))
            print(f"Rapport JSON : {report['report_path']}")
            print(f"Journal d'audit : {report['audit_log_path']}")
        elif args.command == "route":
            if isinstance(routed_request, LegalSearchRequest):
                result = LegalPolicyAgent(knowledge_base, top_k=args.top_k).answer(
                    routed_request.question,
                    retrieval_mode=args.retrieval_mode,
                )
                print(result["answer"])
            elif isinstance(routed_request, DocumentAuditRequest):
                report = run_scenario(
                    routed_request.scenario_path,
                    knowledge_base,
                    args.output_dir,
                )
                print(render_markdown(report))
                print(f"Rapport JSON : {report['report_path']}")
                print(f"Journal d'audit : {report['audit_log_path']}")
            else:
                raise RuntimeError("Le routeur n'a retourné aucun parcours.")
        elif args.command == "graph":
            relations = knowledge_base.related(args.record_id)
            print(json.dumps(relations, ensure_ascii=False, indent=2))
        elif args.command == "evaluate-search":
            cases = load_retrieval_cases(args.benchmark)
            result = evaluate_retrieval(
                knowledge_base,
                cases,
                top_k=args.top_k,
                retrieval_mode=args.retrieval_mode,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, RuntimeError, sqlite3.Error, ValueError) as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
