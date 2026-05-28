from datetime import datetime

from pydantic import BaseModel

from app.models.document import DocumentRole, DocumentStatus, PdfScope


class DocumentResponse(BaseModel):
    id: int
    file_name: str
    original_name: str
    subject: str
    document_role: DocumentRole
    pdf_scope: PdfScope
    chapter_outline: list[dict] | None = None
    status: DocumentStatus
    page_count: int | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUpdateRequest(BaseModel):
    subject: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int
