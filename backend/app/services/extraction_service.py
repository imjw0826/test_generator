import logging
import os
import shutil
from dataclasses import asdict

from sqlalchemy.orm import Session

from app.config import settings
from app.core.chapter_detector import detect_page_chapters
from app.core.chapter_outline_extractor import detect_chapter_outline_with_sonnet, fallback_chapter_outline
from app.core.pdf_parser import parse_pdf, get_page_count
from app.core.text_cleaner import clean_text, detect_headers_footers
from app.models.document import Document, DocumentStatus, PdfScope
from app.models.parsed_page import ParsedPage

logger = logging.getLogger(__name__)


def process_document(db: Session, document: Document) -> Document:
    if not os.path.exists(document.file_path):
        document.status = DocumentStatus.failed
        document.error_message = "File not found on disk."
        db.commit()
        db.refresh(document)
        raise FileNotFoundError(f"File not found: {document.file_path}")

    try:
        db.query(ParsedPage).filter(ParsedPage.document_id == document.id).delete()

        page_count = get_page_count(document.file_path)
        document.page_count = page_count

        figure_output_dir = settings.figure_path / f"document_{document.id}"
        if figure_output_dir.exists():
            shutil.rmtree(figure_output_dir)

        pages = parse_pdf(
            document.file_path,
            figure_output_dir=figure_output_dir,
            figure_url_prefix=f"{settings.figure_url_prefix}/document_{document.id}",
        )
        page_chapters = detect_page_chapters(pages)

        raw_texts = [p.raw_text for p in pages]
        headers, footers = detect_headers_footers(raw_texts)

        parsed_pages: list[ParsedPage] = []
        for page in pages:
            cleaned = clean_text(page.raw_text, headers=headers, footers=footers)
            parsed_page = ParsedPage(
                document_id=document.id,
                page_number=page.page_number,
                raw_text=page.raw_text,
                cleaned_text=cleaned,
                section_hint=page_chapters.get(page.page_number),
                figures=[asdict(figure) for figure in page.figures],
            )
            db.add(parsed_page)
            parsed_pages.append(parsed_page)

        if document.pdf_scope == PdfScope.full:
            db.flush()
            try:
                document.chapter_outline = detect_chapter_outline_with_sonnet(
                    parsed_pages,
                    document_path=document.file_path,
                )
            except Exception as e:
                logger.warning("Chapter outline detection failed for document %s: %s", document.id, e)
                document.chapter_outline = []

            # Fallback 1: heading-based outline (uses detected section headings)
            if not document.chapter_outline:
                logger.info(
                    "No TOC detected for document %s; trying heading-based fallback.", document.id
                )
                document.chapter_outline = fallback_chapter_outline(parsed_pages)

            # Fallback 2: treat the entire PDF as one selectable chapter
            if not document.chapter_outline and parsed_pages:
                logger.info(
                    "No headings detected for document %s; using whole-document fallback.", document.id
                )
                document.chapter_outline = [
                    {
                        "title": "Full Document",
                        "start_page": parsed_pages[0].page_number,
                        "end_page": parsed_pages[-1].page_number,
                        "page_label": None,
                    }
                ]
        else:
            document.chapter_outline = fallback_chapter_outline(parsed_pages)

        document.status = DocumentStatus.parsed
        document.error_message = None
        db.commit()
        db.refresh(document)
        return document

    except Exception as e:
        db.rollback()
        document.status = DocumentStatus.failed
        document.error_message = str(e)[:500]
        db.commit()
        db.refresh(document)
        raise
