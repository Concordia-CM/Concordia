"""Coordonne les contrôles d'un scénario dans l'ordre des événements reçus."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.agents.auditor_agent import AuditorAgent
from src.agents.institutional_agent import InstitutionalAgent
from src.agents.legal_policy_agent import LegalPolicyAgent
from src.knowledge.index import KnowledgeBase
from src.sink.audit_logger import write_audit_log
from src.sink.report_generator import write_audit_report


def _string_list(value: Any, field: str, event_id: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field} doit être une liste de textes dans l'événement {event_id}.")
    return value


def run_scenario(
    scenario_path: str | Path,
    knowledge_base: KnowledgeBase,
    output_dir: str | Path,
) -> dict[str, Any]:
    source_path = Path(scenario_path)
    try:
        scenario = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Scénario JSON illisible {source_path}: {error}") from error
    if not isinstance(scenario, dict):
        raise ValueError("Le fichier de scénario doit contenir un objet JSON.")

    events = scenario.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("Le scénario doit contenir une liste non vide d'événements.")

    institutional_config = scenario.get("institutional_review")
    institutional_agent = None
    if institutional_config is not None:
        if not isinstance(institutional_config, dict):
            raise ValueError("institutional_review doit être un objet JSON.")
        institution = institutional_config.get("institution")
        mandate = institutional_config.get("mandate")
        jurisdiction = institutional_config.get("jurisdiction")
        generate = institutional_config.get("generate", False)
        if not isinstance(institution, str) or not institution.strip():
            raise ValueError("institutional_review.institution doit être un texte non vide.")
        if not isinstance(mandate, str) or not mandate.strip():
            raise ValueError("institutional_review.mandate doit être un texte non vide.")
        if jurisdiction is not None and (
            not isinstance(jurisdiction, str) or not jurisdiction.strip()
        ):
            raise ValueError(
                "institutional_review.jurisdiction doit être omise ou non vide."
            )
        if not isinstance(generate, bool):
            raise ValueError("institutional_review.generate doit être booléen.")
        institutional_agent = InstitutionalAgent(knowledge_base)

    legal_agent = LegalPolicyAgent(knowledge_base)
    auditor = AuditorAgent(legal_agent)
    audit_id = str(uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    processed_events = []
    log_events = []

    for event_index, event_value in enumerate(events, start=1):
        if not isinstance(event_value, dict):
            raise ValueError(f"L'événement {event_index} doit être un objet JSON.")
        event_id = str(event_value.get("event_id") or event_index)
        facts = _string_list(event_value.get("facts", []), "facts", event_id)
        documents = _string_list(
            event_value.get("documents_received", []),
            "documents_received",
            event_id,
        )
        checks = event_value.get("checks", [])
        if not isinstance(checks, list) or not checks:
            raise ValueError(f"L'événement {event_id} doit contenir au moins un contrôle.")

        check_results = []
        for check_value in checks:
            if not isinstance(check_value, dict):
                raise ValueError(f"Chaque contrôle de l'événement {event_id} doit être un objet.")
            check_result = auditor.assess_check(check_value, facts, documents)
            if institutional_agent is not None:
                check_result["institutional_analysis"] = institutional_agent.analyze(
                    check_result["question"],
                    institution=institution,
                    mandate=mandate,
                    jurisdiction=jurisdiction,
                    use_llm=generate,
                )
            check_results.append(check_result)

        assessed_at = datetime.now(timezone.utc).isoformat()
        processed_events.append(
            {
                "event_id": event_id,
                "sequence": event_index,
                "assessed_at": assessed_at,
                "title": str(event_value.get("title") or f"Événement {event_index}"),
                "facts": facts,
                "documents_received": documents,
                "checks": check_results,
            }
        )
        log_events.append(
            {
                "event_id": event_id,
                "sequence": event_index,
                "assessed_at": assessed_at,
                "checks": [
                    {
                        "check_id": item["check_id"],
                        "question": item["question"],
                        "finding": item["finding"],
                        "policy": item.get("policy"),
                        "institutional_analysis": item.get("institutional_analysis"),
                        "sources": [
                            {
                                "record_id": source["record_id"],
                                "section_id": source["section_id"],
                                "citation": source["citation"],
                            }
                            for source in item["sources"]
                        ],
                    }
                    for item in check_results
                ],
            }
        )

    completed_at = datetime.now(timezone.utc).isoformat()
    report = {
        "audit_id": audit_id,
        "scenario_id": str(scenario.get("scenario_id") or source_path.stem),
        "title": str(scenario.get("title") or source_path.stem),
        "jurisdiction": str(scenario.get("jurisdiction") or ""),
        "started_at": started_at,
        "completed_at": completed_at,
        "assessment": "human_review_required",
        "events": processed_events,
        "limitations": [
            "Les événements ont été évalués dans l'ordre et les informations futures "
            "n'ont pas été transmises aux contrôles précédents.",
            "Les résultats sont des pistes documentaires ; ils ne constituent pas une "
            "décision juridique ni une conclusion automatique de conformité.",
            "Les pièces attendues sont définies par le scénario et doivent être validées "
            "par un responsable métier.",
        ],
    }

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    report_path = destination / f"audit-{audit_id}.json"
    log_path = destination / f"audit-{audit_id}.jsonl"
    write_audit_report(report, report_path)
    write_audit_log(
        audit_id=audit_id,
        scenario_id=report["scenario_id"],
        started_at=started_at,
        completed_at=completed_at,
        events=log_events,
        path=log_path,
    )
    report["report_path"] = str(report_path)
    report["audit_log_path"] = str(log_path)
    return report