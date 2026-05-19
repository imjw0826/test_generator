from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.document import DocumentRole, DocumentStatus
from app.schemas.document import DocumentResponse, DocumentListResponse
from app.services.document_service import delete_document, list_documents, get_document, reset_all_data

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents", response_model=DocumentListResponse)
def get_documents(
    role: DocumentRole | None = None,
    status: DocumentStatus | None = None,
    db: Session = Depends(get_db),
):
    docs = list_documents(db, role=role, status=status)
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=len(docs),
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document_detail(document_id: int, db: Session = Depends(get_db)):
    doc = get_document(db, document_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    return doc


@router.get("/documents/{document_id}/chapters")
def get_document_chapters(document_id: int, db: Session = Depends(get_db)):
    doc = get_document(db, document_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    return {"document_id": doc.id, "chapters": doc.chapter_outline or []}


@router.delete("/documents/{document_id}")
def delete_document_endpoint(document_id: int, db: Session = Depends(get_db)):
    doc = get_document(db, document_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    counts = delete_document(db, doc)
    return {"deleted": counts}


@router.delete("/reset")
def reset_all_endpoint(db: Session = Depends(get_db)):
    counts = reset_all_data(db)
    return {"reset": True, "deleted": counts}
