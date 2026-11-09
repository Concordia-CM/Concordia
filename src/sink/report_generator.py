"""Génération locale de rapports d'audit JSON et Markdown."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_audit_report(report: dict[str, Any], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write("\n")


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Rapport d'audit — {report['title']}",
        "",
        f"- **Identifiant :** `{report['audit_id']}`",
        f"- **Juridiction :** {report['jurisdiction'] or 'Non précisée'}",
        "- **Évaluation :** revue humaine requise",
        "",
        "> Ce rapport fournit des pistes documentaires et des contrôles de pièces. "
        "Il ne conclut pas automatiquement à la conformité.",
    ]
    for event in report["events"]:
        lines.extend(["", f"## {event['sequence']}. {event['title']}", ""])
        if event["facts"]:
            lines.append("**Faits déclarés**")
            lines.extend(f"- {fact}" for fact in event["facts"])
            lines.append("")
        if event["documents_received"]:
            lines.append("**Pièces déclarées reçues**")
            lines.extend(f"- {document}" for document in event["documents_received"])
            lines.append("")
        for check in event["checks"]:
            lines.extend(
                [
                    f"### Contrôle {check['check_id'] or 'sans identifiant'}",
                    "",
                    f"**Question :** {check['question']}",
                    "",
                    f"**Constat documentaire :** `{check['finding']}`",
                    "",
                ]
            )
            policy = check.get("policy")
            if isinstance(policy, dict):
                lines.extend(
                    [
                        f"**Contrôle Policy :** `{policy['decision']}`",
                        "",
                    ]
                )
                for policy_finding in policy.get("findings", []):
                    lines.append(f"- `{policy_finding['rule_id']}` : {policy_finding['message']}")
                lines.append("")
            institutional_analysis = check.get("institutional_analysis")
            if isinstance(institutional_analysis, dict):
                institutional_result = institutional_analysis.get("agent_result", {})
                if isinstance(institutional_result, dict):
                    lines.extend(
                        [
                            "#### Perspective institutionnelle déclarée",
                            "",
                            f"- **Institution / rôle :** {institutional_analysis.get('institution', '')}",
                            f"- **Mandat fourni :** {institutional_analysis.get('mandate', '')}",
                            f"- **Contrôle Policy :** `{institutional_analysis.get('policy', {}).get('decision', 'inconnu')}`",
                            "",
                            str(institutional_result.get("summary", "")),
                            "",
                        ]
                    )
                    for uncertainty in institutional_result.get("uncertainties", []):
                        lines.append(f"- **Limite :** {uncertainty}")
                    if institutional_result.get("sources"):
                        lines.append("- **Sources institutionnelles consultées :**")
                        lines.extend(
                            f"  - {source['citation']}"
                            for source in institutional_result["sources"]
                        )
                    lines.append("")
            if check["missing_scenario_evidence"]:
                lines.append("**Pièces attendues par le scénario mais non déclarées reçues**")
                lines.extend(f"- {item}" for item in check["missing_scenario_evidence"])
                lines.append("")
            if check["sources"]:
                lines.append("**Sources retrouvées**")
                for source in check["sources"]:
                    lines.extend(
                        [
                            f"- **{source['citation']}**",
                            f"  > {source['excerpt'] or source['text'][:600]}",
                        ]
                    )
                lines.append("")
            else:
                lines.extend(
                    [
                        "**Sources retrouvées :** aucune correspondance dans l'index.",
                        "",
                    ]
                )
            lines.append("**Incertitudes et prochaines étapes**")
            lines.extend(f"- {item}" for item in check["uncertainties"])
            lines.extend(f"- {item}" for item in check["recommendations"])
            lines.append("")

    lines.extend(["## Limites", ""])
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    return "\n".join(lines).rstrip() + "\n"