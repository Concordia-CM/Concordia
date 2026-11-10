"""Client Ollama local pour générer des affirmations limitées aux sources fournies."""

from __future__ import annotations

import json
from typing import Any

import requests

from config.settings import Settings, get_settings
from src.agents.contracts import SourceReference, SourcedClaim


class OllamaClient:
    """Appelle l'API chat Ollama et exige une sortie structurée avec index de sources."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def generate_claims(
        self,
        question: str,
        sources: tuple[SourceReference, ...],
    ) -> tuple[SourcedClaim, ...]:
        if not question.strip():
            raise ValueError("La question ne peut pas être vide.")
        if not sources:
            raise ValueError("La génération juridique nécessite au moins une source.")

        model = self.settings.require_ollama_model()
        source_payload = [
            {"source_index": index, "citation": source.citation, "text": source.text}
            for index, source in enumerate(sources, start=1)
        ]
        prompt = (
            "Réponds directement à la question, en français naturel et en courts "
            "paragraphes. Utilise uniquement les règles et faits explicitement "
            "présents dans les passages juridiques fournis. Le contexte éventuel "
            "sert à comprendre la demande, pas de preuve. N'ajoute aucun fait, "
            "procédure ou obligation qui n'y figure. Si les passages ne répondent "
            "pas à la question, indique clairement cette limite et n'invente pas "
            "de réponse. Retourne un objet JSON avec une clé 'claims', tableau "
            "de paragraphes sourcés. Chaque élément contient 'text' et "
            "'source_indices', tableau non vide d'indices entiers des passages qui "
            "la soutiennent. Les indices commencent à 1 et doivent correspondre "
            "exactement aux valeurs 'source_index' fournies. Si les passages ne "
            "suffisent pas, retourne un tableau 'claims' vide. Ne présente pas "
            "une recommandation de pratique comme une obligation légale. "
            "N'invente jamais de citation.\n\n"
            f"Question : {question}\n\n"
            f"Passages : {json.dumps(source_payload, ensure_ascii=False)}"
        )
        try:
            response = requests.post(
                f"{self.settings.ollama_base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Tu es un assistant documentaire prudent. Tu ne donnes "
                                "pas d'avis juridique et tu rattaches chaque affirmation "
                                "aux seules sources fournies."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0},
                },
                timeout=self.settings.llm_timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise RuntimeError(
                f"Échec de l'appel au serveur Ollama ({self.settings.ollama_base_url}) "
                f"avec le modèle {model}: {error}"
            ) from error

        try:
            payload: Any = response.json()
            content = payload["message"]["content"]
            decoded: Any = json.loads(content)
        except (KeyError, TypeError, json.JSONDecodeError, ValueError) as error:
            raise RuntimeError("Ollama a retourné une réponse JSON invalide.") from error
        if not isinstance(decoded, dict) or not isinstance(decoded.get("claims"), list):
            raise RuntimeError("La réponse Ollama doit contenir un tableau 'claims'.")
        if not decoded["claims"]:
            return ()

        claims = []
        for index, claim in enumerate(decoded["claims"], start=1):
            if not isinstance(claim, dict):
                raise RuntimeError(f"L'affirmation Ollama {index} doit être un objet.")
            text = claim.get("text")
            source_indices = claim.get("source_indices")
            if not isinstance(text, str) or not text.strip():
                raise RuntimeError(f"L'affirmation Ollama {index} ne contient pas de texte.")
            if not isinstance(source_indices, list) or not source_indices:
                raise RuntimeError(
                    f"L'affirmation Ollama {index} ne référence aucune source."
                )
            if any(
                isinstance(source_index, bool)
                or not isinstance(source_index, int)
                or source_index < 1
                or source_index > len(sources)
                for source_index in source_indices
            ):
                raise RuntimeError(
                    f"L'affirmation Ollama {index} référence un indice de source invalide."
                )
            source_refs = tuple(
                dict.fromkeys(
                    sources[source_index - 1].key for source_index in source_indices
                )
            )
            claims.append(SourcedClaim(text=text.strip(), source_refs=source_refs))
        return tuple(claims)
