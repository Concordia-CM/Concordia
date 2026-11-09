"""Interface web locale de démonstration pour les audits documentaires."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

import streamlit as st

from config.settings import get_settings
from src.agents.auditor_agent import AuditorAgent
from src.agents.legal_policy_agent import LegalPolicyAgent
from src.knowledge.index import KnowledgeBase
from src.web.document_extraction import (
    MAX_DOCUMENT_BYTES,
    MAX_TOTAL_UPLOAD_BYTES,
    ExtractedDocument,
    extract_document,
)
from src.web.checklists import ChecklistTemplate, load_accounting_checklist


def _fingerprint(
    documents: list[ExtractedDocument],
    questions: list[str],
    evidence: list[str],
    facts: str,
    checklist_control_ids: list[str] | None = None,
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
    return digest.hexdigest()


def _create_report(
    knowledge_base: KnowledgeBase,
    documents: list[ExtractedDocument],
    questions: list[str],
    evidence_lists: list[list[str]],
    facts: list[str],
    checklist: ChecklistTemplate | None = None,
    checklist_control_ids: list[str] | None = None,
) -> dict[str, object]:
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
        )
        for index, question in enumerate(questions, start=1)
    ]
    now = datetime.now(timezone.utc).isoformat()
    return {
        "audit_id": str(uuid4()),
        "title": "Revue documentaire — dossier d'entreprise OHADA",
        "jurisdiction": "Cameroun",
        "started_at": now,
        "completed_at": now,
        "assessment": "human_review_required",
        "checklist": (
            {
                "checklist_id": checklist.checklist_id,
                "title": checklist.title,
                "status": checklist.status,
                "disclaimer": checklist.disclaimer,
                "source_note": checklist.source_note,
                "controls_applied": checklist_control_ids or [],
            }
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
            for name, document in zip(document_names, documents)
        ],
        "facts_reported": facts,
        "checks": checks,
        "limitations": [
            "Les originaux et textes extraits restent en mémoire et ne sont pas ajoutés "
            "à l'index juridique ni envoyés à un service externe.",
            "Le contrôle de présence des pièces est lexical ; il ne valide ni leur "
            "authenticité, ni leur complétude, ni leur conformité juridique.",
            "Les références retrouvées et les résultats doivent être vérifiés par un "
            "professionnel qualifié.",
        ],
    }


def main() -> None:
    st.set_page_config(page_title="Concordia — Audit confidentiel", page_icon="⚖️")
    st.title("Concordia — revue documentaire")
    st.caption("Prototype local d'aide à l'audit documentaire OHADA — Cameroun.")
    st.warning(
        "Confidentialité : cette version n'envoie aucun document à Ollama ou au cloud. "
        "Les fichiers et leur texte sont traités localement en mémoire, sans écriture "
        "persistante par Concordia, et ne sont pas ajoutés au corpus juridique. "
        "Choisis ci-dessous s'ils restent en mémoire jusqu'à la fin de la session ou "
        "s'ils sont supprimés après la revue. Aucun service cloud n'est configuré."
    )
    st.info(
        "Ce prototype vérifie des éléments documentaires et retrouve des sources. "
        "Il ne certifie pas la conformité et ne remplace pas un audit professionnel."
    )

    upload_version = int(st.session_state.get("upload_version", 0))
    if st.button("Effacer le rapport et les données de cette session"):
        st.session_state.clear()
        st.session_state["upload_version"] = upload_version + 1
        st.rerun()

    uploaded_files = st.file_uploader(
        "Dépose les documents du dossier (PDF ou DOCX)",
        type=["pdf", "docx"],
        accept_multiple_files=True,
        key=f"uploaded_documents_{upload_version}",
        help=(
            "Les fichiers restent en mémoire pendant la session. Limites : "
            "20 Mio par fichier et 50 Mio au total."
        ),
    )
    if uploaded_files and st.session_state.get("audit_inputs_cleared"):
        st.session_state["audit_inputs_cleared"] = False
    documents: list[ExtractedDocument] = []
    extraction_errors: list[str] = []
    if uploaded_files:
        total_size = sum(file.size for file in uploaded_files)
        if total_size > MAX_TOTAL_UPLOAD_BYTES:
            extraction_errors.append("La taille totale des fichiers dépasse 50 Mio.")
        else:
            for uploaded_file in uploaded_files:
                if uploaded_file.size > MAX_DOCUMENT_BYTES:
                    extraction_errors.append(
                        f"{uploaded_file.name} dépasse la limite de 20 Mio."
                    )
                    continue
                try:
                    documents.append(
                        extract_document(uploaded_file.name, uploaded_file.getvalue())
                    )
                except ValueError as error:
                    extraction_errors.append(str(error))

    for error in extraction_errors:
        st.error(error)
    if documents:
        st.subheader("Documents reçus")
        for document_index, document in enumerate(documents):
            with st.expander(
                f"{document.name} — "
                f"{document.page_count} page(s)"
                if document.page_count
                else document.name
            ):
                if document.ocr_pages:
                    st.caption(f"OCR utilisé aux pages : {', '.join(map(str, document.ocr_pages))}")
                for warning in document.warnings:
                    st.warning(warning)
                st.text_area(
                    "Aperçu du texte extrait",
                    value=document.text[:5000],
                    height=160,
                    disabled=True,
                    key=f"preview-{document_index}",
                )

    try:
        accounting_checklist = load_accounting_checklist()
    except ValueError as error:
        st.error(f"Impossible de charger le modèle indicatif : {error}")
        accounting_checklist = None

    checklist_mode = st.radio(
        "Type de contrôles",
        options=("Contrôles personnalisés", "Préparation comptable indicative"),
        horizontal=True,
    )
    selected_controls = []
    if checklist_mode == "Préparation comptable indicative" and accounting_checklist:
        st.warning(
            f"{accounting_checklist.title} — brouillon non validé. "
            f"{accounting_checklist.disclaimer}"
        )
        categories = list(
            dict.fromkeys(control.category for control in accounting_checklist.controls)
        )
        selected_categories = st.multiselect(
            "Rubriques à inclure (à confirmer par le réviseur)",
            options=categories,
            default=categories,
        )
        selected_controls = [
            control
            for control in accounting_checklist.controls
            if control.category in selected_categories
        ]
    else:
        check_count = st.number_input(
            "Nombre de contrôles à effectuer",
            min_value=1,
            max_value=8,
            value=1,
            step=1,
        )
    questions: list[str] = []
    expected_evidence: list[list[str]] = []
    facts_text = ""
    checklist_acknowledged = True
    with st.form("audit-form"):
        if checklist_mode == "Préparation comptable indicative":
            st.subheader("Rubriques indicatives sélectionnées")
            for control in selected_controls:
                st.markdown(f"**{control.category}**")
                st.write(control.question)
                st.caption(
                    "Termes de repérage proposés : "
                    + ", ".join(control.expected_evidence)
                )
                questions.append(control.question)
                expected_evidence.append(list(control.expected_evidence))
            checklist_acknowledged = st.checkbox(
                "Je comprends que ce modèle est indicatif, non exhaustif et non validé "
                "juridiquement ; je confirmerai le périmètre avec un professionnel."
            )
        else:
            st.subheader("Contrôles définis par le réviseur")
            st.caption(
                "Renseigne chaque question et les éléments attendus (un par ligne). "
                "Concordia ne présume pas des obligations juridiques applicables."
            )
            for index in range(int(check_count)):
                question = st.text_input(
                    f"Question de contrôle {index + 1}",
                    key=f"question-{index}",
                )
                evidence_text = st.text_area(
                    f"Éléments documentaires attendus — contrôle {index + 1} (un par ligne)",
                    key=f"evidence-{index}",
                    height=80,
                )
                questions.append(question)
                expected_evidence.append(
                    [line.strip() for line in evidence_text.splitlines() if line.strip()]
                )
        facts_text = st.text_area(
            "Faits ou contexte fournis (facultatif, un par ligne)",
            key="audit-facts",
        )
        consent = st.checkbox(
            "Je confirme que ces documents peuvent être traités localement pour cet audit. "
            "Je comprends qu'aucune analyse cloud n'est disponible dans cette version."
        )
        submitted = st.form_submit_button("Lancer la revue documentaire")

    extracted_text = any(document.text for document in documents)
    if submitted:
        if extraction_errors:
            st.error("Corrige les fichiers signalés avant de lancer l'audit.")
        elif not documents or not extracted_text:
            st.error("Ajoute au moins un document contenant du texte exploitable.")
        elif not consent:
            st.error("Le consentement au traitement local est nécessaire pour continuer.")
        elif not checklist_acknowledged:
            st.error("Confirme la limite de la checklist indicative avant de continuer.")
        elif checklist_mode == "Préparation comptable indicative" and not selected_controls:
            st.error("Sélectionne au moins une rubrique de préparation.")
        elif any(not question.strip() for question in questions):
            st.error("Chaque contrôle doit contenir une question.")
        else:
            try:
                report = _create_report(
                    KnowledgeBase(get_settings().database_path),
                    documents,
                    [question.strip() for question in questions],
                    expected_evidence,
                    [line.strip() for line in facts_text.splitlines() if line.strip()],
                    checklist=(
                        accounting_checklist
                        if checklist_mode == "Préparation comptable indicative"
                        else None
                    ),
                    checklist_control_ids=[
                        control.control_id for control in selected_controls
                    ],
                )
                st.session_state["audit_report"] = report
                st.session_state["audit_inputs_cleared"] = False
                st.session_state["audit_fingerprint"] = _fingerprint(
                    documents,
                    questions,
                    ["\n".join(items) for items in expected_evidence],
                    facts_text,
                    [control.control_id for control in selected_controls],
                )
            except (OSError, RuntimeError, sqlite3.Error, ValueError) as error:
                st.error(f"Impossible d'exécuter la revue : {error}")

    report = st.session_state.get("audit_report")
    if isinstance(report, dict):
        current_fingerprint = _fingerprint(
            documents,
            questions,
            ["\n".join(items) for items in expected_evidence],
            facts_text,
            [control.control_id for control in selected_controls],
        )
        inputs_cleared = st.session_state.get("audit_inputs_cleared", False)
        if (
            not inputs_cleared
            and st.session_state.get("audit_fingerprint") != current_fingerprint
        ):
            st.warning("Le dossier ou les contrôles ont changé. Relance l'audit.")
        else:
            st.subheader("Résultats — revue humaine requise")
            for check in report["checks"]:
                st.markdown(f"**{check['question']}**")
                st.write(f"Constat documentaire : {check['finding']}")
                if check["evidence_found_in_documents"]:
                    st.write(
                        "Éléments retrouvés par correspondance textuelle : "
                        + ", ".join(check["evidence_found_in_documents"])
                    )
                if check["missing_scenario_evidence"]:
                    st.write(
                        "Éléments attendus non repérés : "
                        + ", ".join(check["missing_scenario_evidence"])
                    )
                for source in check["sources"]:
                    st.write(f"Source juridique : {source['citation']}")
                for uncertainty in check["uncertainties"]:
                    st.caption(uncertainty)

            st.caption(
                "Le rapport n'est pas enregistré automatiquement. Le téléchargement "
                "ci-dessous est proposé après confirmation et peut contenir les faits "
                "que tu as saisis et les noms de fichiers."
            )
            authorize_report = st.checkbox(
                "Je choisis de télécharger une copie locale du rapport pour cet audit.",
                key="authorize-report-download",
            )
            if authorize_report:
                st.download_button(
                    "Télécharger le rapport JSON",
                    data=json.dumps(report, ensure_ascii=False, indent=2),
                    file_name=f"concordia-audit-{report['audit_id']}.json",
                    mime="application/json",
                )
            st.markdown("**Conservation des originaux**")
            retention = st.radio(
                "Choisis quoi faire des documents temporaires après cette revue.",
                options=("Les garder en mémoire jusqu'à la fin de la session",
                         "Les supprimer maintenant"),
                key=f"document-retention-{report['audit_id']}",
            )
            if retention == "Les supprimer maintenant" and st.button(
                "Supprimer les documents de cette session",
                key=f"delete-documents-{report['audit_id']}",
            ):
                st.session_state["upload_version"] = upload_version + 1
                st.session_state["audit_inputs_cleared"] = True
                st.rerun()


if __name__ == "__main__":
    main()
