"""Interface web locale de démonstration pour les audits documentaires."""

from __future__ import annotations

import json
import sqlite3

import streamlit as st

from config.settings import get_settings
from src.knowledge.index import KnowledgeBase
from src.web.audit_workflow import audit_fingerprint, create_audit_report
from src.web.document_extraction import (
    MAX_DOCUMENT_BYTES,
    MAX_TOTAL_UPLOAD_BYTES,
    ExtractedDocument,
    extract_document,
)
from src.web.checklists import load_accounting_checklist
from src.web.policy_gap_workflow import (
    create_policy_gap_report,
    policy_gap_fingerprint,
)


_POLICY_GAP_CATEGORIES = (
    "Responsabilités et mandats",
    "Politiques et stratégies",
    "Normes et standards",
    "Capacités technologiques",
    "Lacunes législatives ou réglementaires",
    "Coordination",
    "Conflits entre objectifs",
)


def _render_policy_gap_analysis() -> None:
    st.subheader("Analyse thématique des lacunes de politique")
    st.caption(
        "Décris un problème dans un domaine lié à la conformité OHADA-CEMAC. "
        "L'analyse porte sur les lacunes du domaine ; la recherche compare les sources "
        "régionales et nationales aux cadres ou standards mondiaux pertinents de l'index."
    )
    with st.form("policy-gap-form"):
        domain = st.text_input(
            "Domaine de politique",
            key="policy-gap-domain",
            placeholder="Ex. gouvernance des données, audit, conformité financière",
            max_chars=120,
        )
        issue = st.text_area(
            "Problème ou question à examiner",
            key="policy-gap-issue",
            placeholder="Décris la lacune de politique, de normes ou de coordination.",
            max_chars=500,
        )
        categories = st.multiselect(
            "Types de lacunes à examiner",
            options=_POLICY_GAP_CATEGORIES,
            default=list(_POLICY_GAP_CATEGORIES),
            key="policy-gap-categories",
        )
        use_llm = st.checkbox(
            "Rédiger une synthèse avec le modèle Ollama configuré",
            value=False,
            key="policy-gap-use-llm",
            help=(
                "La génération peut transmettre le domaine, la problématique et les "
                "extraits retrouvés au serveur Ollama configuré."
            ),
        )
        llm_consent = st.checkbox(
            "J'autorise l'envoi de ces éléments et des extraits retrouvés au serveur "
            "Ollama configuré.",
            key="policy-gap-llm-consent",
        )
        submitted = st.form_submit_button("Rechercher les sources et analyser les lacunes")

    if submitted:
        if not domain.strip():
            st.error("Indique un domaine de politique.")
        elif not issue.strip():
            st.error("Décris le problème ou la question à examiner.")
        elif not categories:
            st.error("Sélectionne au moins un type de lacune.")
        elif use_llm and not llm_consent:
            st.error("Confirme le transfert des données avant d'activer Ollama.")
        else:
            try:
                report = create_policy_gap_report(
                    KnowledgeBase(get_settings().database_path),
                    domain,
                    issue,
                    categories,
                    use_llm=use_llm,
                )
                st.session_state["policy_gap_report"] = report
                st.session_state["policy_gap_fingerprint"] = policy_gap_fingerprint(
                    domain, issue, categories, use_llm
                )
            except (OSError, RuntimeError, sqlite3.Error, ValueError) as error:
                st.error(f"Impossible d'exécuter l'analyse documentaire : {error}")

    report = st.session_state.get("policy_gap_report")
    if not isinstance(report, dict):
        return
    current_fingerprint = policy_gap_fingerprint(
        st.session_state.get("policy-gap-domain", ""),
        st.session_state.get("policy-gap-issue", ""),
        st.session_state.get("policy-gap-categories", []),
        st.session_state.get("policy-gap-use-llm", False),
    )
    if st.session_state.get("policy_gap_fingerprint") != current_fingerprint:
        st.warning("Les paramètres ont changé. Relance la recherche pour actualiser le rapport.")
        return

    st.subheader("Résultats — validation humaine requise")
    st.write(report["answer"])
    st.caption(
        "La recherche couvre le domaine demandé et les termes de comparaison "
        "internationaux. Vérifie la portée et l'autorité de chaque source dans ses "
        "métadonnées avant de l'interpréter comme un comparateur mondial."
    )
    if report["global_comparator_count"]:
        st.success(
            f"{report['global_comparator_count']} source(s) à portée mondiale ou "
            "internationale explicite retrouvée(s) pour comparaison."
        )
    else:
        st.info(
            "Aucun comparateur mondial ou international à portée explicite n'a été "
            "retrouvé pour ce domaine dans l'index."
        )
    for group in report["retrieval_groups"]:
        group_label = (
            "Sources sur le domaine"
            if group["purpose"] == "domain_context"
            else "Résultats de la recherche comparative internationale"
        )
        st.markdown(f"**{group_label}**")
        for source_group, source_label in (
            (group["sources"], "Textes et décisions"),
            (group["doctrine_sources"], "Éclairage doctrinal non normatif"),
        ):
            if source_group:
                st.caption(source_label)
            for source in source_group:
                with st.expander(source["citation"]):
                    st.caption(
                        f"Fichier : {source['source_file']} · Domaine : "
                        f"{source['domain']} · Type : {source['entity_type']}"
                    )
                    st.write(source["excerpt"] or source["text"])
                    st.caption(
                        f"Identifiants de provenance : {source['record_id']} / "
                        f"{source['section_id']}"
                    )
                    if source.get("metadata"):
                        st.json(source["metadata"])
    st.markdown("**Trace vérifiable**")
    st.json(report["audit_trace"])
    st.caption("La trace porte sur les entrées, la recherche et les sources, pas sur une chaîne de pensée interne.")
    if st.checkbox(
        "Je choisis de télécharger une copie locale du rapport.",
        key="authorize-policy-gap-download",
    ):
        st.download_button(
            "Télécharger le rapport JSON",
            data=json.dumps(report, ensure_ascii=False, indent=2),
            file_name=f"concordia-policy-gap-{report['analysis_id']}.json",
            mime="application/json",
        )


