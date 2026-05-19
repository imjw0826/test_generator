import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import Document, DocumentRole, DocumentStatus, PdfScope
from app.models.parsed_page import ParsedPage
from app.models.practice_session import PracticeSession
from app.models.question import Question


def save_upload(
    db: Session,
    file: UploadFile,
    document_role: DocumentRole,
    subject: str = "Uncategorized",
    pdf_scope: PdfScope = PdfScope.chapter,
) -> Document:
    ext = Path(file.filename or "upload.pdf").suffix
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest = settings.upload_path / unique_name

    with open(dest, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    doc = Document(
        file_name=unique_name,
        original_name=file.filename or "unknown.pdf",
        subject=_normalize_subject(subject),
        document_role=document_role,
        pdf_scope=pdf_scope,
        file_path=str(dest),
        mime_type=file.content_type or "application/pdf",
        status=DocumentStatus.uploaded,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _normalize_subject(subject: str | None) -> str:
    cleaned = (subject or "").strip()
    return cleaned or "Uncategorized"


def list_documents(
    db: Session,
    role: DocumentRole | None = None,
    status: DocumentStatus | None = None,
) -> list[Document]:
    query = db.query(Document)
    if role:
        query = query.filter(Document.document_role == role)
    if status:
        query = query.filter(Document.status == status)
    return query.order_by(Document.created_at.desc()).all()


def get_document(db: Session, document_id: int) -> Document | None:
    return db.query(Document).filter(Document.id == document_id).first()


def delete_document(db: Session, document: Document) -> dict[str, int]:
    counts = {
        "documents": 1,
        "parsed_pages": db.query(ParsedPage).filter(ParsedPage.document_id == document.id).count(),
        "questions": db.query(Question).filter(Question.source_document_id == document.id).count(),
    }
    file_path = Path(document.file_path)
    figure_dir = settings.figure_path / f"document_{document.id}"

    db.delete(document)
    db.commit()

    if file_path.exists():
        file_path.unlink()
    if figure_dir.exists():
        shutil.rmtree(figure_dir)

    return counts


def reset_all_data(db: Session) -> dict[str, int]:
    counts = {
        "documents": db.query(Document).count(),
        "parsed_pages": db.query(ParsedPage).count(),
        "questions": db.query(Question).count(),
        "practice_sessions": db.query(PracticeSession).count(),
    }

    db.query(PracticeSession).delete(synchronize_session=False)
    db.query(Question).delete(synchronize_session=False)
    db.query(ParsedPage).delete(synchronize_session=False)
    db.query(Document).delete(synchronize_session=False)
    db.commit()

    _empty_directory(settings.upload_path)
    _empty_directory(settings.figure_path)
    _empty_directory(settings.generated_exam_path)

    return counts


def _empty_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
