from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

import requests

from config.settings import Settings
from src.agents.contracts import SourceReference
from src.llm.ollama_client import OllamaClient


class OllamaClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(ollama_model="qwen2.5:3b")
        self.client = OllamaClient(self.settings)
        self.sources = (
            SourceReference(
                record_id="law-1",
                section_id="article-7",
                citation="Loi — article 7",
                text="Toute société doit être immatriculée.",
            ),
        )

    @patch("src.llm.ollama_client.requests.post")
    def test_generates_claims_referencing_only_supplied_sources(
        self,
        post: MagicMock,
    ) -> None:
        response = MagicMock()
        response.json.return_value = {
            "message": {
                "content": json.dumps(
                    {
                        "claims": [
                            {
                                "text": "La société doit être immatriculée.",
                                "source_indices": [1],
                            }
                        ]
                    },
                    ensure_ascii=False,
                )
            }
        }
        post.return_value = response

        claims = self.client.generate_claims("Quelle obligation ?", self.sources)

        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].source_refs, (("law-1", "article-7"),))
        request = post.call_args.kwargs
        self.assertEqual(request["json"]["model"], "qwen2.5:3b")
        self.assertFalse(request["json"]["stream"])
        self.assertEqual(request["timeout"], self.settings.llm_timeout_seconds)
        self.assertIn("Toute société doit être immatriculée.", request["json"]["messages"][1]["content"])
        self.assertIn('"source_index": 1', request["json"]["messages"][1]["content"])
        self.assertIn("français naturel", request["json"]["messages"][1]["content"])
        self.assertIn("N'ajoute aucun fait", request["json"]["messages"][1]["content"])

    @patch("src.llm.ollama_client.requests.post")
    def test_rejects_claims_with_unknown_source_indices(self, post: MagicMock) -> None:
        response = MagicMock()
        response.json.return_value = {
            "message": {
                "content": json.dumps(
                    {"claims": [{"text": "Affirmation.", "source_indices": [2]}]}
                )
            }
        }
        post.return_value = response

        with self.assertRaisesRegex(RuntimeError, "indice de source invalide"):
            self.client.generate_claims("Question ?", self.sources)

    @patch("src.llm.ollama_client.requests.post")
    def test_reports_ollama_connection_errors(self, post: MagicMock) -> None:
        post.side_effect = requests.ConnectionError("serveur indisponible")

        with self.assertRaisesRegex(RuntimeError, "Échec de l'appel au serveur Ollama"):
            self.client.generate_claims("Question ?", self.sources)

    def test_requires_sources_before_calling_ollama(self) -> None:
        with patch("src.llm.ollama_client.requests.post") as post:
            with self.assertRaisesRegex(ValueError, "au moins une source"):
                self.client.generate_claims("Question ?", ())
        post.assert_not_called()

    @patch("src.llm.ollama_client.requests.post")
    def test_rejects_invalid_json_from_model(self, post: MagicMock) -> None:
        response = MagicMock()
        response.json.return_value = {"message": {"content": "not-json"}}
        post.return_value = response

        with self.assertRaisesRegex(RuntimeError, "réponse JSON invalide"):
            self.client.generate_claims("Question ?", self.sources)


if __name__ == "__main__":
    unittest.main()
