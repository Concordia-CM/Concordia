"""Chargement validé des modèles de préparation documentaire."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


DEFAULT_ACCOUNTING_CHECKLIST = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "checklists"
    / "accounting_readiness_draft.json"
)


@dataclass(frozen=True)
class ChecklistLegalSource:
    authority: str
    citation: str
    jurisdiction: str
    source_uri: str
    record_id: str
    section_id: str
    source_file: str
    source_sha256: str
    version: str
    version_status: str
    verification_status: str
    verified_by: str
    verified_at: str

    def to_dict(self) -> dict[str, str]:
        return {
            "authority": self.authority,
            "citation": self.citation,
            "jurisdiction": self.jurisdiction,
            "source_uri": self.source_uri,
            "record_id": self.record_id,
            "section_id": self.section_id,
            "source_file": self.source_file,
            "source_sha256": self.source_sha256,
            "version": self.version,
            "version_status": self.version_status,
            "verification_status": self.verification_status,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at,
        }


@dataclass(frozen=True)
class ChecklistControl:
    control_id: str
    category: str
    question: str
    expected_evidence: tuple[str, ...]
    validation_status: str
    basis: str
    legal_sources: tuple[ChecklistLegalSource, ...]
    reviewed_by: str | None = None
    reviewed_at: str | None = None


@dataclass(frozen=True)
class ChecklistTemplate:
    checklist_id: str
    title: str
    status: str
    jurisdiction: str
    disclaimer: str
    source_note: str
    validation_policy: str
    controls: tuple[ChecklistControl, ...]

    def report_metadata(self, control_ids: list[str]) -> dict[str, Any]:
        selected_ids = set(control_ids)
        return {
            "checklist_id": self.checklist_id,
            "title": self.title,
            "status": self.status,
            "disclaimer": self.disclaimer,
            "source_note": self.source_note,
            "validation_policy": self.validation_policy,
            "controls_applied": [
                {
                    "control_id": control.control_id,
                    "validation_status": control.validation_status,
                    "basis": control.basis,
                    "reviewed_by": control.reviewed_by,
                    "reviewed_at": control.reviewed_at,
                    "legal_sources": [
                        source.to_dict() for source in control.legal_sources
                    ],
                }
                for control in self.controls
                if control.control_id in selected_ids
            ],
        }


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
        "validation_policy",
    )
    if any(
        not isinstance(payload.get(field), str) or not payload[field].strip()
        for field in required_text_fields
    ):
        raise ValueError("Le modèle de checklist contient des métadonnées manquantes.")
    if payload["status"] not in {"draft_unvalidated", "expert_validated"}:
        raise ValueError(
            "Le statut du modèle doit être draft_unvalidated ou expert_validated."
        )
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
        validation_status = value.get("validation_status")
        basis = value.get("basis")
        raw_sources = value.get("legal_sources", [])
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
        if validation_status not in {"indicative", "expert_validated"}:
            raise ValueError(
                f"Statut de validation inconnu pour le contrôle {control_id}."
            )
        if not isinstance(basis, str) or not basis.strip():
            raise ValueError(f"Le contrôle {control_id} doit indiquer sa base.")
        if not isinstance(raw_sources, list):
            raise ValueError(
                f"Les sources juridiques du contrôle {control_id} doivent être une liste."
            )
        legal_sources = tuple(
            _parse_legal_source(source, control_id)
            for source in raw_sources
        )
        reviewed_by = value.get("reviewed_by")
        reviewed_at = value.get("reviewed_at")
        if validation_status == "expert_validated":
            if (
                not isinstance(reviewed_by, str)
                or not reviewed_by.strip()
                or not isinstance(reviewed_at, str)
                or not reviewed_at.strip()
                or not legal_sources
            ):
                raise ValueError(
                    f"Le contrôle {control_id} exige un réviseur, une date et "
                    "des sources officielles avant validation."
                )
            _validate_iso_datetime(reviewed_at, f"date de revue du contrôle {control_id}")
        elif reviewed_by is not None or reviewed_at is not None:
            raise ValueError(
                f"Le contrôle indicatif {control_id} ne peut pas déclarer une revue validée."
            )
        if payload["status"] == "expert_validated" and validation_status != "expert_validated":
            raise ValueError(
                "Un modèle expert_validated ne peut contenir de contrôles indicatifs."
            )
        if validation_status == "expert_validated" and payload["status"] != "expert_validated":
            raise ValueError(
                "Un contrôle validé exige un modèle expert_validated."
            )
        seen_ids.add(control_id)
        controls.append(
            ChecklistControl(
                control_id=control_id,
                category=category,
                question=question,
                expected_evidence=tuple(evidence),
                validation_status=validation_status,
                basis=basis,
                legal_sources=legal_sources,
                reviewed_by=reviewed_by,
                reviewed_at=reviewed_at,
            )
        )
    return ChecklistTemplate(
        checklist_id=payload["checklist_id"],
        title=payload["title"],
        status=payload["status"],
        jurisdiction=payload["jurisdiction"],
        disclaimer=payload["disclaimer"],
        source_note=payload["source_note"],
        validation_policy=payload["validation_policy"],
        controls=tuple(controls),
    )


def _validate_iso_datetime(value: str, label: str) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"La {label} doit être une date ISO valide.") from error


def _parse_legal_source(value: Any, control_id: str) -> ChecklistLegalSource:
    fields = (
        "authority",
        "citation",
        "jurisdiction",
        "source_uri",
        "record_id",
        "section_id",
        "source_file",
        "source_sha256",
        "version",
        "version_status",
        "verification_status",
        "verified_by",
        "verified_at",
    )
    if not isinstance(value, dict) or any(
        not isinstance(value.get(field), str) or not value[field].strip()
        for field in fields
    ):
        raise ValueError(
            f"Chaque source du contrôle {control_id} doit avoir une provenance complète."
        )
    parsed_uri = urlsplit(value["source_uri"])
    if parsed_uri.scheme not in {"https", "http"} or not parsed_uri.netloc:
        raise ValueError(
            f"La source du contrôle {control_id} doit avoir une URL officielle."
        )
    if value["verification_status"] != "official_source_verified":
        raise ValueError(
            f"La source du contrôle {control_id} doit porter une vérification "
            "explicite de son caractère officiel."
        )
    if value["version_status"] == "unknown":
        raise ValueError(
            f"La version de la source du contrôle {control_id} doit être vérifiée."
        )
    if not re.fullmatch(r"[0-9a-f]{64}", value["source_sha256"]):
        raise ValueError(
            f"L'empreinte SHA-256 de la source du contrôle {control_id} est invalide."
        )
    _validate_iso_datetime(value["verified_at"], f"date de vérification de {control_id}")
    return ChecklistLegalSource(**{field: value[field] for field in fields})
