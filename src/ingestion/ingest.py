"""Extraction et segmentation de documents juridiques PDF."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import tempfile
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import pymupdf as fitz
except ImportError:  # Compatibilité avec les versions antérieures de PyMuPDF.
    import fitz


LOGGER = logging.getLogger(__name__)

_ARTICLE_HEADING = re.compile(
    r"^\s*(?:article\b|art\.?)\s*"
    r"(?P<number>(?:\d+(?:[.-]\d+)*(?:(?:\s+(?:bis|ter|quater|quinquies))|(?:er|e|ème))?)"
    r"|premier|première)"
    r"(?=\s|[.:;,\-–—]|$)\s*[.:;,\-–—]?\s*(?P<title>[^\n]*)$",
    re.IGNORECASE,
)
_STRUCTURE_HEADING = re.compile(
    r"^\s*(?P<kind>PARTIE|LIVRE|TITRE|CHAPITRE|SECTION|SOUS[- ]SECTION)"
    r"\s+(?P<number>préliminaire|preliminaire|"
    r"\d+(?:[.-]\d+)*(?:(?:\s+(?:bis|ter|quater))|(?:er|e|ème))?|[IVXLCDM]+)"
    r"(?=\s|[.:;,\-–—]|$)\s*[.:;,\-–—]?\s*(?P<title>[^\n]*)$",
    re.IGNORECASE,
)
_STRUCTURE_LEVELS = {
    "partie": 0,
    "livre": 1,
    "titre": 2,
    "chapitre": 3,
    "section": 4,
    "sous-section": 5,
}
_PAGE_MARKER = re.compile(r"^\s*(?:page\s+)?\d+\s*(?:/|sur|of)\s*\d+\s*$", re.IGNORECASE)
_URL = re.compile(r"https?://\S+", re.IGNORECASE)
_OCR_NATIVE_TEXT_MIN_CHARS = 250
_DOCUMENT_CHUNK_MAX_CHARS = 6000


def clean_headers_and_footers(text: str) -> str:
    """Nettoie les parasites sans supprimer les retours à la ligne utiles au découpage."""
    text = unicodedata.normalize("NFC", text)
    text = text.encode("utf-8", errors="replace").decode("utf-8")
    text = _URL.sub("", text)

    cleaned_lines = []
    for line in text.splitlines():
        line = re.sub(r"\bpage\s+\d+\s*/\s*\d+\b", "", line, flags=re.IGNORECASE)
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def _sha256_file(path: Path) -> str:
    """Calcule l'empreinte sans charger le fichier complet en mémoire."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _line_key(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip().casefold()


def _document_id(path: Path, source_hash: str) -> str:
    """Construit un nom de document lisible et stable malgré les homonymes."""
    readable_name = unicodedata.normalize("NFKD", path.stem)
    readable_name = readable_name.encode("ascii", "ignore").decode("ascii").casefold()
    readable_name = re.sub(r"[^a-z0-9]+", "-", readable_name).strip("-")
    return f"{readable_name[:80].rstrip('-') or 'document'}-{source_hash[:8]}"


def _slug(value: str) -> str:
    """Normalise une valeur pour l'insérer dans un identifiant lisible."""
    readable_value = unicodedata.normalize("NFKD", value)
    readable_value = readable_value.encode("ascii", "ignore").decode("ascii").casefold()
    return re.sub(r"[^a-z0-9]+", "-", readable_value).strip("-")


