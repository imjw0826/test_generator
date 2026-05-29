import logging
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import settings
from app.core.candidate_detector import CandidateBlock, detect_candidates
from app.core.llm_runtime import selected_model_config
from app.core.pdf_parser import render_page_png_base64
from app.core.question_extractor import extract_questions_from_block
from app.core.question_normalizer import normalize_question_text
from app.models.document import Document, DocumentStatus
from app.models.parsed_page import ParsedPage
from app.models.question import Question

logger = logging.getLogger(__name__)

# In-memory extraction progress store: {document_id: {current, total}}
# Single-process deployment (one uvicorn worker) so this is safe.
_extraction_progress: dict[int, dict] = {}


def get_extraction_progress(document_id: int) -> dict:
    prog = _extraction_progress.get(document_id)
    if not prog:
        return {"active": False, "current": 0, "total": 0, "percent": 0}
    current, total = prog["current"], prog["total"]
    percent = round(current / total * 100) if total else 0
    return {"active": True, "current": current, "total": total, "percent": percent}


@dataclass
class ExtractedQuestionData:
    chapter: str | None
    page_number: int
    question_number: str | None
    question_text: str
    tags: list[str]
    figure_refs: list[dict]
    confidence: float


def extract_questions_for_document(
    db: Session,
    document: Document,
    selected_chapters: list[str] | None = None,
    selected_chapter_ranges: list[dict] | None = None,
) -> list[Question]:
    try:
        return _do_extract(
            db,
            document,
            selected_chapters=selected_chapters,
            selected_chapter_ranges=selected_chapter_ranges,
        )
    except Exception as e:
        _extraction_progress.pop(document.id, None)
        db.rollback()
        document.status = DocumentStatus.failed
        document.error_message = f"Extraction failed: {str(e)[:400]}"
        db.commit()
        db.refresh(document)
        raise


def _do_extract(
    db: Session,
    document: Document,
    selected_chapters: list[str] | None = None,
    selected_chapter_ranges: list[dict] | None = None,
) -> list[Question]:
    pages = (
        db.query(ParsedPage)
        .filter(ParsedPage.document_id == document.id)
        .order_by(ParsedPage.page_number)
        .all()
    )

    if not pages:
        raise ValueError("No parsed pages found. Run process first.")

    pages = _filter_pages_by_selected_chapters(
        pages,
        document,
        selected_chapters,
        selected_chapter_ranges,
    )
    if not pages:
        raise ValueError("No parsed pages found for the selected chapters.")

    figure_lookup = _build_figure_lookup(pages)
    candidates = _build_extraction_candidates(pages)
    logger.info(f"Prepared {len(candidates)} extraction page blocks for document {document.id}")

    page_images = _render_candidate_pages(document, candidates)

    total_candidates = len(candidates)
    _extraction_progress[document.id] = {"current": 0, "total": total_candidates}

    extracted_payloads: list[ExtractedQuestionData] = []
    for i, block in enumerate(candidates):
        _extraction_progress[document.id]["current"] = i + 1

        page_image = page_images.get(block.page_number)
        if settings.llm_include_page_image and not page_image:
            logger.warning(f"Skipping page {block.page_number}: page image is unavailable")
            continue

        extracted = extract_questions_from_block(
            block.text,
            block.page_number,
            page_image_base64=page_image,
        )
        for q_data in extracted:
            chapter = block.chapter_hint
            figure_refs = _resolve_figure_refs(q_data, figure_lookup)
            question_text = _clean_question_text(q_data["question_text"])
            extracted_payloads.append(ExtractedQuestionData(
                chapter=chapter,
                page_number=block.page_number,
                question_number=q_data.get("question_number"),
                question_text=question_text,
                tags=[chapter] if chapter else [],
                figure_refs=figure_refs,
                confidence=q_data.get("confidence", 0.5),
            ))

    db.query(Question).filter(Question.source_document_id == document.id).delete()

    all_questions: list[Question] = []
    for payload in extracted_payloads:
        question = Question(
            source_document_id=document.id,
            source_role=document.document_role.value,
            chapter=payload.chapter,
            page_start=payload.page_number,
            page_end=payload.page_number,
            question_number=payload.question_number,
            question_text=payload.question_text,
            normalized_question_text=normalize_question_text(payload.question_text),
            tags=payload.tags,
            figure_refs=payload.figure_refs,
            extracted_confidence=payload.confidence,
            is_active=True,
        )
        db.add(question)
        all_questions.append(question)

    document.status = DocumentStatus.extracted
    document.error_message = None
    db.commit()

    _extraction_progress.pop(document.id, None)
    logger.info(f"Extracted {len(all_questions)} questions from document {document.id}")
    return all_questions


