from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.knowledge.index import KnowledgeBase, format_documentary_answer
from src.knowledge.evaluation import evaluate_retrieval, load_retrieval_cases


class KnowledgeBaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.processed_dir = self.root / "processed"
        self.processed_dir.mkdir()
        self.database_path = self.root / "index.sqlite3"
        self.knowledge_base = KnowledgeBase(self.database_path)
        self._write_document()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _write_document(self) -> None:
        record = {
            "record_id": "test-law",
            "document_title": "Loi de démonstration",
            "source_file": "loi-demo.pdf",
            "domain": "Cameroun",
            "entity_type": "Legal_Document",
            "content": "Texte complet de démonstration.",
            "metadata": {"source_sha256": "abc"},
            "sections": [
                {
                    "section_id": "article-7",
                    "entity_type": "Article",
                    "title": "Article 7",
                    "article_number": "7",
                    "content": (
                        "Toute société est immatriculée au Registre du commerce et du crédit "
                        "mobilier avant l'exercice de ses activités."
                    ),
                    "metadata": {"source_page_start": 12, "source_page_end": 13},
                }
            ],
        }
        (self.processed_dir / "test-law.json").write_text(
            json.dumps(record, ensure_ascii=False),
            encoding="utf-8",
        )

    def _build(self) -> dict[str, int]:
        return self.knowledge_base.build(
            processed_dir=self.processed_dir,
            ccja_documents=self.root / "missing-decisions.jsonl",
            ccja_chunks=self.root / "missing-chunks.jsonl",
        )

    def test_search_returns_exact_article_and_page_citation(self) -> None:
        self._build()
        hits = self.knowledge_base.search("immatriculation société registre commerce", limit=3)

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].article_number, "7")
        self.assertEqual(hits[0].page_start, 12)
        self.assertIn("article 7", hits[0].citation)
        self.assertIn("p. 12-13", hits[0].citation)
        self.assertIn("Registre du commerce", hits[0].text)

    def test_rccm_search_prioritizes_registration_hierarchy_over_mentions(self) -> None:
        commercial_law_path = (
            Path(__file__).resolve().parents[1]
            / "02_PROCESSED_JSON"
            / "ohada-acte-uniforme-2010-droit-commercial-c554eccc.json"
        )
        self.processed_dir.joinpath("test-law.json").unlink()
        shutil.copyfile(commercial_law_path, self.processed_dir / commercial_law_path.name)
        self._build()

        hits = self.knowledge_base.search(
            "Quelles dispositions concernent l'immatriculation au RCCM ?",
            limit=5,
            source_scope="legal_texts",
        )

        self.assertTrue({"44", "45", "46", "47"}.issubset(
            {hit.article_number for hit in hits}
        ))
        self.assertNotIn("257-1", {hit.article_number for hit in hits})

    def test_rebuild_is_idempotent(self) -> None:
        first = self._build()
        second = self._build()

        self.assertEqual(first, {"documents": 1, "chunks": 1, "relationships": 0})
        self.assertEqual(second, first)
        self.assertEqual(len(self.knowledge_base.search("immatriculation société", limit=10)), 1)

    def test_answer_is_explicit_about_no_generated_legal_opinion(self) -> None:
        self._build()
        answer = format_documentary_answer(
            "immatriculation société",
            self.knowledge_base.search("immatriculation société"),
        )

        self.assertIn("article 7", answer)
        self.assertIn("pas un avis juridique", answer)

    def test_missing_index_reports_build_instruction(self) -> None:
        with self.assertRaisesRegex(FileNotFoundError, "build-index"):
            self.knowledge_base.search("immatriculation")

    def test_vector_and_hybrid_retrieval_use_local_embeddings(self) -> None:
        class FakeEncoder:
            def encode(self, sentences: list[str], **kwargs: object) -> np.ndarray:
                del kwargs
                return np.asarray(
                    [
                        [1.0, 0.0]
                        if "immatriculée" in sentence.casefold()
                        or "enregistrement" in sentence.casefold()
                        else [0.0, 1.0]
                        for sentence in sentences
                    ],
                    dtype=np.float32,
                )

        self._build()
        with patch("src.knowledge.index._load_text_encoder", return_value=FakeEncoder()):
            result = self.knowledge_base.build_vectors("test-local-model")
            fts_hits = self.knowledge_base.search("enregistrement", retrieval_mode="fts")
            vector_hits = self.knowledge_base.search("enregistrement", retrieval_mode="vector")
            hybrid_hits = self.knowledge_base.search("enregistrement", retrieval_mode="hybrid")

        self.assertEqual(result, {"model": "test-local-model", "chunks": 1})
        self.assertEqual(fts_hits, [])
        self.assertEqual(vector_hits[0].article_number, "7")
        self.assertEqual(hybrid_hits[0].article_number, "7")

    def test_vector_search_requires_a_built_embedding_index(self) -> None:
        self._build()
        with self.assertRaisesRegex(RuntimeError, "Aucun index vectoriel"):
            self.knowledge_base.search("immatriculation", retrieval_mode="vector")

    def test_hybrid_search_preserves_a_strong_lexical_match(self) -> None:
        distractor = {
            "record_id": "distractor-law",
            "document_title": "Document sans terme distinctif",
            "source_file": "distractor.pdf",
            "sections": [
                {
                    "section_id": f"article-{number}",
                    "article_number": str(number),
                    "content": "Texte juridique de contenu général.",
                }
                for number in range(1, 7)
            ],
        }
        target = {
            "record_id": "target-law",
            "document_title": "Texte ciblé",
            "source_file": "target.pdf",
            "sections": [
                {
                    "section_id": "article-target",
                    "article_number": "99",
                    "content": "Disposition sur le mot distinctif zebraconcordia.",
                }
            ],
        }
        (self.processed_dir / "test-law.json").unlink()
        (self.processed_dir / "a-distractor.json").write_text(
            json.dumps(distractor, ensure_ascii=False),
            encoding="utf-8",
        )
        (self.processed_dir / "z-target.json").write_text(
            json.dumps(target, ensure_ascii=False),
            encoding="utf-8",
        )

        class IdenticalEncoder:
            def encode(self, sentences: list[str], **kwargs: object) -> np.ndarray:
                del kwargs
                return np.ones((len(sentences), 2), dtype=np.float32)

        self._build()
        with patch("src.knowledge.index._load_text_encoder", return_value=IdenticalEncoder()):
            self.knowledge_base.build_vectors("test-identical-model")
            fts_hits = self.knowledge_base.search("zebraconcordia", limit=5)
            hybrid_hits = self.knowledge_base.search(
                "zebraconcordia",
                limit=5,
                retrieval_mode="hybrid",
            )

        self.assertEqual(fts_hits[0].record_id, "target-law")
        self.assertEqual(hybrid_hits[0].record_id, "target-law")

    def test_ccja_segments_and_relationships_are_indexed(self) -> None:
        ccja_documents = self.root / "ccja-decisions.jsonl"
        ccja_chunks = self.root / "ccja-chunks.jsonl"
        ccja_documents.write_text(
            json.dumps(
                {
                    "record_id": "OHADA-CCJA-00001",
                    "case_id": "OHADA-CCJA-00001",
                    "document_title": "Arrêt CCJA n° 12/2020",
                    "source_file": "ccja.csv",
                    "domain": "OHADA",
                    "entity_type": "CCJA_Decision",
                    "content": "Texte entier non segmenté.",
                    "metadata": {"case_number": "12/2020"},
                    "relationships": {
                        "cited_articles": [{"article_number": "101"}],
                        "cited_cases": [
                            {"cited_case_id": "OHADA-CCJA-00002", "cited_case_number": "14/2020"}
                        ],
                    },
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        ccja_chunks.write_text(
            json.dumps(
                {
                    "chunk_id": "OHADA-CCJA-00001:reasoning:1",
                    "case_id": "OHADA-CCJA-00001",
                    "source_field": "reasoning",
                    "text": "Passage de motivation indexé uniquement comme segment.",
                    "metadata": {"case_number": "12/2020"},
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.knowledge_base.build(
            processed_dir=self.processed_dir,
            ccja_documents=ccja_documents,
            ccja_chunks=ccja_chunks,
        )

        hits = self.knowledge_base.search("passage motivation segment", limit=3)
        relations = self.knowledge_base.related("OHADA-CCJA-00001")
        self.assertEqual(result["relationships"], 2)
        self.assertEqual(len(hits), 1)
        self.assertIn("Arrêt CCJA n° 12/2020", hits[0].citation)
        self.assertEqual(
            {relation["relation_type"] for relation in relations},
            {"cited_articles", "cited_cases"},
        )

    def test_source_scope_separates_law_texts_doctrine_and_ccja_cases(self) -> None:
        doctrine = {
            "record_id": "doctrine-sureties",
            "document_title": "Cours de droit des sûretés OHADA",
            "source_file": "cours-suretes.pdf",
            "domain": "doctrine et manuel",
            "entity_type": "Legal_Document",
            "metadata": {"document_category": "doctrine_or_manual"},
            "sections": [
                {
                    "section_id": "section-1",
                    "content": (
                        "Dispositions concernant l'immatriculation au RCCM "
                        "pour la société."
                    ),
                    "metadata": {"document_category": "doctrine_or_manual"},
                }
            ],
        }
        ccja_documents = self.root / "ccja-decisions.jsonl"
        ccja_chunks = self.root / "ccja-chunks.jsonl"
        ccja_documents.write_text(
            json.dumps(
                {
                    "record_id": "OHADA-CCJA-00099",
                    "case_id": "OHADA-CCJA-00099",
                    "document_title": "Arrêt CCJA n° 99/2020",
                    "source_file": "ccja.csv",
                    "domain": "OHADA",
                    "entity_type": "CCJA_Decision",
                    "metadata": {},
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        ccja_chunks.write_text(
            json.dumps(
                {
                    "chunk_id": "OHADA-CCJA-00099:full_text:1",
                    "case_id": "OHADA-CCJA-00099",
                    "source_field": "full_text",
                    "text": (
                        "Dispositions concernant l'immatriculation au RCCM "
                        "pour la société."
                    ),
                    "metadata": {},
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (self.processed_dir / "doctrine.json").write_text(
            json.dumps(doctrine, ensure_ascii=False),
            encoding="utf-8",
        )
        preamble = {
            "record_id": "commercial-law-toc",
            "document_title": "Acte uniforme portant droit commercial",
            "source_file": "droit-commercial.pdf",
            "domain": "OHADA",
            "entity_type": "Legal_Document",
            "metadata": {"document_category": "legal_document"},
            "sections": [
                {
                    "section_id": "preamble",
                    "title": "Préambule",
                    "content": (
                        "RCCM — dispositions concernant les conditions de "
                        "l'immatriculation."
                    ),
                    "metadata": {"document_category": "legal_document"},
                }
            ],
        }
        (self.processed_dir / "preamble.json").write_text(
            json.dumps(preamble, ensure_ascii=False),
            encoding="utf-8",
        )
        self._build_with_ccja(ccja_documents, ccja_chunks)

        legal_hits = self.knowledge_base.search(
            "dispositions immatriculation RCCM société",
            source_scope="legal_texts",
        )
        case_hits = self.knowledge_base.search(
            "dispositions immatriculation RCCM société",
            source_scope="case_law",
        )
        all_hits = self.knowledge_base.search(
            "dispositions immatriculation RCCM société",
            source_scope="all",
        )
        class IdenticalEncoder:
            def encode(self, sentences: list[str], **kwargs: object) -> np.ndarray:
                del kwargs
                return np.ones((len(sentences), 2), dtype=np.float32)

        with patch(
            "src.knowledge.index._load_text_encoder",
            return_value=IdenticalEncoder(),
        ):
            self.knowledge_base.build_vectors("scope-test-model")
            vector_hits = self.knowledge_base.search(
                "dispositions immatriculation RCCM société",
                retrieval_mode="vector",
                source_scope="legal_texts",
            )

        self.assertTrue(legal_hits)
        self.assertIn("test-law", {hit.record_id for hit in legal_hits})
        self.assertTrue(legal_hits[0].article_number)
        self.assertTrue(all(hit.entity_type != "CCJA_Decision" for hit in legal_hits))
        self.assertTrue(
            all(
                hit.metadata["document"].get("document_category") != "doctrine_or_manual"
                for hit in legal_hits
            )
        )
        self.assertTrue(case_hits)
        self.assertTrue(all(hit.entity_type == "CCJA_Decision" for hit in case_hits))
        self.assertGreater(len(all_hits), len(legal_hits))
        self.assertTrue(vector_hits)
        self.assertTrue(
            all(hit.entity_type != "CCJA_Decision" for hit in vector_hits)
        )
        self.assertTrue(
            all(
                hit.metadata["document"].get("document_category") != "doctrine_or_manual"
                for hit in vector_hits
            )
        )

    def _build_with_ccja(self, ccja_documents: Path, ccja_chunks: Path) -> None:
        self.knowledge_base.build(
            processed_dir=self.processed_dir,
            ccja_documents=ccja_documents,
            ccja_chunks=ccja_chunks,
        )

    def test_retrieval_benchmark_reports_source_recall_and_citations(self) -> None:
        repository_root = Path(__file__).resolve().parents[1]
        corpus_dir = self.root / "verified-corpus"
        corpus_dir.mkdir()
        benchmark_path = repository_root / "data" / "evaluation" / "legal_retrieval.json"
        cases = load_retrieval_cases(benchmark_path)
        benchmark_data = json.loads(benchmark_path.read_text(encoding="utf-8"))
        corpus_files = [case["source_file"] for case in benchmark_data["cases"]]
        for filename in corpus_files:
            shutil.copyfile(
                repository_root / "02_PROCESSED_JSON" / filename,
                corpus_dir / filename,
            )
        self.knowledge_base.build(
            processed_dir=corpus_dir,
            ccja_documents=self.root / "missing-decisions.jsonl",
            ccja_chunks=self.root / "missing-chunks.jsonl",
        )
        result = evaluate_retrieval(self.knowledge_base, cases, top_k=5)

        self.assertEqual(result["case_count"], 12)
        self.assertEqual(result["hit_rate_at_k"], 1.0)
        self.assertEqual(result["mean_recall_at_k"], 1.0)
        self.assertEqual(result["mean_reciprocal_rank"], 1.0)
        self.assertEqual(result["precision_at_k"], 0.25)
        self.assertEqual(result["citation_coverage_of_retrieved_relevant"], 1.0)
        self.assertGreaterEqual(result["mean_latency_ms"], 0)
        self.assertTrue(result["cases"][2]["expected_before_distractors"])
        self.assertEqual(result["cases"][2]["relevant_ranks"], [1, 2, 4, 5])
        self.assertEqual(result["cases"][2]["distractor_ranks"], [])
        self.assertTrue(
            all(case["relevant_ranks"][0] == 1 for case in result["cases"])
        )


if __name__ == "__main__":
    unittest.main()
