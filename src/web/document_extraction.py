"""Extraction de texte confidentiel en mémoire, sans sauvegarde des fichiers."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePath

import fitz

MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
MAX_TOTAL_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_PDF_PAGES = 200
_OCR_NATIVE_TEXT_MIN_CHARS = 250
_ALLOWED_SUFFIXES = {".pdf", ".docx"}


@dataclass(frozen=True)
class ExtractedDocument:
    name: str
    text: str
    page_count: int
    ocr_pages: tuple[int, ...] = ()
    warnings: tuple[str, ...] = ()


def extract_document(name: str, content: bytes) -> ExtractedDocument:
    """Extrait PDF/DOCX en mémoire et ne conserve que le texte retourné."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Le nom du document ne peut pas être vide.")
    if not isinstance(content, bytes) or not content:
        raise ValueError(f"Le fichier {name} est vide ou invalide.")
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError(f"Le fichier {name} dépasse la limite de 20 Mio.")
    suffix = PurePath(name).suffix.casefold()
    if suffix not in _ALLOWED_SUFFIXES:
        raise ValueError(f"Format non pris en charge pour {name} (PDF ou DOCX requis).")

    if suffix == ".pdf":
        return _extract_pdf(name, content)
    return _extract_docx(name, content)


def _extract_pdf(name: str, content: bytes) -> ExtractedDocument:
    try:
        document = fitz.open(stream=content, filetype="pdf")
    except (fitz.FileDataError, RuntimeError) as error:
        raise ValueError(f"Le PDF {name} est illisible ou invalide.") from error

    with document:
        if document.needs_pass:
            raise ValueError(f"Le PDF {name} est protégé par mot de passe.")
        if document.page_count == 0:
            raise ValueError(f"Le PDF {name} ne contient aucune page.")
        if document.page_count > MAX_PDF_PAGES:
            raise ValueError(
                f"Le PDF {name} dépasse la limite de {MAX_PDF_PAGES} pages."
            )

        pages: list[str] = []
        ocr_pages: list[int] = []
        warnings: list[str] = []
        for page_number, page in enumerate(document, start=1):
            page_text = page.get_text("text", sort=True)
            if (
                len(page_text.strip()) < _OCR_NATIVE_TEXT_MIN_CHARS
                and page.get_images(full=True)
            ):
                try:
                    text_page = page.get_textpage_ocr(
                        language="fra+eng",
                        dpi=200,
                        full=True,
                    )
                    ocr_text = page.get_text(
                        "text",
                        textpage=text_page,
                        sort=True,
                    )
                    if len(ocr_text.strip()) > len(page_text.strip()):
                        page_text = ocr_text
                        ocr_pages.append(page_number)
                except (RuntimeError, OSError):
                    warnings.append(
                        f"OCR indisponible à la page {page_number} de {name}."
                    )
            pages.append(page_text)

    text = "\n\n".join(page.strip() for page in pages if page.strip()).strip()
    if not text:
        warnings.append(
            f"Aucun texte extrait de {name}; vérifier l'OCR ou la qualité du fichier."
        )
    return ExtractedDocument(
        name=name,
        text=text,
        page_count=len(pages),
        ocr_pages=tuple(ocr_pages),
        warnings=tuple(warnings),
    )


def _extract_docx(name: str, content: bytes) -> ExtractedDocument:
    try:
        from docx import Document
        from docx.opc.exceptions import PackageNotFoundError

        document = Document(BytesIO(content))
    except ImportError as error:
        raise RuntimeError(
            "La lecture des fichiers DOCX nécessite python-docx. "
            "Installez les dépendances du projet avec `pip install -r requirements.txt`."
        ) from error
    except (KeyError, OSError, PackageNotFoundError, ValueError) as error:
        raise ValueError(f"Le document Word {name} est illisible ou invalide.") from error

    parts = [paragraph.text.strip() for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    text = "\n".join(part for part in parts if part).strip()
    warnings = (
        (f"Aucun texte extrait de {name}.",)
        if not text
        else ()
    )
    return ExtractedDocument(
        name=name,
        text=text,
        page_count=0,
        warnings=warnings,
    )
