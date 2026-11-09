"""Index plein texte local avec provenance et références juridiques."""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, Literal, Protocol

if TYPE_CHECKING:
    import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE = PROJECT_ROOT / "data" / "knowledge_base" / "concordia.sqlite3"
DEFAULT_PROCESSED_DIR = PROJECT_ROOT / "02_PROCESSED_JSON"
DEFAULT_CCJA_DOCUMENTS = DEFAULT_PROCESSED_DIR / "ccja-decisions.jsonl"
DEFAULT_CCJA_CHUNKS = DEFAULT_PROCESSED_DIR / "ccja-search-chunks.jsonl"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_MAX_CHUNK_CHARS = 1800
_EMBEDDING_BATCH_SIZE = 64
_RRF_K = 60
_FTS_RRF_WEIGHT = 2.0
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_ARTICLE_REFERENCE = re.compile(
    r"\b(?:article|art\.?)\s*(?P<number>\d+(?:[.-]\d+)*"
    r"(?:(?:\s+(?:bis|ter|quater|quinquies))|(?:er|e|ème))?"
    r"|premier|première)\b",
    re.IGNORECASE,
)
_RCCM_QUERY = re.compile(r"\brccm\b", re.IGNORECASE)
_STOP_WORDS = {
    "afin", "ainsi", "alors", "au", "aucun", "aucune", "auquel", "aussi", "autre",
    "aux", "avec", "car", "ce", "ces", "cet", "cette", "ceux", "chez", "comme",
    "comment", "dans", "de", "des", "du", "elle", "elles", "en", "entre", "est",
    "et", "eux", "fait", "font", "hors", "ici", "il", "ils", "je", "la", "le",
    "les", "leur", "leurs", "lors", "ma", "mais", "me", "mes", "moi", "mon",
    "meme", "ne", "ni", "nos", "notre", "nous", "on", "ou", "par", "pas", "peu",
    "plus", "pour", "pourquoi", "quand", "que", "quel", "quelle", "quelles",
    "quels", "qui", "quoi", "sa", "sans", "se", "ses", "si", "sous", "sur", "ta",
    "te", "tes", "toi", "ton", "tous", "tout", "toute", "toutes", "tu", "un",
    "une", "vos", "votre", "vous", "y",
}

RetrievalMode = Literal["fts", "vector", "hybrid"]
SourceScope = Literal["legal_texts", "case_law", "all"]


_SOURCE_SCOPE_PREDICATES: dict[SourceScope, str] = {
    "legal_texts": (
        "AND c.entity_type != 'CCJA_Decision' "
        "AND COALESCE("
        "json_extract(c.metadata_json, '$.document.document_category'), "
        "''"
        ") != 'doctrine_or_manual'"
    ),
    "case_law": "AND c.entity_type = 'CCJA_Decision'",
    "all": "",
}


class TextEncoder(Protocol):
    def encode(self, sentences: list[str], **kwargs: Any) -> Any: ...


def _load_text_encoder(model_name: str) -> TextEncoder:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise RuntimeError(
            "La recherche vectorielle nécessite sentence-transformers. "
            "Installez les dépendances avec `pip install -r requirements.txt`."
        ) from error
    return SentenceTransformer(model_name, device="cpu")


@dataclass(frozen=True)
class SearchHit:
    document_id: str
    record_id: str
    title: str
    source_file: str
    domain: str
    entity_type: str
    section_id: str
    section_title: str
    article_number: str
    page_start: int | None
    page_end: int | None
    source_field: str
    text: str
    excerpt: str
    metadata: dict[str, Any]
    score: float

    @property
    def citation(self) -> str:
        parts = [self.title]
        if self.article_number:
            parts.append(f"article {self.article_number}")
        elif self.section_title:
            parts.append(self.section_title)
        if self.page_start is not None:
            page = str(self.page_start)
            if self.page_end is not None and self.page_end != self.page_start:
                page += f"-{self.page_end}"
            parts.append(f"p. {page}")
        if self.source_file:
            parts.append(self.source_file)
        return " — ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "title": self.title,
            "source_file": self.source_file,
            "domain": self.domain,
            "entity_type": self.entity_type,
            "section_id": self.section_id,
            "section_title": self.section_title,
            "article_number": self.article_number,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "source_field": self.source_field,
            "text": self.text,
            "excerpt": self.excerpt,
            "citation": self.citation,
            "metadata": self.metadata,
            "score": self.score,
        }


