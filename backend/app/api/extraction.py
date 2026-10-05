import os

import anthropic
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.document import DocumentResponse
from app.services.document_service import get_document
from app.services.extraction_service import process_document
from app.services.question_service import extract_questions_for_document, get_extraction_progress
from app.models.document import PdfScope

router = APIRouter(prefix="/api", tags=["extraction"])


class ExtractRequest(BaseModel):
    chapters: list[str] | None = None
    chapter_ranges: list[dict] | None = None


def _require_source_file(doc) -> None:
    if not os.path.exists(doc.file_path):
        raise HTTPException(
            409,
            f"Source PDF for '{doc.original_name}' is missing on disk. Re-upload the document.",
        )


def _pdf_inspector_override(value: str | None) -> bool | None:
    """`X-PDF-Inspector: on|off` overrides PDF_STRUCTURE_ANALYSIS for one request."""
    normalized = (value or "").strip().lower()
    if normalized in {"on", "true", "1"}:
        return True
    if normalized in {"off", "false", "0"}:
        return False
    return None


def _handle_llm_error(e: Exception, action: str):
    """Convert LLM/API errors into appropriate HTTP exceptions."""
    if isinstance(e, anthropic.APIStatusError):
        msg = str(e)
        if "credit balance" in msg.lower() or "too low" in msg.lower():
            raise HTTPException(402, f"Anthropic API credits exhausted. Please add credits at console.anthropic.com/settings/billing.")
        if e.status_code == 401:
            raise HTTPException(401, "Anthropic API key is invalid or missing.")
        if e.status_code == 403:
            raise HTTPException(403, f"Anthropic API access denied: {e}")
    raise HTTPException(500, f"{action} failed: {e}")


@router.get("/documents/{document_id}/progress")
def get_progress(document_id: int):
    return get_extraction_progress(document_id)


@router.post("/documents/{document_id}/process", response_model=DocumentResponse)
def process_doc(
    document_id: int,
    db: Session = Depends(get_db),
    x_pdf_inspector: str | None = Header(default=None),
):
    doc = get_document(db, document_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    _require_source_file(doc)

    try:
        doc = process_document(db, doc, analyze_structure=_pdf_inspector_override(x_pdf_inspector))
    except Exception as e:
        _handle_llm_error(e, "Processing")

    return doc


@router.post("/documents/{document_id}/extract", response_model=DocumentResponse)
def extract_questions(
    document_id: int,
    request: ExtractRequest | None = None,
    db: Session = Depends(get_db),
):
    doc = get_document(db, document_id)
    if not doc:
        raise HTTPException(404, "Document not found.")

    if doc.status.value not in ("parsed", "extracted"):
        raise HTTPException(400, "Document must be parsed before extraction. Run /process first.")
    _require_source_file(doc)

    selected_chapters = request.chapters if request else None
    selected_ranges = request.chapter_ranges if request else None
    if doc.pdf_scope == PdfScope.full and not selected_chapters and not selected_ranges:
        raise HTTPException(400, "Select at least one chapter before extracting from a full PDF.")

    try:
        extract_questions_for_document(
            db,
            doc,
            selected_chapters=selected_chapters,
            selected_chapter_ranges=selected_ranges,
        )
    except Exception as e:
        _handle_llm_error(e, "Extraction")

    db.refresh(doc)
    return doc


@router.post("/documents/{document_id}/reprocess", response_model=DocumentResponse)
def reprocess_doc(
    document_id: int,
    db: Session = Depends(get_db),
    x_pdf_inspector: str | None = Header(default=None),
):
    """Re-parse and re-extract a document without re-uploading."""
    doc = get_document(db, document_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    _require_source_file(doc)

    try:
        doc = process_document(db, doc, analyze_structure=_pdf_inspector_override(x_pdf_inspector))
        if doc.pdf_scope != PdfScope.full:
            extract_questions_for_document(db, doc)
    except Exception as e:
        _handle_llm_error(e, "Parsing")

    db.refresh(doc)
    return doc
