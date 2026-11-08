"""Importe le corpus des décisions CCJA et ses relations de graphe en JSONL."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterator


LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS_DIR = (
    PROJECT_ROOT
    / "data"
    / "knowledge_graphs"
    / "ccja_jurisprudence"
    / "ccja_corpus"
)
DEFAULT_CSV_PATH = DEFAULT_CORPUS_DIR / "full_dataset.csv"
DEFAULT_GRAPH_DIR = DEFAULT_CORPUS_DIR / "ohada_graph"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "02_PROCESSED_JSON" / "ccja-decisions.jsonl"
DEFAULT_CHUNKS_PATH = PROJECT_ROOT / "02_PROCESSED_JSON" / "ccja-search-chunks.jsonl"
DEFAULT_CHUNK_SIZE = 4000
DEFAULT_CHUNK_OVERLAP = 400

REQUIRED_COLUMNS = {"case_id", "case_number", "full_text"}
SEARCHABLE_FIELDS = ("full_text", "dispute_summary", "reasoning", "ruling")
RELATION_FILES = {
    "cited_articles": ("edges/case_cites_article.csv", "case_id"),
    "cited_cases": ("edges/case_cites_case.csv", "source_case_id"),
    "referenced_acts": ("edges/case_references_acte.csv", "case_id"),
    "parties": ("edges/case_involves_party.csv", "case_id"),
    "origin_states": ("edges/case_originates_from_state.csv", "case_id"),
    "classified_domains": ("edges/case_classified_as_domain.csv", "case_id"),
}
DATASET_LICENSE = "CC-BY-4.0"
DATASET_VERSION = "1.0.0"


def _read_csv(path: Path) -> Iterator[dict[str, str]]:
    """Lit un CSV UTF-8 en tolérant un éventuel BOM."""
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError(f"Le fichier CSV ne contient pas d'en-tête : {path}")
        for row in reader:
            yield {key: (value or "").strip() for key, value in row.items() if key}


def _load_graph_relations(graph_dir: Path) -> dict[str, dict[str, list[dict[str, str]]]]:
    """Charge les arêtes du graphe en les regroupant par identifiant de décision."""
    relations: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for relation_name, (relative_path, case_id_column) in RELATION_FILES.items():
        path = graph_dir / relative_path
        if not path.is_file():
            LOGGER.warning("Fichier de relations absent, ignoré : %s", path)
            continue

        for row in _read_csv(path):
            case_id = row.get(case_id_column, "")
            if not case_id:
                LOGGER.warning("Arête sans identifiant de décision dans %s", path)
                continue
            relation = {
                key: value
                for key, value in row.items()
                if key != case_id_column and value
            }
            if relation:
                relations[case_id][relation_name].append(relation)

    return relations


def _build_document(
    row: dict[str, str],
    relations: dict[str, list[dict[str, str]]],
) -> dict[str, Any]:
    """Normalise une ligne du corpus sans perdre les champs de la décision."""
    case_id = row["case_id"]
    case_number = row["case_number"]
    title = f"Arrêt CCJA n° {case_number}"
    if row.get("date"):
        title += f" du {row['date']}"

    return {
        "record_id": case_id,
        "case_id": case_id,
        "document_title": title,
        "source_file": row.get("source", "") or "full_dataset.csv",
        "domain": "OHADA",
        "entity_type": "CCJA_Decision",
        "content": row["full_text"],
        "sections": {
            "dispute_summary": row.get("dispute_summary", ""),
            "reasoning": row.get("reasoning", ""),
            "ruling": row.get("ruling", ""),
        },
        "metadata": {
            "case_id": case_id,
            "case_number": case_number,
            "date": row.get("date", ""),
            "year": row.get("year", ""),
            "legal_domain": row.get("legal_domain", ""),
            "case_type": row.get("case_type", ""),
            "jurisdiction": row.get("jurisdiction", ""),
            "formation": row.get("formation", ""),
            "plaintiff": row.get("plaintiff", ""),
            "defendant": row.get("defendant", ""),
            "articles_cited": row.get("articles_cited", ""),
            "source": row.get("source", ""),
            "source_dataset": "ohada_ccja_corpus",
            "source_dataset_version": DATASET_VERSION,
            "source_license": DATASET_LICENSE,
        },
        "relationships": relations,
    }


def _split_text(text: str, chunk_size: int, overlap: int) -> Iterator[str]:
    """Découpe un texte en segments chevauchants en privilégiant les paragraphes."""
    normalized_text = text.strip()
    if not normalized_text:
        return

    paragraphs = [
        " ".join(paragraph.split())
        for paragraph in normalized_text.splitlines()
        if paragraph.strip()
    ]
    if not paragraphs:
        paragraphs = [" ".join(normalized_text.split())]

    current = ""
    for paragraph in paragraphs:
        while len(paragraph) > chunk_size:
            if current:
                yield current
                current = current[-overlap:] if overlap else ""

            end = chunk_size
            boundary = max(
                paragraph.rfind(". ", 0, end),
                paragraph.rfind("; ", 0, end),
                paragraph.rfind(", ", 0, end),
            )
            if boundary >= chunk_size // 2:
                end = boundary + 1
            piece = paragraph[:end].strip()
            yield piece
            paragraph = paragraph[max(end - overlap, 0):].strip()

        if not paragraph:
            continue
        if current and len(current) + len(paragraph) + 1 > chunk_size:
            yield current
            current = current[-overlap:] if overlap else ""
            if current and len(current) + len(paragraph) + 1 > chunk_size:
                current = ""
        current = f"{current}\n{paragraph}".strip() if current else paragraph

    if current:
        yield current


def _build_search_chunks(
    document: dict[str, Any],
    chunk_size: int,
    overlap: int,
) -> Iterator[dict[str, Any]]:
    """Crée des segments traçables pour l'indexation plein texte ou vectorielle."""
    case_id = document["case_id"]
    metadata = document["metadata"]

    for field in SEARCHABLE_FIELDS:
        if field == "full_text":
            text = document["content"]
        else:
            text = document["sections"].get(field, "")

        for field_chunk_index, chunk_text in enumerate(
            _split_text(text, chunk_size, overlap),
            start=1,
        ):
            yield {
                "chunk_id": f"{case_id}:{field}:{field_chunk_index}",
                "case_id": case_id,
                "source_field": field,
                "chunk_index": field_chunk_index,
                "text": chunk_text,
                "metadata": {
                    "case_number": metadata["case_number"],
                    "date": metadata["date"],
                    "legal_domain": metadata["legal_domain"],
                    "jurisdiction": metadata["jurisdiction"],
                    "source": metadata["source"],
                    "source_dataset": metadata["source_dataset"],
                },
            }