def _hierarchy_path(hierarchy: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    """Retourne la hiérarchie dans l'ordre juridique, du niveau supérieur au chapitre."""
    return [
        {
            "type": kind.replace("-", " ").title(),
            "number": details["number"],
            "title": details["title"],
        }
        for kind, details in sorted(
            hierarchy.items(),
            key=lambda item: _STRUCTURE_LEVELS[item[0]],
        )
    ]


def _hierarchy_id(hierarchy: dict[str, dict[str, str]]) -> str:
    """Produit un segment d'identifiant lisible à partir des titres et chapitres."""
    parts = [
        f"{kind}-{_slug(details['number'])}"
        for kind, details in sorted(
            hierarchy.items(),
            key=lambda item: _STRUCTURE_LEVELS[item[0]],
        )
    ]
    return "-".join(parts)


def _find_repeated_marginal_lines(doc: fitz.Document) -> set[str]:
    """Repère les lignes répétées dans les marges, en excluant les titres juridiques."""
    occurrences: Counter[str] = Counter()
    page_count = doc.page_count

    for page in doc:
        lines = [line.strip() for line in page.get_text("text", sort=True).splitlines() if line.strip()]
        margins = lines[:3] + lines[-3:]
        for line in set(margins):
            if len(line) > 160 or _ARTICLE_HEADING.match(line) or _STRUCTURE_HEADING.match(line):
                continue
            occurrences[_line_key(line)] += 1

    minimum_occurrences = max(2, math.ceil(page_count * 0.2))
    return {
        line for line, count in occurrences.items()
        if count >= minimum_occurrences
    }


def _is_edge_page_number(lines: list[str], index: int) -> bool:
    """Ne retire un numéro isolé que s'il se trouve dans la marge de la page."""
    return (
        (index < 3 or index >= len(lines) - 3)
        and bool(re.fullmatch(r"\d{1,5}", lines[index].strip()))
    )


def extract_and_clean_articles(
    pdf_path: str | os.PathLike[str],
    domain: str = "OHADA",
    source_hash: str | None = None,
) -> list[dict[str, Any]]:
    """Retourne un document JSON logique, avec ses sections structurées."""
    path = Path(pdf_path)
    if not path.is_file():
        LOGGER.warning("Fichier PDF introuvable ou inaccessible : %s", path)
        return []

    if source_hash is None:
        try:
            source_hash = _sha256_file(path)
        except OSError:
            LOGGER.exception("Impossible de calculer l'empreinte du fichier %s", path)
            return []

    file_name = path.name
    ingested_at = datetime.now(timezone.utc).isoformat()
    normalized_parts = {
        unicodedata.normalize("NFKD", part).encode("ascii", "ignore").decode("ascii").casefold()
        for part in path.parts
    }
    is_doctrine_document = any(
        "doctrine" in part or "manuel" in part
        for part in normalized_parts
    )
    records: list[dict[str, Any]] = []
    document_lines: list[str] = []
    fallback_lines: list[str] = []
    fallback_start_page = 0
    fallback_end_page = 0
    active_article: dict[str, Any] | None = None
    hierarchy: dict[str, dict[str, str]] = {}
    article_count = 0
    section_id_occurrences: Counter[str] = Counter()
    ocr_pages: set[int] = set()
    document_chunk_lines: list[str] = []
    document_chunk_size = 0
    document_chunk_start_page = 0
    document_chunk_end_page = 0
    document_chunk_title = ""
    document_chunk_ocr_pages: set[int] = set()
    document_chunk_count = 0

    try:
        with fitz.open(path) as doc:
            if doc.needs_pass:
                LOGGER.error("Le PDF est chiffré et aucun mot de passe n'a été fourni : %s", path)
                return []
            if doc.page_count == 0:
                LOGGER.warning("Le PDF ne contient aucune page : %s", path)
                return []

            page_count = doc.page_count
            repeated_lines = _find_repeated_marginal_lines(doc)

            def finish_article() -> None:
                nonlocal active_article
                if active_article is None:
                    return

                content = "\n".join(active_article.pop("_lines")).strip()
                active_article["content"] = content
                article_start = active_article["metadata"]["source_page_start"]
                article_end = active_article["metadata"]["source_page_end"]
                article_ocr_pages = sorted(
                    page for page in ocr_pages if article_start <= page <= article_end
                )
                active_article["metadata"]["ocr_used"] = bool(article_ocr_pages)
                active_article["metadata"]["ocr_pages"] = article_ocr_pages
                records.append(active_article)
                active_article = None

            def finish_document_chunk() -> None:
                nonlocal document_chunk_size, document_chunk_start_page
                nonlocal document_chunk_end_page, document_chunk_title
                nonlocal document_chunk_count, document_chunk_ocr_pages
                if not document_chunk_lines:
                    return

                document_chunk_count += 1
                records.append({
                    "section_id": f"{_document_id(path, source_hash)}-section-{document_chunk_count}",
                    "entity_type": "Document_Section",
                    "title": document_chunk_title or f"Section {document_chunk_count}",
                    "content": "\n".join(document_chunk_lines).strip(),
                    "metadata": {
                        "source_page_start": document_chunk_start_page,
                        "source_page_end": document_chunk_end_page,
                        "ocr_used": bool(document_chunk_ocr_pages),
                        "ocr_pages": sorted(document_chunk_ocr_pages),
                        "document_category": "doctrine_or_manual",
                        "hierarchy": {},
                    },
                })
                document_chunk_lines.clear()
                document_chunk_size = 0
                document_chunk_start_page = 0
                document_chunk_end_page = 0
                document_chunk_title = ""
                document_chunk_ocr_pages = set()

            for page_index, page in enumerate(doc, start=1):
                native_text = page.get_text("text", sort=True)
                page_text = native_text
                if (
                    len(native_text.strip()) < _OCR_NATIVE_TEXT_MIN_CHARS
                    and page.get_images(full=True)
                ):
                    try:
                        ocr_textpage = page.get_textpage_ocr(
                            language="fra+eng",
                            dpi=200,
                            full=True,
                        )
                        ocr_text = page.get_text("text", textpage=ocr_textpage, sort=True)
                        if len(ocr_text.strip()) > len(native_text.strip()):
                            page_text = ocr_text
                            ocr_pages.add(page_index)
                        del ocr_textpage
                    except (RuntimeError, OSError):
                        LOGGER.exception(
                            "Échec OCR de la page %d de %s ; le texte natif sera conservé",
                            page_index,
                            path,
                        )
                page_text = clean_headers_and_footers(page_text)
                lines = page_text.splitlines()

                for line_index, line in enumerate(lines):
                    if _line_key(line) in repeated_lines or _PAGE_MARKER.match(line):
                        continue
                    if _is_edge_page_number(lines, line_index):
                        continue
                    document_lines.append(line)

                    if is_doctrine_document:
                        structure_match = _STRUCTURE_HEADING.match(line)
                        if structure_match and document_chunk_lines:
                            finish_document_chunk()
                        line_size = len(line) + 1
                        if (
                            document_chunk_lines
                            and document_chunk_size + line_size > _DOCUMENT_CHUNK_MAX_CHARS
                        ):
                            finish_document_chunk()
                        if not document_chunk_lines:
                            document_chunk_start_page = page_index
                            document_chunk_title = line[:240]
                        document_chunk_lines.append(line)
                        document_chunk_size += line_size
                        document_chunk_end_page = page_index
                        if page_index in ocr_pages:
                            document_chunk_ocr_pages.add(page_index)
                        continue

                    structure_match = _STRUCTURE_HEADING.match(line)
                    if structure_match:
                        finish_article()
                        kind = structure_match.group("kind").lower().replace(" ", "-")
                        level = _STRUCTURE_LEVELS[kind]
                        hierarchy = {
                            key: value
                            for key, value in hierarchy.items()
                            if _STRUCTURE_LEVELS[key] < level
                        }
                        hierarchy[kind] = {
                            "number": structure_match.group("number").strip(),
                            "title": structure_match.group("title").strip(),
                        }
                        if article_count == 0:
                            fallback_lines.append(line)
                            if not fallback_start_page:
                                fallback_start_page = page_index
                            fallback_end_page = page_index
                        continue

                    article_match = _ARTICLE_HEADING.match(line)
                    if article_match:
                        if fallback_lines:
                            records.append({
                                "section_id": f"{_document_id(path, source_hash)}-preamble",
                                "entity_type": "Document_Preamble",
                                "title": "Préambule",
                                "content": "\n".join(fallback_lines).strip(),
                                "metadata": {
                                    "source_page_start": fallback_start_page,
                                    "source_page_end": fallback_end_page,
                                    "ocr_used": any(
                                        fallback_start_page <= page <= fallback_end_page
                                        for page in ocr_pages
                                    ),
                                    "ocr_pages": sorted(
                                        page
                                        for page in ocr_pages
                                        if fallback_start_page <= page <= fallback_end_page
                                    ),
                                    "hierarchy": {},
                                },
                            })
                            fallback_lines.clear()
                        finish_article()
                        article_count += 1
                        article_number = re.sub(
                            r"\s+", " ", article_match.group("number").strip()
                        )
                        slug = re.sub(r"[^\w.-]+", "_", article_number, flags=re.UNICODE)
                        hierarchy_id = _hierarchy_id(hierarchy)
                        section_id = (
                            f"{_document_id(path, source_hash)}-"
                            f"{hierarchy_id + '-' if hierarchy_id else ''}"
                            f"article-{slug}"
                        )
                        section_id_occurrences[section_id] += 1
                        if section_id_occurrences[section_id] > 1:
                            section_id = (
                                f"{section_id}-"
                                f"{section_id_occurrences[section_id]}"
                            )
                        record = {
                            "section_id": section_id,
                            "entity_type": "Article",
                            "title": f"Article {article_number}",
                            "article_number": article_number,
                            "hierarchy_path": _hierarchy_path(hierarchy),
                            "content": "",
                            "metadata": {
                                "standard_type": "ITU_Readiness_Record",
                                "compliance_level": "mandatory",
                                "source_sha256": source_hash,
                                "ingested_at": ingested_at,
                                "source_page_count": page_count,
                                "source_page_start": page_index,
                                "source_page_end": page_index,
                                "ocr_used": page_index in ocr_pages,
                                "ocr_pages": [page_index] if page_index in ocr_pages else [],
                                "hierarchy": {key: value.copy() for key, value in hierarchy.items()},
                            },
                            "_lines": [line],
                        }
                        active_article = record
                        continue

                    if active_article is not None:
                        active_article["_lines"].append(line)
                        active_article["metadata"]["source_page_end"] = page_index
                    elif article_count == 0:
                        fallback_lines.append(line)
                        if not fallback_start_page:
                            fallback_start_page = page_index
                        fallback_end_page = page_index

            finish_article()
            finish_document_chunk()

            if fallback_lines:
                content = "\n".join(fallback_lines).strip()
                if content:
                    records.append({
                        "section_id": f"{_document_id(path, source_hash)}-content",
                        "entity_type": "Document_Section",
                        "title": "Contenu du document",
                        "content": content,
                        "metadata": {
                            "source_page_start": fallback_start_page,
                            "source_page_end": fallback_end_page,
                            "ocr_used": any(
                                fallback_start_page <= page <= fallback_end_page
                                for page in ocr_pages
                            ),
                            "ocr_pages": sorted(
                                page
                                for page in ocr_pages
                                if fallback_start_page <= page <= fallback_end_page
                            ),
                            "hierarchy": {},
                        },
                    })
    except (fitz.FileDataError, fitz.EmptyFileError, OSError, RuntimeError):
        LOGGER.exception("Erreur lors de l'extraction du PDF %s", path)
        return []

    if not document_lines:
        LOGGER.warning("Aucun texte exploitable extrait du PDF %s", path)
        return []

    document_record = {
        "record_id": _document_id(path, source_hash),
        "document_title": re.sub(r"[_-]+", " ", path.stem).strip(),
        "source_file": file_name,
        "domain": domain,
        "entity_type": "Legal_Document",
        "content": "\n".join(document_lines).strip(),
        "sections": records,
        "metadata": {
            "standard_type": "ITU_Readiness_Record",
            "compliance_level": "mandatory",
            "source_sha256": source_hash,
            "ingested_at": ingested_at,
            "source_page_count": page_count,
            "section_count": len(records),
            "document_category": "doctrine_or_manual" if is_doctrine_document else "legal_document",
            "segmentation_strategy": (
                "document_sections" if is_doctrine_document
                else "articles" if article_count
                else "full_text"
            ),
            "ocr_used": bool(ocr_pages),
            "ocr_pages": sorted(ocr_pages),
        },
    }

    LOGGER.info(
        "Extraction terminée : %d section(s) dans le document %s",
        len(records),
        file_name,
    )
    return [document_record]


def save_processed_records(
    records: list[dict[str, Any]],
    output_dir: str | os.PathLike[str] = "02_PROCESSED_JSON",
) -> None:
    """Écrit chaque enregistrement JSON de façon atomique en UTF-8."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    for record in records:
        record_id = record.get("record_id")
        if not isinstance(record_id, str) or not record_id or Path(record_id).name != record_id:
            raise ValueError(f"Identifiant d'enregistrement invalide : {record_id!r}")

        output_path = destination / f"{record_id}.json"
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=destination,
                prefix=f".{record_id}.",
                suffix=".tmp",
                delete=False,
            ) as output_file:
                temporary_path = output_file.name
                json.dump(record, output_file, ensure_ascii=False, indent=2)
                output_file.write("\n")
                output_file.flush()
                os.fsync(output_file.fileno())
            os.replace(temporary_path, output_path)
        finally:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)


def _has_processed_output(
    record_id: str,
    source_hash: str,
    output_dir: Path,
) -> bool:
    """Vérifie qu'une sortie complète correspond à la version actuelle du PDF."""
    output_path = output_dir / f"{record_id}.json"
    if not output_path.is_file():
        return False

    try:
        with output_path.open("r", encoding="utf-8") as output_file:
            record = json.load(output_file)
    except (OSError, UnicodeError, json.JSONDecodeError):
        LOGGER.warning(
            "Sortie existante illisible, le document sera retraité : %s",
            output_path,
        )
        return False

    metadata = record.get("metadata") if isinstance(record, dict) else None
    if (
        not isinstance(record, dict)
        or record.get("record_id") != record_id
        or not isinstance(metadata, dict)
        or metadata.get("source_sha256") != source_hash
    ):
        LOGGER.warning(
            "Sortie existante ne correspondant pas au PDF, le document sera retraité : %s",
            output_path,
        )
        return False
    return True


def main() -> None:
    """Traite récursivement les PDF du répertoire des documents bruts."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    base_raw_dir = Path("data/raw_legal_docs")
    output_dir = Path("02_PROCESSED_JSON")
    if not base_raw_dir.is_dir():
        LOGGER.error("Le dossier des documents bruts est introuvable : %s", base_raw_dir)
        return

    processed_files = 0
    skipped_files = 0
    for root, _, files in os.walk(base_raw_dir):
        for file_name in sorted(files):
            if Path(file_name).suffix.lower() != ".pdf":
                continue
            file_path = Path(root) / file_name
            try:
                source_hash = _sha256_file(file_path)
            except OSError:
                LOGGER.exception("Impossible de calculer l'empreinte du fichier %s", file_path)
                continue

            record_id = _document_id(file_path, source_hash)
            if _has_processed_output(record_id, source_hash, output_dir):
                LOGGER.info("Document déjà traité, ignoré : %s", file_path)
                skipped_files += 1
                continue

            records = extract_and_clean_articles(
                file_path,
                domain=Path(root).name,
                source_hash=source_hash,
            )
            if not records:
                continue
            try:
                save_processed_records(records, output_dir=output_dir)
            except (OSError, TypeError, ValueError):
                LOGGER.exception("Impossible de sauvegarder les enregistrements de %s", file_path)
                continue
            processed_files += 1

    LOGGER.info(
        "Pipeline terminé : %d document(s) traité(s), %d déjà traité(s) ignoré(s).",
        processed_files,
        skipped_files,
    )


if __name__ == "__main__":
    main()