def _json_object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clean_metadata(value: Any) -> dict[str, Any]:
    return _json_object(value)


def _split_text(text: str, max_chars: int = _MAX_CHUNK_CHARS) -> Iterator[str]:
    """Découpe le texte en segments sans perdre le contenu ni dépasser la limite."""
    for paragraph in re.split(r"\n\s*\n", text.strip()):
        remaining = " ".join(paragraph.split())
        while len(remaining) > max_chars:
            boundary = max(
                remaining.rfind(". ", 0, max_chars),
                remaining.rfind("; ", 0, max_chars),
                remaining.rfind(" ", 0, max_chars),
            )
            if boundary < max_chars // 2:
                boundary = max_chars
            piece = remaining[:boundary].strip()
            if piece:
                yield piece
            remaining = remaining[boundary:].strip()
        if remaining:
            yield remaining


def _query_expression(question: str) -> str:
    tokens = []
    seen: set[str] = set()
    for token in _TOKEN.findall(question.casefold()):
        if token in _STOP_WORDS or len(token) < 2 or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
        if len(tokens) == 16:
            break
    return " OR ".join(f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens)


def _contains_rccm_reference(text: str) -> bool:
    tokens = [
        "".join(
            character
            for character in unicodedata.normalize("NFKD", token.casefold())
            if not unicodedata.combining(character)
        )
        for token in _TOKEN.findall(text)
    ]
    joined_tokens: list[str] = []
    for token in tokens:
        if joined_tokens and (
            (joined_tokens[-1] == "commer" and token == "ce")
            or (joined_tokens[-1] == "credi" and token == "t")
        ):
            joined_tokens[-1] += token
        else:
            joined_tokens.append(token)

    if "rccm" in joined_tokens:
        return True
    for register_index, token in enumerate(joined_tokens):
        if token != "registre":
            continue
        commerce_index = next(
            (
                index
                for index in range(register_index + 1, min(register_index + 5, len(joined_tokens)))
                if joined_tokens[index] == "commerce"
            ),
            None,
        )
        if commerce_index is None:
            continue
        credit_index = next(
            (
                index
                for index in range(commerce_index + 1, min(commerce_index + 6, len(joined_tokens)))
                if joined_tokens[index] == "credit"
            ),
            None,
        )
        if credit_index is not None and any(
            joined_tokens[index] == "mobilier"
            for index in range(credit_index + 1, min(credit_index + 4, len(joined_tokens)))
        ):
            return True
    return False


def _hit_has_rccm_reference(hit: SearchHit) -> bool:
    if _contains_rccm_reference(f"{hit.title} {hit.section_title} {hit.text}"):
        return True
    hierarchy_path = hit.metadata.get("hierarchy_path", [])
    if not isinstance(hierarchy_path, list):
        return False
    hierarchy_text = " ".join(
        str(item.get("title", ""))
        for item in hierarchy_path
        if isinstance(item, dict)
    )
    return _contains_rccm_reference(hierarchy_text)


def _citation_metadata(
    metadata: dict[str, Any],
    section: dict[str, Any],
) -> dict[str, Any]:
    section_metadata = _json_object(section.get("metadata"))
    return {
        "document": metadata,
        "section": section_metadata,
        "hierarchy_path": section.get("hierarchy_path", []),
    }


def _record_chunks(
    document_id: str,
    record: dict[str, Any],
) -> Iterator[dict[str, Any]]:
    record_id = str(record.get("record_id") or record.get("case_id") or document_id)
    title = str(record.get("document_title") or record_id)
    source_file = str(record.get("source_file") or "")
    domain = str(record.get("domain") or "")
    entity_type = str(record.get("entity_type") or "")
    metadata = _clean_metadata(record.get("metadata"))
    sections = record.get("sections")

    if isinstance(sections, list) and sections:
        for section_index, section_value in enumerate(sections):
            section = _json_object(section_value)
            section_text = section.get("content")
            if not isinstance(section_text, str) or not section_text.strip():
                continue
            section_id = str(section.get("section_id") or f"section-{section_index + 1}")
            section_title = str(section.get("title") or "")
            section_metadata = _json_object(section.get("metadata"))
            for chunk_index, text in enumerate(_split_text(section_text), start=1):
                yield {
                    "document_id": document_id,
                    "record_id": record_id,
                    "title": title,
                    "source_file": source_file,
                    "domain": domain,
                    "entity_type": entity_type,
                    "section_id": section_id,
                    "section_title": section_title,
                    "article_number": str(section.get("article_number") or ""),
                    "page_start": section_metadata.get("source_page_start"),
                    "page_end": section_metadata.get("source_page_end"),
                    "source_field": "section",
                    "text": text,
                    "metadata_json": json.dumps(
                        _citation_metadata(metadata, section),
                        ensure_ascii=False,
                    ),
                    "chunk_index": chunk_index,
                }
        return

    content = record.get("content")
    if not isinstance(content, str) or not content.strip():
        return
    for chunk_index, text in enumerate(_split_text(content), start=1):
        yield {
            "document_id": document_id,
            "record_id": record_id,
            "title": title,
            "source_file": source_file,
            "domain": domain,
            "entity_type": entity_type,
            "section_id": "",
            "section_title": "",
            "article_number": "",
            "page_start": None,
            "page_end": None,
            "source_field": "content",
            "text": text,
            "metadata_json": json.dumps(
                {"document": metadata, "section": {}},
                ensure_ascii=False,
            ),
            "chunk_index": chunk_index,
        }


