from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from config.settings import DEFAULT_OLLAMA_MODEL, DEFAULT_OLLAMA_URL, Settings
from src.agents.contracts import AgentInput, AgentResult, SourceReference, SourcedClaim
from src.agents.institutional_agent import InstitutionalAgent
from src.agents.legal_policy_agent import LegalPolicyAgent
from src.knowledge.index import KnowledgeBase
from src.policy.legal_policy import LegalPolicyGuard


class SettingsTests(unittest.TestCase):
    def test_ollama_uses_the_lightweight_default_and_can_be_disabled(self) -> None:
        settings = Settings()

        self.assertEqual(settings.ollama_base_url, DEFAULT_OLLAMA_URL)
        self.assertEqual(settings.require_ollama_model(), DEFAULT_OLLAMA_MODEL)
        self.assertTrue(settings.llm_enabled)
        disabled = Settings.from_env({"CONCORDIA_OLLAMA_MODEL": ""})
        self.assertFalse(disabled.llm_enabled)
        with self.assertRaisesRegex(RuntimeError, "CONCORDIA_OLLAMA_MODEL"):
            disabled.require_ollama_model()

    def test_loads_an_explicit_ollama_model_and_timeout(self) -> None:
        settings = Settings.from_env(
            {
                "CONCORDIA_OLLAMA_BASE_URL": "http://localhost:11434/",
                "CONCORDIA_OLLAMA_MODEL": "qwen2.5:3b",
                "CONCORDIA_LLM_TIMEOUT_SECONDS": "45",
                "CONCORDIA_DATABASE_PATH": "~/concordia.sqlite3",
            }
        )

        self.assertTrue(settings.llm_enabled)
        self.assertEqual(settings.require_ollama_model(), "qwen2.5:3b")
        self.assertEqual(settings.ollama_base_url, "http://localhost:11434")
        self.assertEqual(settings.llm_timeout_seconds, 45)
        self.assertEqual(settings.database_path, Path.home() / "concordia.sqlite3")

    def test_rejects_invalid_endpoint_timeout_and_empty_model(self) -> None:
        with self.assertRaisesRegex(ValueError, "URL HTTP ou HTTPS"):
            Settings(ollama_base_url="file:///tmp/ollama")
        with self.assertRaisesRegex(ValueError, "strictement positif"):
            Settings(llm_timeout_seconds=0)
        with self.assertRaisesRegex(ValueError, "doit être un nombre"):
            Settings.from_env({"CONCORDIA_LLM_TIMEOUT_SECONDS": "fast"})
        with self.assertRaisesRegex(ValueError, "omis ou non vide"):
            Settings(ollama_model=" ")


class AgentContractTests(unittest.TestCase):
    def test_agent_input_requires_request_id_and_task(self) -> None:
        with self.assertRaisesRegex(ValueError, "request_id"):
            AgentInput(request_id=" ", task="rechercher une règle")
        with self.assertRaisesRegex(ValueError, "task"):
            AgentInput(request_id="request-1", task=" ")


class LegalPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        processed = self.root / "processed"
        processed.mkdir()
        record = {
            "record_id": "test-law",
            "document_title": "Loi test",
            "source_file": "law.pdf",
            "sections": [
                {
                    "section_id": "article-7",
                    "article_number": "7",
                    "content": "Toute société est immatriculée au registre du commerce.",
                }
            ],
        }
        (processed / "law.json").write_text(json.dumps(record), encoding="utf-8")
        self.knowledge_base = KnowledgeBase(self.root / "index.sqlite3")
        self.knowledge_base.build(
            processed,
            self.root / "missing-decisions.jsonl",
            self.root / "missing-chunks.jsonl",
        )
        self.guard = LegalPolicyGuard(self.knowledge_base)
        self.source = SourceReference(
            record_id="test-law",
            section_id="article-7",
            citation="Loi test — article 7 — law.pdf",
            text="Toute société est immatriculée au registre du commerce.",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_verified_citation_still_requires_human_legal_review(self) -> None:
        result = AgentResult(
            role="legal_search",
            status="completed",
            summary="Une disposition traite de l'immatriculation.",
            sources=(self.source,),
            claims=(SourcedClaim("La société doit être immatriculée.", (self.source.key,)),),
        )

        outcome = self.guard.evaluate(result)

        self.assertEqual(outcome.decision, "human_review_required")
        self.assertEqual(outcome.verified_source_count, 1)
        self.assertEqual(outcome.findings[-1].rule_id, "P-HUMAN-REVIEW")

    def test_uncited_claim_is_blocked(self) -> None:
        result = AgentResult(
            role="legal_search",
            status="completed",
            summary="Une affirmation sans citation.",
            claims=(SourcedClaim("La société doit être immatriculée.", ()),),
        )

        outcome = self.guard.evaluate(result)

        self.assertEqual(outcome.decision, "blocked")
        self.assertIn(
            "P-CLAIM-CITATION-REQUIRED",
            {finding.rule_id for finding in outcome.findings},
        )

    def test_unknown_reference_is_blocked(self) -> None:
        fabricated_source = SourceReference(
            record_id="missing-law",
            section_id="article-999",
            citation="Loi inventée — article 999",
            text="Texte non présent dans l'index.",
        )
        result = AgentResult(
            role="legal_search",
            status="completed",
            summary="Une affirmation à vérifier.",
            sources=(fabricated_source,),
            claims=(
                SourcedClaim(
                    "La règle s'applique.",
                    (fabricated_source.key,),
                ),
            ),
        )

        outcome = self.guard.evaluate(result)

        self.assertEqual(outcome.decision, "blocked")
        self.assertIn("P-SOURCE-EXISTS", {finding.rule_id for finding in outcome.findings})

    def test_existing_section_with_fabricated_citation_is_blocked(self) -> None:
        fabricated_source = SourceReference(
            record_id="test-law",
            section_id="article-7",
            citation="Loi inventée — article 999",
            text="Toute société est immatriculée au registre du commerce.",
        )
        result = AgentResult(
            role="legal_search",
            status="completed",
            summary="Une affirmation à vérifier.",
            sources=(fabricated_source,),
        )

        outcome = self.guard.evaluate(result)

        self.assertEqual(outcome.decision, "blocked")
        self.assertIn("P-SOURCE-EXISTS", {finding.rule_id for finding in outcome.findings})

    def test_no_source_is_held_for_review_not_approved(self) -> None:
        result = AgentResult(
            role="legal_search",
            status="needs_review",
            summary="Aucun passage correspondant n'a été trouvé.",
        )

        outcome = self.guard.evaluate(result)

        self.assertEqual(outcome.decision, "human_review_required")
        self.assertIn("P-SOURCE-REQUIRED", {finding.rule_id for finding in outcome.findings})

    def test_legal_agent_routes_generated_claims_through_policy(self) -> None:
        class FakeOllamaClient:
            def generate_claims(
                self,
                question: str,
                sources: tuple[SourceReference, ...],
            ) -> tuple[SourcedClaim, ...]:
                if question != "société immatriculée":
                    raise AssertionError("L'agent a transmis une question inattendue.")
                return (
                    SourcedClaim(
                        "La société doit être immatriculée.",
                        (sources[0].key,),
                    ),
                )

        answer = LegalPolicyAgent(
            self.knowledge_base,
            ollama_client=FakeOllamaClient(),
        ).answer("société immatriculée", use_llm=True)

        self.assertEqual(answer["answer_mode"], "ollama_rag")
        self.assertEqual(answer["source_scope"], "legal_texts")
        self.assertIn("Sources :", answer["answer"])
        self.assertEqual(answer["policy"]["decision"], "human_review_required")
        self.assertEqual(answer["policy"]["verified_source_count"], 1)

    def test_legal_agent_blocks_unknown_generated_source_before_rendering(self) -> None:
        class InvalidReferenceClient:
            def generate_claims(
                self,
                question: str,
                sources: tuple[SourceReference, ...],
            ) -> tuple[SourcedClaim, ...]:
                del question, sources
                return (SourcedClaim("Affirmation non vérifiable.", (("absent", "section"),)),)

        answer = LegalPolicyAgent(
            self.knowledge_base,
            ollama_client=InvalidReferenceClient(),
        ).answer("société immatriculée", use_llm=True)

        self.assertEqual(answer["answer_mode"], "policy_blocked")
        self.assertEqual(answer["sources"], [])
        self.assertEqual(answer["policy"]["decision"], "blocked")

    def test_institutional_agent_returns_sourced_analysis_and_requires_review(self) -> None:
        answer = InstitutionalAgent(self.knowledge_base).analyze(
            question="société immatriculée",
            institution="Autorité de supervision",
            mandate="Examiner les obligations de déclaration.",
            jurisdiction="Cameroun",
        )

        self.assertEqual(answer["agent_result"]["role"], "institutional")
        self.assertEqual(answer["agent_result"]["status"], "completed")
        self.assertEqual(len(answer["agent_result"]["sources"]), 1)
        self.assertIn("pas une position officielle", " ".join(
            answer["agent_result"]["uncertainties"]
        ))
        self.assertEqual(answer["policy"]["decision"], "human_review_required")

    def test_institutional_agent_requires_explicit_mandate_and_valid_top_k(self) -> None:
        with self.assertRaisesRegex(ValueError, "top_k"):
            InstitutionalAgent(self.knowledge_base, top_k=0)
        with self.assertRaisesRegex(ValueError, "mandate"):
            InstitutionalAgent(self.knowledge_base).analyze(
                "question", "institution", " "
            )

    def test_institutional_generation_includes_its_declared_scope(self) -> None:
        class FakeInstitutionalClient:
            prompt = ""

            def generate_claims(
                self,
                question: str,
                sources: tuple[SourceReference, ...],
            ) -> tuple[SourcedClaim, ...]:
                self.prompt = question
                return (
                    SourcedClaim("Le texte prévoit une immatriculation.", (sources[0].key,)),
                )

        client = FakeInstitutionalClient()
        answer = InstitutionalAgent(
            self.knowledge_base,
            ollama_client=client,
        ).analyze(
            question="société immatriculée",
            institution="Autorité de supervision",
            mandate="Examiner les obligations de déclaration.",
            jurisdiction="Cameroun",
            use_llm=True,
        )

        self.assertIn("Autorité de supervision", client.prompt)
        self.assertIn("Examiner les obligations de déclaration", client.prompt)
        self.assertIn("Cameroun", client.prompt)
        self.assertIn(
            "Le texte prévoit une immatriculation.",
            answer["agent_result"]["summary"],
        )
        self.assertEqual(answer["policy"]["decision"], "human_review_required")
