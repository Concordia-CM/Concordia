"""Workflow d'audit documentaire appelé par l'interface web."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from src.agents.auditor_agent import AuditorAgent
from src.agents.legal_policy_agent import LegalPolicyAgent
from src.knowledge.index import KnowledgeBase
from src.web.checklists import ChecklistTemplate
from src.web.document_extraction import ExtractedDocument


def audit_fingerprint(
    documents: list[ExtractedDocument],
    questions: list[str],
    evidence: list[str],
    facts: str,
    checklist_control_ids: list[str] | None = None,
    use_llm: bool = False,
) -> str:
    digest = hashlib.sha256()
    for document in documents:
        digest.update(document.name.encode("utf-8"))
        digest.update(document.text.encode("utf-8"))
    digest.update(json.dumps(questions, ensure_ascii=False).encode("utf-8"))
    digest.update(json.dumps(evidence, ensure_ascii=False).encode("utf-8"))
    digest.update(facts.encode("utf-8"))
    digest.update(
        json.dumps(checklist_control_ids or [], ensure_ascii=False).encode("utf-8")
    )
    digest.update(str(use_llm).encode("ascii"))
    return digest.hexdigest()


def create_audit_report(
    knowledge_base: KnowledgeBase,
    documents: list[ExtractedDocument],
    questions: list[str],
    evidence_lists: list[list[str]],
    facts: list[str],
    checklist: ChecklistTemplate | None = None,
    checklist_control_ids: list[str] | None = None,
    use_llm: bool = False,
) -> dict[str, object]:
    started_at = datetime.now(timezone.utc).isoformat()
    legal_agent = LegalPolicyAgent(knowledge_base)
    auditor = AuditorAgent(legal_agent)
    document_contents: dict[str, str] = {}
    document_names: list[str] = []
    for document in documents:
        name = document.name
        suffix = 2
        while name in document_contents:
            name = f"{document.name} ({suffix})"
            suffix += 1
        document_names.append(name)
        document_contents[name] = document.text

    checks = [
        auditor.assess_check(
            {
                "check_id": (
                    checklist_control_ids[index - 1]
                    if checklist_control_ids
                    else f"check-{index}"
                ),
                "question": question,
                "expected_evidence": evidence_lists[index - 1],
            },
            facts=facts,
            documents_received=document_names,
            document_contents=document_contents,
            use_llm=use_llm,
        )
        for index, question in enumerate(questions, start=1)
    ]
    completed_at = datetime.now(timezone.utc).isoformat()
    llm_limitation = (
        "Lorsqu'une génération Ollama est lancée, le serveur configuré reçoit les "
        "questions, les noms de fichiers, les faits et éléments attendus ainsi que les "
        "extraits juridiques retrouvés ; le texte intégral des documents déposés n'est "
        "pas transmis."
        if use_llm
        else "Aucun contenu n'est transmis à Ollama pour cet audit."
    )
    return {
        "audit_id": str(uuid4()),
        "title": "Revue documentaire — dossier d'entreprise OHADA",
        "jurisdiction": "Cameroun",
        "started_at": started_at,
        "completed_at": completed_at,
        "assessment": "human_review_required",
        "checklist": (
            checklist.report_metadata(checklist_control_ids or [])
            if checklist
            else None
        ),
        "documents": [
            {
                "name": name,
                "page_count": document.page_count,
                "ocr_pages": list(document.ocr_pages),
                "warnings": list(document.warnings),
            }
            for name, document in zip(document_names, documents, strict=True)
        ],
        "facts_reported": facts,
        "checks": checks,
        "audit_trace": [
            {
                "step": "documents_extracted",
                "timestamp": started_at,
                "document_count": len(document_names),
                "document_names": document_names,
            },
            {
                "step": "controls_assessed",
                "timestamp": completed_at,
                "checks": [
                    {
                        "check_id": check.get("check_id", ""),
                        "question": check.get("question", ""),
                        "finding": check.get("finding", "human_review_required"),
                        "policy_decision": (
                            check["policy"].get("decision")
                            if isinstance(check.get("policy"), dict)
                            else None
                        ),
                        "sources": [
                            {
                                "record_id": source["record_id"],
                                "section_id": source["section_id"],
                                "citation": source["citation"],
                            }
                            for source in check.get("sources", [])
                        ],
                    }
                    for check in checks
                ],
            },
        ],
        "limitations": [
            "Les originaux et textes extraits restent en mémoire et ne sont pas ajoutés "
            "à l'index juridique.",
            llm_limitation,
            "Le contrôle de présence des pièces est lexical ; il ne valide ni leur "
            "authenticité, ni leur complétude, ni leur conformité juridique.",
            "Les références retrouvées et les résultats doivent être vérifiés par un "
            "professionnel qualifié.",
        ],
    }
