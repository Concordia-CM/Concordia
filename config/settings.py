"""Configuration applicative explicite, chargée depuis l'environnement."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = PROJECT_ROOT / "data" / "knowledge_base" / "concordia.sqlite3"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5:3b"


@dataclass(frozen=True)
class Settings:
    """Paramètres du prototype et modèle Ollama local de démarrage."""

    database_path: Path = DEFAULT_DATABASE
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    ollama_base_url: str = DEFAULT_OLLAMA_URL
    ollama_model: str | None = DEFAULT_OLLAMA_MODEL
    llm_timeout_seconds: float = 120.0

    def __post_init__(self) -> None:
        if not self.embedding_model.strip():
            raise ValueError("CONCORDIA_EMBEDDING_MODEL ne peut pas être vide.")
        if not self.ollama_base_url.strip():
            raise ValueError("CONCORDIA_OLLAMA_BASE_URL ne peut pas être vide.")
        parsed_url = urlsplit(self.ollama_base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError("CONCORDIA_OLLAMA_BASE_URL doit être une URL HTTP ou HTTPS valide.")
        if parsed_url.username is not None or parsed_url.password is not None:
            raise ValueError("Les identifiants ne doivent pas être intégrés à l'URL Ollama.")
        if self.ollama_model is not None and not self.ollama_model.strip():
            raise ValueError("CONCORDIA_OLLAMA_MODEL doit être omis ou non vide.")
        if self.llm_timeout_seconds <= 0:
            raise ValueError("CONCORDIA_LLM_TIMEOUT_SECONDS doit être strictement positif.")

    @property
    def llm_enabled(self) -> bool:
        return self.ollama_model is not None

    def require_ollama_model(self) -> str:
        if self.ollama_model is None:
            raise RuntimeError(
                "Aucun modèle génératif n'est configuré. Définissez "
                "CONCORDIA_OLLAMA_MODEL ou restaurez la valeur par défaut."
            )
        return self.ollama_model

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        values = os.environ if environ is None else environ
        timeout_value = values.get("CONCORDIA_LLM_TIMEOUT_SECONDS", "120")
        try:
            timeout = float(timeout_value)
        except ValueError as error:
            raise ValueError("CONCORDIA_LLM_TIMEOUT_SECONDS doit être un nombre.") from error

        model_value = values.get("CONCORDIA_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL).strip()
        return cls(
            database_path=Path(
                values.get("CONCORDIA_DATABASE_PATH", str(DEFAULT_DATABASE))
            ).expanduser(),
            embedding_model=values.get(
                "CONCORDIA_EMBEDDING_MODEL",
                DEFAULT_EMBEDDING_MODEL,
            ).strip(),
            ollama_base_url=values.get(
                "CONCORDIA_OLLAMA_BASE_URL",
                DEFAULT_OLLAMA_URL,
            ).rstrip("/"),
            ollama_model=model_value or None,
            llm_timeout_seconds=timeout,
        )


def get_settings() -> Settings:
    """Retourne la configuration chargée depuis les variables d'environnement."""
    return Settings.from_env()