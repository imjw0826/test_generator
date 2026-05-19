from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.models.document import DocumentRole, PdfScope
from app.schemas.document import DocumentResponse
from app.services.document_service import save_upload

router = APIRouter(prefix="/api", tags=["upload"])

PDF_MAGIC = b"%PDF-"


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_role: DocumentRole = Form(...),
    subject: str = Form("Uncategorized"),
    pdf_scope: PdfScope = Form(PdfScope.chapter),
    db: Session = Depends(get_db),
):
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if file.size and file.size > max_bytes:
        raise HTTPException(400, f"File exceeds {settings.max_upload_size_mb} MB limit.")

    header = await file.read(len(PDF_MAGIC))
    if header != PDF_MAGIC:
        raise HTTPException(400, "Only PDF files are allowed.")
    await file.seek(0)

    doc = save_upload(db, file, document_role, subject, pdf_scope)
    return doc
