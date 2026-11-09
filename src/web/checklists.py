"""Chargement validé des modèles de préparation documentaire."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_ACCOUNTING_CHECKLIST = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "checklists"
    / "accounting_readiness_draft.json"
)


@dataclass(frozen=True)
class ChecklistControl:
    control_id: str
    category: str
    question: str
    expected_evidence: tuple[str, ...]


@dataclass(frozen=True)
class ChecklistTemplate:
    checklist_id: str
    title: str
    status: str
    jurisdiction: str
    disclaimer: str
    source_note: str
    controls: tuple[ChecklistControl, ...]


def load_accounting_checklist(
    path: str | Path = DEFAULT_ACCOUNTING_CHECKLIST,
) -> ChecklistTemplate:
    """Charge le brouillon en vérifiant sa structure avant affichage ou exécution."""
    source = Path(path)
    try:
        payload: Any = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Modèle de checklist illisible {source}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("Le modèle de checklist doit être un objet JSON.")

    required_text_fields = (
        "checklist_id",
        "title",
        "status",
        "jurisdiction",
        "disclaimer",
        "source_note",
    )
    if any(
        not isinstance(payload.get(field), str) or not payload[field].strip()
        for field in required_text_fields
    ):
        raise ValueError("Le modèle de checklist contient des métadonnées manquantes.")
    if payload["status"] != "draft_unvalidated":
        raise ValueError("Le modèle doit rester marqué draft_unvalidated.")
    raw_controls = payload.get("controls")
    if not isinstance(raw_controls, list) or not raw_controls:
        raise ValueError("Le modèle doit contenir au moins un contrôle.")

    controls = []
    seen_ids: set[str] = set()
    for index, value in enumerate(raw_controls, start=1):
        if not isinstance(value, dict):
            raise ValueError(f"Le contrôle {index} doit être un objet.")
        control_id = value.get("id")
        category = value.get("category")
        question = value.get("question")
        evidence = value.get("expected_evidence")
        if not all(
            isinstance(field, str) and field.strip()
            for field in (control_id, category, question)
        ):
            raise ValueError(f"Le contrôle {index} contient un champ texte vide.")
        if control_id in seen_ids:
            raise ValueError(f"Identifiant de contrôle dupliqué : {control_id}.")
        if (
            not isinstance(evidence, list)
            or not evidence
            or not all(isinstance(item, str) and item.strip() for item in evidence)
        ):
            raise ValueError(
                f"Le contrôle {control_id} doit fournir des pièces attendues non vides."
            )
        seen_ids.add(control_id)
        controls.append(
            ChecklistControl(
                control_id=control_id,
                category=category,
                question=question,
                expected_evidence=tuple(evidence),
            )
        )
    return ChecklistTemplate(
        checklist_id=payload["checklist_id"],
        title=payload["title"],
        status=payload["status"],
        jurisdiction=payload["jurisdiction"],
        disclaimer=payload["disclaimer"],
        source_note=payload["source_note"],
        controls=tuple(controls),
    )
