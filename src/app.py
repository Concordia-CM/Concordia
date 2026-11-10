"""Interface en ligne de commande pour la recherche et les audits documentaires."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

if __package__ in (None, ""):
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from config.settings import Settings, get_settings
from src.agents.institutional_agent import InstitutionalAgent
from src.agents.legal_policy_agent import LegalPolicyAgent
from src.knowledge.index import (
    DEFAULT_CCJA_CHUNKS,
    DEFAULT_CCJA_DOCUMENTS,
    DEFAULT_PROCESSED_DIR,
    KnowledgeBase,
)
from src.knowledge.evaluation import evaluate_retrieval, load_retrieval_cases
from src.orchestrator.coordinator import run_scenario
from src.orchestrator.intent_router import (
    DocumentAuditRequest,
    InstitutionalAnalysisRequest,
    LegalSearchRequest,
    SUPPORTED_INTENTS,
    route_request,
)
from src.sink.report_generator import render_markdown


def _parser(settings: Settings | None = None) -> argparse.ArgumentParser:
    app_settings = settings or get_settings()
    parser = argparse.ArgumentParser(
        description="Recherche sourcée et audit documentaire Concordia."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build-index", help="Construire ou reconstruire l'index local.")
    build.add_argument("--db", type=Path, default=app_settings.database_path)
    build.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    build.add_argument("--ccja-documents", type=Path, default=DEFAULT_CCJA_DOCUMENTS)
    build.add_argument("--ccja-chunks", type=Path, default=DEFAULT_CCJA_CHUNKS)
    build.add_argument(
        "--vector-model",
        help=(
            "Construire aussi l'index vectoriel avec ce modèle local "
            f"(défaut : {app_settings.embedding_model})."
        ),
    )

    ask = commands.add_parser("ask", help="Rechercher des passages juridiques avec citations.")
    ask.add_argument("question")
    ask.add_argument("--db", type=Path, default=app_settings.database_path)
    ask.add_argument("--top-k", type=int, default=5)
    ask.add_argument("--retrieval-mode", choices=("fts", "vector", "hybrid"), default="fts")
    ask.add_argument(
        "--source-scope",
        choices=("legal_texts", "case_law", "doctrine", "all"),
        default="legal_texts",
        help=(
            "Limiter la recherche aux textes, à la jurisprudence CCJA, à la doctrine "
            "ou à toutes les sources."
        ),
    )
    ask.add_argument(
        "--include-doctrine",
        action="store_true",
        help="Afficher séparément les passages doctrinaux comme éclairage, jamais comme obligation.",
    )
    _add_generation_options(ask)

    audit = commands.add_parser("audit", help="Exécuter les événements d'un scénario.")
    audit.add_argument("scenario", type=Path)
    audit.add_argument("--db", type=Path, default=app_settings.database_path)
    audit.add_argument("--output-dir", type=Path, default=Path("data/audits"))
    _add_generation_options(audit)

    route = commands.add_parser(
        "route",
        help="Router vers la recherche juridique, l'audit ou l'analyse institutionnelle.",
    )
    route.add_argument("request", help="Demande en français à traiter.")
    route.add_argument(
        "--intent",
        choices=SUPPORTED_INTENTS,
        help="Forcer le parcours au lieu de l'inférer à partir de mots-clés.",
    )
    route.add_argument("--scenario", type=Path, help="Fichier JSON requis pour un audit.")
    route.add_argument("--institution", help="Institution ou rôle institutionnel à examiner.")
    route.add_argument("--mandate", help="Mandat explicite de l'analyse institutionnelle.")
    route.add_argument("--jurisdiction", help="Juridiction concernée par l'analyse.")
    route.add_argument("--db", type=Path, default=app_settings.database_path)
    route.add_argument("--top-k", type=int, default=5)
    route.add_argument("--retrieval-mode", choices=("fts", "vector", "hybrid"), default="fts")
    route.add_argument(
        "--source-scope",
        choices=("legal_texts", "case_law", "doctrine", "all"),
        default="legal_texts",
        help="Périmètre de sources pour la recherche juridique ou institutionnelle.",
    )
    route.add_argument(
        "--include-doctrine",
        action="store_true",
        help="Afficher séparément les passages doctrinaux comme éclairage, jamais comme obligation.",
    )
    _add_generation_options(route)
    route.add_argument("--output-dir", type=Path, default=Path("data/audits"))

    graph = commands.add_parser("graph", help="Afficher les relations CCJA indexées.")
    graph.add_argument("record_id", help="Identifiant d'une décision, par exemple OHADA-CCJA-00000.")
    graph.add_argument("--db", type=Path, default=app_settings.database_path)

    graph_neighbors = commands.add_parser(
        "graph-neighbors",
        help="Afficher la structure documentaire et les articles cités d'une source.",
    )
    graph_neighbors.add_argument("record_id", help="Identifiant du document indexé.")
    graph_neighbors.add_argument("--section-id", help="Limiter les relations à un article ou une section.")
    graph_neighbors.add_argument("--db", type=Path, default=app_settings.database_path)

    evaluate = commands.add_parser(
        "evaluate-search",
        help="Mesurer la recherche sur un benchmark de références attendues.",
    )
    evaluate.add_argument("benchmark", type=Path)
    evaluate.add_argument("--db", type=Path, default=app_settings.database_path)
    evaluate.add_argument("--top-k", type=int, default=5)
    evaluate.add_argument("--retrieval-mode", choices=("fts", "vector", "hybrid"), default="fts")
    evaluate.add_argument(
        "--source-scope",
        choices=("legal_texts", "case_law", "doctrine", "all"),
        default="legal_texts",
        help="Périmètre des sources évaluées.",
    )
    return parser


def _add_generation_options(parser: argparse.ArgumentParser) -> None:
    generation = parser.add_mutually_exclusive_group()
    generation.add_argument(
        "--generate",
        dest="generate",
        action="store_true",
        help="Générer une réponse narrative sourcée avec Ollama (défaut).",
    )
    generation.add_argument(
        "--extractive",
        dest="generate",
        action="store_false",
        help="Désactiver Ollama et afficher uniquement les passages retrouvés.",
    )
    parser.set_defaults(generate=True)


def _print_source_scope(source_scope: str) -> None:
    labels = {
        "legal_texts": "textes juridiques (hors doctrine et jurisprudence CCJA)",
        "case_law": "jurisprudence CCJA",
        "doctrine": "doctrine et manuels (éclairage non normatif)",
        "all": "toutes les sources indexées",
    }
    print(f"\nPérimètre des sources : {labels[source_scope]}")


def main(argv: list[str] | None = None) -> int:
    try:
        settings = get_settings()
        parser = _parser(settings)
        arguments = sys.argv[1:] if argv is None else argv
        if not arguments:
            parser.print_help()
            return 0
        args = parser.parse_args(arguments)
        routed_request = None
        if args.command == "route":
            routed_request = route_request(
                args.request,
                intent=args.intent,
                scenario_path=args.scenario,
                institution=args.institution,
                mandate=args.mandate,
                jurisdiction=args.jurisdiction,
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
                use_llm=args.generate,
                source_scope=args.source_scope,
                include_doctrine=args.include_doctrine,
            )
            print(result["answer"])
            _print_source_scope(args.source_scope)
            print(f"\nContrôle Policy : {result['policy']['decision']}")
        elif args.command == "audit":
            route = route_request(
                str(args.scenario),
                intent="document_audit",
                scenario_path=args.scenario,
            )
            if not isinstance(route, DocumentAuditRequest):
                raise RuntimeError("Le routeur n'a pas retourné un audit documentaire.")
            report = run_scenario(
                route.scenario_path,
                knowledge_base,
                args.output_dir,
                use_llm=args.generate,
            )
            print(render_markdown(report))
            print(f"Rapport JSON : {report['report_path']}")
            print(f"Journal d'audit : {report['audit_log_path']}")
        elif args.command == "route":
            if isinstance(routed_request, LegalSearchRequest):
                result = LegalPolicyAgent(knowledge_base, top_k=args.top_k).answer(
                    routed_request.question,
                    retrieval_mode=args.retrieval_mode,
                    use_llm=args.generate,
                    source_scope=args.source_scope,
                    include_doctrine=args.include_doctrine,
                )
                print(result["answer"])
                _print_source_scope(args.source_scope)
                print(f"\nContrôle Policy : {result['policy']['decision']}")
            elif isinstance(routed_request, DocumentAuditRequest):
                report = run_scenario(
                    routed_request.scenario_path,
                    knowledge_base,
                    args.output_dir,
                    use_llm=args.generate,
                )
                print(render_markdown(report))
                print(f"Rapport JSON : {report['report_path']}")
                print(f"Journal d'audit : {report['audit_log_path']}")
            elif isinstance(routed_request, InstitutionalAnalysisRequest):
                result = InstitutionalAgent(
                    knowledge_base,
                    top_k=args.top_k,
                    settings=settings,
                ).analyze(
                    routed_request.question,
                    institution=routed_request.institution,
                    mandate=routed_request.mandate,
                    jurisdiction=routed_request.jurisdiction,
                    retrieval_mode=args.retrieval_mode,
                    use_llm=args.generate,
                    source_scope=args.source_scope,
                    include_doctrine=args.include_doctrine,
                )
                print(result["agent_result"]["summary"])
                _print_source_scope(args.source_scope)
                print(f"\nContrôle Policy : {result['policy']['decision']}")
            else:
                raise RuntimeError("Le routeur n'a retourné aucun parcours.")
        elif args.command == "graph":
            relations = knowledge_base.related(args.record_id)
            print(json.dumps(relations, ensure_ascii=False, indent=2))
        elif args.command == "graph-neighbors":
            relations = knowledge_base.graph_neighborhood(
                args.record_id,
                section_id=args.section_id,
            )
            print(json.dumps(relations, ensure_ascii=False, indent=2))
        elif args.command == "evaluate-search":
            cases = load_retrieval_cases(args.benchmark)
            result = evaluate_retrieval(
                knowledge_base,
                cases,
                top_k=args.top_k,
                retrieval_mode=args.retrieval_mode,
                source_scope=args.source_scope,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, RuntimeError, sqlite3.Error, ValueError) as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