def main() -> None:
    st.set_page_config(page_title="Concordia — Recherche et conformité", page_icon="⚖️")
    st.title("Concordia — recherche juridique et analyse de conformité")
    st.caption(
        "Prototype multi-agent d'audit et de conformité OHADA-CEMAC, avec le Cameroun "
        "comme contexte initial."
    )
    st.warning(
        "Confidentialité : les fichiers et leur texte sont traités localement en mémoire "
        "et ne sont pas ajoutés au corpus juridique. Si tu actives l'analyse Ollama, "
        "la question, le domaine, la problématique, les noms de fichiers, les faits "
        "et éléments attendus ainsi que les extraits "
        "juridiques retrouvés peuvent être transmis au serveur configuré ; la génération "
        "ne démarre que si des sources juridiques sont retrouvées. Le texte intégral des "
        "fichiers déposés n'est pas transmis. Vérifie l'adresse Ollama avant d'activer "
        "cette option. Choisis ci-dessous s'ils restent en mémoire jusqu'à la fin de la "
        "session ou s'ils sont supprimés après la revue."
    )
    st.info(
        "Ce prototype retrouve des sources et assiste l'analyse de politique ou de "
        "pièces. Il ne certifie pas la conformité et ne remplace pas un audit professionnel."
    )

    upload_version = int(st.session_state.get("upload_version", 0))
    if st.button("Effacer le rapport et les données de cette session"):
        st.session_state.clear()
        st.session_state["upload_version"] = upload_version + 1
        st.rerun()

    analysis_mode = st.radio(
        "Parcours de travail",
        options=(
            "Revue documentaire",
            "Analyse des lacunes de politique par domaine",
        ),
        horizontal=True,
        key="analysis-mode",
    )
    if analysis_mode == "Analyse des lacunes de politique par domaine":
        _render_policy_gap_analysis()
        return

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
            f"{accounting_checklist.title} — statut : {accounting_checklist.status}. "
            f"{accounting_checklist.disclaimer}"
        )
        st.caption(accounting_checklist.validation_policy)
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
    generate_analysis = True
    checklist_acknowledged = True
    with st.form("audit-form"):
        if checklist_mode == "Préparation comptable indicative":
            st.subheader("Rubriques indicatives sélectionnées")
            for control in selected_controls:
                st.markdown(f"**{control.category}**")
                st.caption(
                    "Statut : piste indicative — aucune validation experte ni source "
                    "juridique officielle associée."
                    if control.validation_status == "indicative"
                    else f"Statut : validé par {control.reviewed_by} le {control.reviewed_at}."
                )
                st.write(control.question)
                st.caption(f"Base du contrôle : {control.basis}")
                for source in control.legal_sources:
                    st.write(
                        f"Source déclarée : {source.authority} — {source.citation} "
                        f"({source.jurisdiction}, version {source.version}, "
                        f"statut {source.version_status})."
                    )
                    st.caption(
                        f"Vérifiée par {source.verified_by} le {source.verified_at}; "
                        f"fichier {source.source_file}, SHA-256 {source.source_sha256}."
                    )
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
            "Je confirme que ces documents peuvent être traités pour cet audit. "
            "Leur texte intégral n'est pas transmis à Ollama ; si l'analyse IA est activée "
            "et que des sources juridiques sont retrouvées, la question, leurs noms, les "
            "faits déclarés, les éléments attendus et les extraits retrouvés peuvent être "
            "envoyés au serveur Ollama configuré."
        )
        generate_analysis = st.checkbox(
            "Rédiger une analyse avec le modèle Ollama configuré",
            value=True,
            help=(
                "Si des sources juridiques sont retrouvées, la génération Ollama pourra "
                "transmettre la question, les noms de fichiers, les faits et éléments "
                "attendus ainsi que les passages juridiques retrouvés, pas le texte "
                "intégral des fichiers déposés. "
                "Vérifie CONCORDIA_OLLAMA_BASE_URL avant d'activer cette option ; par défaut, "
                "le serveur est attendu sur cette machine."
            ),
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
                report = create_audit_report(
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
                    use_llm=generate_analysis,
                )
                st.session_state["audit_report"] = report
                st.session_state["audit_inputs_cleared"] = False
                st.session_state["audit_fingerprint"] = audit_fingerprint(
                    documents,
                    questions,
                    ["\n".join(items) for items in expected_evidence],
                    facts_text,
                    [control.control_id for control in selected_controls],
                    generate_analysis,
                )
            except (OSError, RuntimeError, sqlite3.Error, ValueError) as error:
                st.error(f"Impossible d'exécuter la revue : {error}")

    report = st.session_state.get("audit_report")
    if isinstance(report, dict):
        current_fingerprint = audit_fingerprint(
            documents,
            questions,
            ["\n".join(items) for items in expected_evidence],
            facts_text,
            [control.control_id for control in selected_controls],
            generate_analysis,
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
                if check.get("analysis"):
                    st.markdown("**Analyse assistée par IA (à valider)**")
                    st.write(check["analysis"])
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
                    with st.expander(f"Source juridique : {source['citation']}"):
                        st.write(source["excerpt"] or source["text"])
                        st.caption(
                            f"Provenance : {source['record_id']} / "
                            f"{source['section_id']} · {source['source_file']}"
                        )
                for uncertainty in check["uncertainties"]:
                    st.caption(uncertainty)

            st.markdown("**Trace vérifiable**")
            st.json(report["audit_trace"])
            st.caption(
                "La trace présente les étapes exécutées et les références consultées, "
                "pas une chaîne de pensée interne."
            )
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