def import_ccja_corpus(
    csv_path: str | os.PathLike[str] = DEFAULT_CSV_PATH,
    graph_dir: str | os.PathLike[str] = DEFAULT_GRAPH_DIR,
    output_path: str | os.PathLike[str] = DEFAULT_OUTPUT_PATH,
    chunks_path: str | os.PathLike[str] = DEFAULT_CHUNKS_PATH,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> int:
    """Produit les documents CCJA et leurs segments d'indexation en JSONL."""
    source_path = Path(csv_path)
    graph_path = Path(graph_dir)
    destination = Path(output_path)
    chunks_destination = Path(chunks_path)

    if not source_path.is_file():
        raise FileNotFoundError(f"Corpus CCJA introuvable : {source_path}")
    if chunk_size < 1:
        raise ValueError("La taille des segments doit être strictement positive.")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("Le chevauchement doit être positif et inférieur à la taille.")
    if destination.resolve() == chunks_destination.resolve():
        raise ValueError("Les fichiers de décisions et de segments doivent être distincts.")

    relation_index = _load_graph_relations(graph_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    chunks_destination.parent.mkdir(parents=True, exist_ok=True)

    temporary_path: str | None = None
    temporary_chunks_path: str | None = None
    case_ids: set[str] = set()
    imported_count = 0
    imported_chunks = 0
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as output:
            temporary_path = output.name
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=chunks_destination.parent,
                prefix=f".{chunks_destination.name}.",
                suffix=".tmp",
                delete=False,
            ) as chunks_output:
                temporary_chunks_path = chunks_output.name
                with source_path.open("r", encoding="utf-8-sig", newline="") as source:
                    reader = csv.DictReader(source)
                    if reader.fieldnames is None:
                        raise ValueError(
                            f"Le corpus CSV ne contient pas d'en-tête : {source_path}"
                        )
                    missing_columns = REQUIRED_COLUMNS.difference(reader.fieldnames)
                    if missing_columns:
                        missing = ", ".join(sorted(missing_columns))
                        raise ValueError(f"Colonnes requises absentes du corpus : {missing}")

                    for line_number, raw_row in enumerate(reader, start=2):
                        row = {
                            key: (value or "").strip()
                            for key, value in raw_row.items()
                            if key
                        }
                        case_id = row.get("case_id", "")
                        if not case_id:
                            raise ValueError(
                                f"Identifiant case_id absent à la ligne {line_number} "
                                f"de {source_path}"
                            )
                        if case_id in case_ids:
                            raise ValueError(f"case_id dupliqué dans le corpus : {case_id}")
                        if not row.get("full_text"):
                            raise ValueError(f"Texte intégral absent pour la décision {case_id}")

                        case_ids.add(case_id)
                        document = _build_document(row, relation_index.get(case_id, {}))
                        output.write(json.dumps(document, ensure_ascii=False))
                        output.write("\n")
                        imported_count += 1

                        for chunk in _build_search_chunks(document, chunk_size, chunk_overlap):
                            chunks_output.write(json.dumps(chunk, ensure_ascii=False))
                            chunks_output.write("\n")
                            imported_chunks += 1

                chunks_output.flush()
                os.fsync(chunks_output.fileno())
            output.flush()
            os.fsync(output.fileno())

        os.replace(temporary_path, destination)
        temporary_path = None
        os.replace(temporary_chunks_path, chunks_destination)
        temporary_chunks_path = None
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)
        if temporary_chunks_path and os.path.exists(temporary_chunks_path):
            os.unlink(temporary_chunks_path)

    graph_case_ids = {
        case_id for case_id in relation_index
    }
    without_graph_relations = len(case_ids - graph_case_ids)
    LOGGER.info(
        "%d décision(s) et %d segment(s) CCJA importé(s) dans %s et %s ; "
        "%d décisions sans arête de graphe.",
        imported_count,
        imported_chunks,
        destination,
        chunks_destination,
        without_graph_relations,
    )
    return imported_count


def main() -> None:
    """Point d'entrée CLI de l'importeur du corpus CCJA."""
    parser = argparse.ArgumentParser(
        description="Convertit le corpus des décisions CCJA en documents JSONL."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH, help="CSV source")
    parser.add_argument(
        "--graph-dir",
        type=Path,
        default=DEFAULT_GRAPH_DIR,
        help="Dossier ohada_graph contenant les arêtes CSV",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Fichier JSONL de sortie",
    )
    parser.add_argument(
        "--chunks-output",
        type=Path,
        default=DEFAULT_CHUNKS_PATH,
        help="Fichier JSONL des segments destinés à la recherche",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Taille maximale des segments en caractères (défaut : 4000)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=DEFAULT_CHUNK_OVERLAP,
        help="Chevauchement des segments en caractères (défaut : 400)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    count = import_ccja_corpus(
        args.csv,
        args.graph_dir,
        args.output,
        args.chunks_output,
        args.chunk_size,
        args.chunk_overlap,
    )
    LOGGER.info("Import CCJA terminé : %d décision(s).", count)


if __name__ == "__main__":
    main()