def _read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"JSONL invalide {path}, ligne {line_number}: {error}") from error
            if not isinstance(value, dict):
                raise ValueError(f"Enregistrement JSONL non objet : {path}, ligne {line_number}")
            yield value


def _relationship_rows(record: dict[str, Any]) -> Iterator[tuple[str, str, str, str]]:
    relationships = _json_object(record.get("relationships"))
    for relation_type, relation_values in relationships.items():
        if not isinstance(relation_values, list):
            continue
        for value in relation_values:
            relation = _json_object(value)
            if not relation:
                continue
            target_id = (
                relation.get("cited_case_id")
                or relation.get("article_number")
                or relation.get("acte_id")
                or relation.get("party_id")
                or relation.get("state_id")
                or relation.get("domain_id")
                or ""
            )
            target_label = (
                relation.get("cited_case_number")
                or relation.get("article_number")
                or relation.get("acte_id")
                or relation.get("party_name")
                or relation.get("state_name")
                or relation.get("domain_name")
                or str(target_id)
            )
            yield (
                str(relation_type),
                str(target_id),
                str(target_label),
                json.dumps(relation, ensure_ascii=False, sort_keys=True),
            )


class KnowledgeBase:
    """Construit et interroge un index SQLite plein texte et vectoriel local."""

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)
        self._encoder_cache: tuple[str, TextEncoder] | None = None
        self._vector_cache: tuple[
            tuple[int, int],
            str,
            "np.ndarray",
            "np.ndarray",
        ] | None = None

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _encoder(self, model_name: str) -> TextEncoder:
        if self._encoder_cache is None or self._encoder_cache[0] != model_name:
            self._encoder_cache = (model_name, _load_text_encoder(model_name))
        return self._encoder_cache[1]

    def build(
        self,
        processed_dir: str | Path = DEFAULT_PROCESSED_DIR,
        ccja_documents: str | Path = DEFAULT_CCJA_DOCUMENTS,
        ccja_chunks: str | Path = DEFAULT_CCJA_CHUNKS,
    ) -> dict[str, int]:
        processed_path = Path(processed_dir)
        if not processed_path.is_dir():
            raise FileNotFoundError(f"Dossier des documents introuvable : {processed_path}")
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        connection = self._connect()
        try:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    record_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id INTEGER PRIMARY KEY,
                    document_id TEXT NOT NULL REFERENCES documents(document_id),
                    record_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    section_id TEXT NOT NULL,
                    section_title TEXT NOT NULL,
                    article_number TEXT NOT NULL,
                    page_start INTEGER,
                    page_end INTEGER,
                    source_field TEXT NOT NULL,
                    text TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS chunks_document_id ON chunks(document_id);
                CREATE TABLE IF NOT EXISTS relationships (
                    source_document_id TEXT NOT NULL REFERENCES documents(document_id),
                    relation_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    target_label TEXT NOT NULL,
                    attributes_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS relationships_source
                    ON relationships(source_document_id, relation_type);
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    title, text, source_file,
                    content='chunks',
                    content_rowid='chunk_id',
                    tokenize='unicode61 remove_diacritics 2'
                );
                """
            )
            connection.execute("BEGIN")
            connection.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('delete-all')")
            connection.execute("DELETE FROM relationships")
            connection.execute("DELETE FROM chunks")
            connection.execute("DELETE FROM documents")
            document_count = 0
            chunk_count = 0
            relationship_count = 0

            def insert_record(record: dict[str, Any], document_id: str) -> None:
                nonlocal document_count, chunk_count, relationship_count
                record_id = str(record.get("record_id") or record.get("case_id") or document_id)
                title = str(record.get("document_title") or record_id)
                source_file = str(record.get("source_file") or "")
                domain = str(record.get("domain") or "")
                entity_type = str(record.get("entity_type") or "")
                metadata = _clean_metadata(record.get("metadata"))
                connection.execute(
                    """
                    INSERT OR REPLACE INTO documents
                    (document_id, record_id, title, source_file, domain, entity_type, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        record_id,
                        title,
                        source_file,
                        domain,
                        entity_type,
                        json.dumps(metadata, ensure_ascii=False),
                    ),
                )
                document_count += 1
                for chunk in _record_chunks(document_id, record):
                    connection.execute(
                        """
                        INSERT INTO chunks
                        (document_id, record_id, title, source_file, domain, entity_type,
                         section_id, section_title, article_number, page_start, page_end,
                         source_field, text, metadata_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            chunk["document_id"],
                            chunk["record_id"],
                            chunk["title"],
                            chunk["source_file"],
                            chunk["domain"],
                            chunk["entity_type"],
                            chunk["section_id"],
                            chunk["section_title"],
                            chunk["article_number"],
                            chunk["page_start"],
                            chunk["page_end"],
                            chunk["source_field"],
                            chunk["text"],
                            chunk["metadata_json"],
                        ),
                    )
                    chunk_count += 1
                for relation_type, target_id, target_label, attributes in _relationship_rows(record):
                    connection.execute(
                        """
                        INSERT INTO relationships
                        (source_document_id, relation_type, target_id, target_label, attributes_json)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (document_id, relation_type, target_id, target_label, attributes),
                    )
                    relationship_count += 1

            for path in sorted(processed_path.glob("*.json")):
                try:
                    record = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as error:
                    raise ValueError(f"Document JSON invalide {path}: {error}") from error
                if not isinstance(record, dict):
                    raise ValueError(f"Le document JSON doit être un objet : {path}")
                insert_record(record, f"json:{path.stem}")

            ccja_docs_path = Path(ccja_documents)
            ccja_chunks_path = Path(ccja_chunks)
            ccja_metadata: dict[str, dict[str, Any]] = {}
            if ccja_docs_path.is_file():
                for record in _read_jsonl(ccja_docs_path):
                    case_id = str(record.get("case_id") or record.get("record_id") or "")
                    if not case_id:
                        raise ValueError(f"Identifiant CCJA absent dans {ccja_docs_path}")
                    document_id = f"ccja:{case_id}"
                    ccja_metadata[case_id] = record
                    indexed_record = dict(record)
                    if ccja_chunks_path.is_file():
                        indexed_record["content"] = ""
                    insert_record(indexed_record, document_id)

            if ccja_chunks_path.is_file():
                for chunk_number, chunk in enumerate(_read_jsonl(ccja_chunks_path), start=1):
                    case_id = str(chunk.get("case_id") or "")
                    text = chunk.get("text")
                    if not case_id or not isinstance(text, str) or not text.strip():
                        raise ValueError(
                            f"Segment CCJA incomplet dans {ccja_chunks_path}, "
                            f"enregistrement {chunk_number}"
                        )
                    document_id = f"ccja:{case_id}"
                    record = ccja_metadata.get(case_id)
                    if record is None:
                        metadata = _clean_metadata(chunk.get("metadata"))
                        case_number = str(metadata.get("case_number") or case_id)
                        record = {
                            "record_id": case_id,
                            "case_id": case_id,
                            "document_title": f"Arrêt CCJA n° {case_number}",
                            "source_file": str(metadata.get("source") or ""),
                            "domain": "OHADA",
                            "entity_type": "CCJA_Decision",
                            "metadata": metadata,
                            "content": "",
                        }
                        ccja_metadata[case_id] = record
                        insert_record(record, document_id)
                    metadata = _clean_metadata(chunk.get("metadata"))
                    connection.execute(
                        """
                        INSERT INTO chunks
                        (document_id, record_id, title, source_file, domain, entity_type,
                         section_id, section_title, article_number, page_start, page_end,
                         source_field, text, metadata_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', NULL, NULL, ?, ?, ?)
                        """,
                        (
                            document_id,
                            case_id,
                            str(record.get("document_title") or case_id),
                            str(record.get("source_file") or ""),
                            str(record.get("domain") or "OHADA"),
                            str(record.get("entity_type") or "CCJA_Decision"),
                            str(chunk.get("chunk_id") or ""),
                            str(chunk.get("source_field") or ""),
                            str(chunk.get("source_field") or "full_text"),
                            text,
                            json.dumps(
                                {"document": _clean_metadata(record.get("metadata")), "chunk": metadata},
                                ensure_ascii=False,
                            ),
                        ),
                    )
                    chunk_count += 1

            connection.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('rebuild')")
            connection.commit()
            self._vector_cache = None
            return {
                "documents": document_count,
                "chunks": chunk_count,
                "relationships": relationship_count,
            }
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def build_vectors(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> dict[str, Any]:
        """Calcule et stocke des embeddings locaux pour les passages indexés."""
        if not model_name.strip():
            raise ValueError("Le nom du modèle d'embeddings ne peut pas être vide.")
        if not self.database_path.is_file():
            raise FileNotFoundError(
                f"Index introuvable : {self.database_path}. "
                "Construisez-le avec la commande build-index."
            )

        import numpy as np

        encoder = self._encoder(model_name)
        connection = self._connect()
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chunk_embeddings (
                    chunk_id INTEGER PRIMARY KEY REFERENCES chunks(chunk_id) ON DELETE CASCADE,
                    model_name TEXT NOT NULL,
                    dimension INTEGER NOT NULL CHECK (dimension > 0),
                    vector BLOB NOT NULL
                )
                """
            )
            connection.execute("BEGIN")
            connection.execute("DELETE FROM chunk_embeddings")
            cursor = connection.execute(
                """
                SELECT chunk_id, title, section_title, text
                FROM chunks
                ORDER BY chunk_id
                """
            )
            embedded_count = 0
            dimension: int | None = None
            while rows := cursor.fetchmany(_EMBEDDING_BATCH_SIZE):
                passages = [
                    f"{row['title']} {row['section_title']}\n{row['text']}".strip()
                    for row in rows
                ]
                vectors = np.asarray(
                    encoder.encode(
                        passages,
                        batch_size=_EMBEDDING_BATCH_SIZE,
                        convert_to_numpy=True,
                        show_progress_bar=False,
                    ),
                    dtype=np.float32,
                )
                if vectors.ndim != 2 or vectors.shape[0] != len(rows) or vectors.shape[1] < 1:
                    raise ValueError("Le modèle a retourné des vecteurs de dimensions invalides.")
                if not np.isfinite(vectors).all():
                    raise ValueError("Le modèle a retourné des vecteurs non finis.")
                norms = np.linalg.norm(vectors, axis=1, keepdims=True)
                if np.any(norms == 0):
                    raise ValueError("Le modèle a retourné un vecteur nul.")
                vectors = vectors / norms
                if dimension is not None and vectors.shape[1] != dimension:
                    raise ValueError("Le modèle a retourné des dimensions incohérentes.")
                dimension = int(vectors.shape[1])
                connection.executemany(
                    """
                    INSERT INTO chunk_embeddings (chunk_id, model_name, dimension, vector)
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        (row["chunk_id"], model_name, dimension, vector.tobytes())
                        for row, vector in zip(rows, vectors, strict=True)
                    ],
                )
                embedded_count += len(rows)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        self._vector_cache = None
        return {"model": model_name, "chunks": embedded_count}

    def search(
        self,
        question: str,
        limit: int = 5,
        retrieval_mode: RetrievalMode = "fts",
        source_scope: SourceScope = "all",
    ) -> list[SearchHit]:
        if limit < 1:
            raise ValueError("Le nombre de résultats doit être positif.")
        if retrieval_mode not in ("fts", "vector", "hybrid"):
            raise ValueError(f"Mode de recherche inconnu : {retrieval_mode}.")
        if source_scope not in _SOURCE_SCOPE_PREDICATES:
            raise ValueError(f"Périmètre de sources inconnu : {source_scope}.")
        if not question.strip():
            return []
        if retrieval_mode == "fts":
            return self._search_fts(question, limit, source_scope)

        vector_hits = self._search_vectors(question, limit, source_scope)
        if retrieval_mode == "vector":
            return vector_hits
        fts_hits = self._search_fts(question, limit, source_scope)
        fused: dict[tuple[str, str, str, str], tuple[SearchHit, float]] = {}
        for weight, hits in ((_FTS_RRF_WEIGHT, fts_hits), (1.0, vector_hits)):
            for rank, hit in enumerate(hits, start=1):
                identity = (hit.document_id, hit.section_id, hit.source_field, hit.text)
                previous = fused.get(identity)
                fused[identity] = (
                    hit,
                    (previous[1] if previous else 0.0) + weight / (_RRF_K + rank),
                )
        return [
            replace(hit, score=score)
            for hit, score in sorted(
                fused.values(),
                key=lambda item: item[1],
                reverse=True,
            )[:limit]
        ]

    def _search_fts(
        self,
        question: str,
        limit: int,
        source_scope: SourceScope,
    ) -> list[SearchHit]:
        expression = _query_expression(question)
        if not expression:
            return []
        if not self.database_path.is_file():
            raise FileNotFoundError(
                f"Index introuvable : {self.database_path}. "
                "Construisez-le avec la commande build-index."
            )

        connection = self._connect()
        try:
            article_match = _ARTICLE_REFERENCE.search(question)
            article_number = article_match.group("number") if article_match else None
            article_filter = "AND lower(c.article_number) = lower(?)" if article_number else ""
            source_filter = _SOURCE_SCOPE_PREDICATES[source_scope]
            candidate_limit = (
                max(limit * 60, 300)
                if _RCCM_QUERY.search(question)
                else max(limit * 30, 100)
            )
            parameters: tuple[Any, ...] = (expression, article_number, candidate_limit)
            if article_number is None:
                parameters = (expression, candidate_limit)
            rows = connection.execute(
                f"""
                SELECT c.*, bm25(chunks_fts, 5.0, 1.0, 0.2) AS score,
                       snippet(chunks_fts, 1, '【', '】', '…', 40) AS excerpt
                FROM chunks_fts
                JOIN chunks AS c ON c.chunk_id = chunks_fts.rowid
                WHERE chunks_fts MATCH ?
                {article_filter}
                {source_filter}
                ORDER BY score
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        finally:
            connection.close()

        hits = [
            SearchHit(
                document_id=row["document_id"],
                record_id=row["record_id"],
                title=row["title"],
                source_file=row["source_file"],
                domain=row["domain"],
                entity_type=row["entity_type"],
                section_id=row["section_id"],
                section_title=row["section_title"],
                article_number=row["article_number"],
                page_start=row["page_start"],
                page_end=row["page_end"],
                source_field=row["source_field"],
                text=row["text"],
                excerpt=row["excerpt"],
                metadata=json.loads(row["metadata_json"]),
                score=row["score"],
            )
            for row in rows
        ]
        if _RCCM_QUERY.search(question):
            hits = [hit for hit in hits if _hit_has_rccm_reference(hit)]
        if article_number is None:
            query_terms = {
                term
                for term in _TOKEN.findall(question.casefold())
                if term not in _STOP_WORDS and len(term) > 1
            }

            def relevance(hit: SearchHit) -> tuple[int, int, float, int, float]:
                searchable = unicodedata.normalize(
                    "NFKD",
                    f"{hit.title} {hit.section_title} {hit.text}".casefold(),
                )
                searchable = "".join(
                    character
                    for character in searchable
                    if not unicodedata.combining(character)
                )
                matched = sum(
                    1
                    for term in query_terms
                    if "".join(
                        character
                        for character in unicodedata.normalize("NFKD", term)
                        if not unicodedata.combining(character)
                    )
                    in searchable
                )
                coverage = matched / len(query_terms) if query_terms else 0.0
                hierarchy_path = hit.metadata.get("hierarchy_path", [])
                hierarchy_text = " ".join(
                    str(item.get("title", ""))
                    for item in hierarchy_path
                    if isinstance(item, dict)
                ) if isinstance(hierarchy_path, list) else ""
                normalized_hierarchy = unicodedata.normalize(
                    "NFKD", hierarchy_text.casefold()
                ).replace("’", "'")
                person_registration_section = any(
                    isinstance(item, dict)
                    and item.get("type") == "Section"
                    and unicodedata.normalize(
                        "NFKD", str(item.get("title", "")).casefold()
                    ).startswith("immatriculation des personnes")
                    for item in hierarchy_path
                ) if isinstance(hierarchy_path, list) else False
                registration_depth = 0
                if (
                    _RCCM_QUERY.search(question)
                    and _contains_rccm_reference(hierarchy_text)
                    and "immatricul" in normalized_hierarchy
                ):
                    registration_depth = (
                        3
                        if person_registration_section
                        else 2
                        if "conditions de l'immatriculation" in normalized_hierarchy
                        else 1
                    )
                return (
                    registration_depth,
                    int(bool(hit.article_number)),
                    coverage,
                    matched,
                    -hit.score,
                )

            hits.sort(key=relevance, reverse=True)
        return hits[:limit]

    def _search_vectors(
        self,
        question: str,
        limit: int,
        source_scope: SourceScope,
    ) -> list[SearchHit]:
        if not self.database_path.is_file():
            raise FileNotFoundError(
                f"Index introuvable : {self.database_path}. "
                "Construisez-le avec la commande build-index."
            )

        import numpy as np

        database_stat = self.database_path.stat()
        stamp = (database_stat.st_mtime_ns, database_stat.st_size)
        if self._vector_cache is None or self._vector_cache[0] != stamp:
            connection = self._connect()
            try:
                table = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'chunk_embeddings'"
                ).fetchone()
                if table is None:
                    raise RuntimeError(
                        "Aucun index vectoriel trouvé. Reconstruisez l'index avec "
                        f"`build-index --vector-model {DEFAULT_EMBEDDING_MODEL}`."
                    )
                configurations = connection.execute(
                    "SELECT DISTINCT model_name, dimension FROM chunk_embeddings"
                ).fetchall()
                if len(configurations) != 1:
                    raise RuntimeError(
                        "Index vectoriel absent ou incohérent. Reconstruisez-le avec "
                        "`build-index --vector-model`."
                    )
                model_name = configurations[0]["model_name"]
                dimension = configurations[0]["dimension"]
                rows = connection.execute(
                    """
                    SELECT chunk_id, vector, dimension
                    FROM chunk_embeddings
                    WHERE model_name = ?
                    ORDER BY chunk_id
                    """,
                    (model_name,),
                ).fetchall()
            finally:
                connection.close()
            if not rows or any(row["dimension"] != dimension for row in rows):
                raise RuntimeError("L'index vectoriel est vide ou contient des dimensions invalides.")
            chunk_ids = np.fromiter(
                (row["chunk_id"] for row in rows),
                dtype=np.int64,
                count=len(rows),
            )
            vectors = np.vstack(
                [np.frombuffer(row["vector"], dtype=np.float32) for row in rows]
            )
            if vectors.shape != (len(rows), dimension):
                raise RuntimeError("Les vecteurs stockés ne correspondent pas aux dimensions déclarées.")
            self._vector_cache = (stamp, model_name, chunk_ids, vectors)

        _, model_name, chunk_ids, vectors = self._vector_cache
        query = np.asarray(
            self._encoder(model_name).encode(
                [question],
                convert_to_numpy=True,
                show_progress_bar=False,
            ),
            dtype=np.float32,
        )
        if query.shape != (1, vectors.shape[1]) or not np.isfinite(query).all():
            raise ValueError("Le modèle a retourné un vecteur de requête invalide.")
        query_norm = np.linalg.norm(query[0])
        if query_norm == 0:
            raise ValueError("Le modèle a retourné un vecteur de requête nul.")
        similarities = vectors @ (query[0] / query_norm)
        candidate_limit = max(limit * 30, 100) if _RCCM_QUERY.search(question) else limit

        connection = self._connect()
        try:
            article_match = _ARTICLE_REFERENCE.search(question)
            allowed_ids: set[int] | None = None
            if article_match is not None:
                matching_rows = connection.execute(
                    "SELECT chunk_id FROM chunks WHERE lower(article_number) = lower(?)",
                    (article_match.group("number"),),
                ).fetchall()
                allowed_ids = {row["chunk_id"] for row in matching_rows}
            source_filter = _SOURCE_SCOPE_PREDICATES[source_scope]
            if source_filter:
                scoped_rows = connection.execute(
                    f"SELECT c.chunk_id FROM chunks AS c WHERE 1=1 {source_filter}"
                ).fetchall()
                scoped_ids = {row["chunk_id"] for row in scoped_rows}
                allowed_ids = (
                    scoped_ids
                    if allowed_ids is None
                    else allowed_ids.intersection(scoped_ids)
                )
            ordered_indices = np.argsort(-similarities, kind="stable")
            selected = []
            for index in ordered_indices:
                chunk_id = int(chunk_ids[index])
                if allowed_ids is not None and chunk_id not in allowed_ids:
                    continue
                selected.append((chunk_id, float(similarities[index])))
                if len(selected) == candidate_limit:
                    break
            if not selected:
                return []
            placeholders = ",".join("?" for _ in selected)
            rows = connection.execute(
                f"""
                SELECT * FROM chunks
                WHERE chunk_id IN ({placeholders})
                """,
                tuple(chunk_id for chunk_id, _ in selected),
            ).fetchall()
        finally:
            connection.close()

        rows_by_id = {row["chunk_id"]: row for row in rows}
        hits = []
        for chunk_id, score in selected:
            row = rows_by_id[chunk_id]
            hits.append(
                SearchHit(
                    document_id=row["document_id"],
                    record_id=row["record_id"],
                    title=row["title"],
                    source_file=row["source_file"],
                    domain=row["domain"],
                    entity_type=row["entity_type"],
                    section_id=row["section_id"],
                    section_title=row["section_title"],
                    article_number=row["article_number"],
                    page_start=row["page_start"],
                    page_end=row["page_end"],
                    source_field=row["source_field"],
                    text=row["text"],
                    excerpt=row["text"][:300],
                    metadata=json.loads(row["metadata_json"]),
                    score=score,
                )
            )
        if _RCCM_QUERY.search(question):
            hits = [hit for hit in hits if _contains_rccm_reference(
                f"{hit.title} {hit.section_title} {hit.text}"
            )]
            hits.sort(key=lambda hit: (not bool(hit.article_number), -hit.score))
        return hits[:limit]

    def related(self, record_id: str) -> list[dict[str, Any]]:
        """Retourne les relations CCJA conservées avec la décision."""
        if not self.database_path.is_file():
            raise FileNotFoundError(
                f"Index introuvable : {self.database_path}. "
                "Construisez-le avec la commande build-index."
            )
        connection = self._connect()
        try:
            return [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT r.relation_type, r.target_id, r.target_label, r.attributes_json
                    FROM relationships AS r
                    JOIN documents AS d ON d.document_id = r.source_document_id
                    WHERE d.record_id = ?
                    ORDER BY r.relation_type, r.target_label
                    """,
                    (record_id,),
                )
            ]
        finally:
            connection.close()

    def verify_source(
        self,
        record_id: str,
        section_id: str,
        citation: str,
        text: str,
    ) -> bool:
        """Vérifie l'identifiant, la citation formatée et le passage exact indexé."""
        if not all(value.strip() for value in (record_id, section_id, citation, text)):
            return False
        if not self.database_path.is_file():
            raise FileNotFoundError(
                f"Index introuvable : {self.database_path}. "
                "Construisez-le avec la commande build-index."
            )
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT title, source_file, section_title, article_number,
                       page_start, page_end, text
                FROM chunks
                WHERE record_id = ? AND section_id = ?
                """,
                (record_id, section_id),
            ).fetchall()
        finally:
            connection.close()

        for row in rows:
            parts = [row["title"]]
            if row["article_number"]:
                parts.append(f"article {row['article_number']}")
            elif row["section_title"]:
                parts.append(row["section_title"])
            if row["page_start"] is not None:
                page = str(row["page_start"])
                if row["page_end"] is not None and row["page_end"] != row["page_start"]:
                    page += f"-{row['page_end']}"
                parts.append(f"p. {page}")
            if row["source_file"]:
                parts.append(row["source_file"])
            if " — ".join(parts) == citation and row["text"] == text:
                return True
        return False


def format_documentary_answer(question: str, hits: list[SearchHit]) -> str:
    """Formate une réponse extractive, limitée aux passages effectivement retrouvés."""
    if not hits:
        return (
            "Aucun passage correspondant n'a été retrouvé dans la base indexée. "
            "Cela ne prouve pas l'absence de règle : vérifiez la couverture du corpus "
            "et reformulez la question."
        )

    passages = "\n\n".join(
        f"{index}. **{hit.citation}**\n   {hit.excerpt or hit.text[:700]}"
        for index, hit in enumerate(hits, start=1)
    )
    return (
        f"Passages documentaires retrouvés pour : « {question} »\n\n{passages}\n\n"
        "Cette réponse est une restitution extractive de l'index, pas un avis juridique. "
        "Vérifiez le texte intégral, sa version en vigueur et son applicabilité aux faits."
    )


def normalize_for_comparison(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return " ".join(
        "".join(character for character in normalized if not unicodedata.combining(character)).split()
    )
