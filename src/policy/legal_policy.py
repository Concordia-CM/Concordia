"""Contrôles déterministes de traçabilité avant transmission d'une sortie juridique."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.agents.contracts import AgentResult, SourceKey
from src.knowledge.index import KnowledgeBase

PolicyDecision = Literal["blocked", "human_review_required"]


@dataclass(frozen=True)
class PolicyFinding:
    rule_id: str
    message: str


@dataclass(frozen=True)
class PolicyOutcome:
    decision: PolicyDecision
    findings: tuple[PolicyFinding, ...]
    verified_source_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision,
            "findings": [
                {"rule_id": finding.rule_id, "message": finding.message}
                for finding in self.findings
            ],
            "verified_source_count": self.verified_source_count,
        }


class LegalPolicyGuard:
    """Vérifie la traçabilité, sans statuer sur la validité juridique des claims."""

    def __init__(self, knowledge_base: KnowledgeBase) -> None:
        self.knowledge_base = knowledge_base

    def evaluate(self, result: AgentResult) -> PolicyOutcome:
        findings: list[PolicyFinding] = []
        source_keys: set[SourceKey] = set()
        verified_source_count = 0

        for source in result.sources:
            if not all(
                value.strip()
                for value in (source.record_id, source.section_id, source.citation, source.text)
            ):
                findings.append(
                    PolicyFinding(
                        "P-SOURCE-COMPLETE",
                        "Une source ne contient pas tous les identifiants, citation et texte requis.",
                    )
                )
                continue
            if source.key in source_keys:
                findings.append(
                    PolicyFinding("P-SOURCE-UNIQUE", "Une source est dupliquée dans le résultat.")
                )
                continue
            source_keys.add(source.key)
            if not self.knowledge_base.verify_source(
                source.record_id,
                source.section_id,
                source.citation,
                source.text,
            ):
                findings.append(
                    PolicyFinding(
                        "P-SOURCE-EXISTS",
                        f"La citation ou le passage {source.record_id}/{source.section_id} "
                        "ne correspond pas au contenu exact de l'index.",
                    )
                )
                continue
            verified_source_count += 1

        if not result.sources:
            findings.append(
                PolicyFinding(
                    "P-SOURCE-REQUIRED",
                    "Aucune source retrouvée ; ne pas présenter le résultat comme une réponse juridique.",
                )
            )

        for claim in result.claims:
            if not claim.text.strip() or not claim.source_refs:
                findings.append(
                    PolicyFinding(
                        "P-CLAIM-CITATION-REQUIRED",
                        "Chaque affirmation doit être non vide et liée à au moins une source.",
                    )
                )
                continue
            for source_ref in claim.source_refs:
                if source_ref not in source_keys:
                    findings.append(
                        PolicyFinding(
                            "P-CLAIM-CITATION-UNKNOWN",
                            "Une affirmation référence une source absente des passages fournis.",
                        )
                    )
                    break

        blocked = any(
            finding.rule_id
            in {
                "P-SOURCE-COMPLETE",
                "P-SOURCE-UNIQUE",
                "P-SOURCE-EXISTS",
                "P-CLAIM-CITATION-REQUIRED",
                "P-CLAIM-CITATION-UNKNOWN",
            }
            for finding in findings
        )
        if not blocked:
            findings.append(
                PolicyFinding(
                    "P-HUMAN-REVIEW",
                    "La présence des références est vérifiée ; leur pertinence, "
                    "leur version et leur application exigent une revue humaine.",
                )
            )
        return PolicyOutcome(
            decision="blocked" if blocked else "human_review_required",
            findings=tuple(findings),
            verified_source_count=verified_source_count,
        )