def _filter_pages_by_selected_chapters(
    pages: list[ParsedPage],
    document: Document,
    selected_chapters: list[str] | None,
    selected_chapter_ranges: list[dict] | None = None,
) -> list[ParsedPage]:
    explicit_ranges = _normalize_selected_ranges(selected_chapter_ranges)
    if explicit_ranges:
        return _pages_for_ranges(pages, explicit_ranges)

    selected = {chapter.strip() for chapter in selected_chapters or [] if chapter.strip()}
    if not selected:
        return pages

    outline = document.chapter_outline or []
    selected_ranges: list[tuple[int, int, str]] = []
    for item in outline:
        title = str(item.get("title") or "").strip()
        if title not in selected:
            continue
        try:
            start = int(item.get("start_page"))
            end = int(item.get("end_page") or start)
        except (TypeError, ValueError):
            continue
        selected_ranges.append((start, end, title))

    if selected_ranges:
        return _pages_for_ranges(pages, selected_ranges)

    return [page for page in pages if page.section_hint in selected]


def _normalize_selected_ranges(items: list[dict] | None) -> list[tuple[int, int, str]]:
    ranges: list[tuple[int, int, str]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        try:
            start = int(item.get("start_page"))
            end = int(item.get("end_page") or start)
        except (TypeError, ValueError):
            continue
        if title and start:
            ranges.append((start, end, title))
    return ranges


def _pages_for_ranges(
    pages: list[ParsedPage],
    ranges: list[tuple[int, int, str]],
) -> list[ParsedPage]:
    filtered: list[ParsedPage] = []
    for page in pages:
        for start, end, title in ranges:
            if start <= page.page_number <= end:
                page.section_hint = title
                filtered.append(page)
                break
    return filtered


FIGURE_MARKER_PATTERN = re.compile(r'\[\[FIGURE\s+id="([^"]+)"')
FIGURE_MARKER_TEXT_PATTERN = re.compile(r"\s*\[\[FIGURE[^\]]+\]\]\s*")


def _build_figure_lookup(pages: list[ParsedPage]) -> dict[str, dict]:
    figure_lookup: dict[str, dict] = {}
    for page in pages:
        for figure in page.figures or []:
            figure_id = str(figure.get("id", ""))
            if figure_id:
                figure_lookup[figure_id] = figure
    return figure_lookup


def _resolve_figure_refs(q_data: dict, figure_lookup: dict[str, dict]) -> list[dict]:
    figure_ids = q_data.get("figure_ids") or []
    if not isinstance(figure_ids, list):
        figure_ids = []

    question_text = str(q_data.get("question_text", ""))
    figure_ids.extend(FIGURE_MARKER_PATTERN.findall(question_text))

    refs: list[dict] = []
    seen: set[str] = set()
    for figure_id in figure_ids:
        figure_id = str(figure_id)
        if figure_id in seen:
            continue
        seen.add(figure_id)
        figure = figure_lookup.get(figure_id)
        if figure:
            refs.append(figure)
    return refs


def _clean_question_text(question_text: str) -> str:
    text = FIGURE_MARKER_TEXT_PATTERN.sub("\n", question_text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _build_extraction_candidates(pages: list[ParsedPage]) -> list[CandidateBlock]:
    if settings.llm_include_page_image and selected_model_config(settings.llm_model).supports_vision:
        return [
            CandidateBlock(
                page_number=page.page_number,
                text="",
                section_hint=None,
                chapter_hint=page.section_hint,
            )
            for page in pages
        ]

    page_tuples = [(p.page_number, p.cleaned_text or p.raw_text, p.section_hint) for p in pages]
    return detect_candidates(page_tuples)


def _render_candidate_pages(document: Document, candidates) -> dict[int, str]:
    if not settings.llm_include_page_image or not selected_model_config(settings.llm_model).supports_vision:
        return {}

    page_numbers = {candidate.page_number for candidate in candidates}
    page_images: dict[int, str] = {}
    for page_number in page_numbers:
        try:
            page_images[page_number] = render_page_png_base64(
                document.file_path,
                page_number,
                zoom=settings.llm_page_image_zoom,
            )
        except Exception as e:
            logger.warning(f"Could not render page {page_number} for vision extraction: {e}")
    return page_images
