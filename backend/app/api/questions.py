from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.db.database import get_db
from app.core.question_translator import translate_question_to_korean
from app.models.document import Document
from app.models.question import Question
from app.schemas.question import (
    QuestionFilterOptionsResponse,
    QuestionListResponse,
    QuestionResponse,
    QuestionTranslationResponse,
)

router = APIRouter(prefix="/api", tags=["questions"])


@router.get("/questions", response_model=QuestionListResponse)
def list_questions(
    source_role: str | None = None,
    subject: str | None = None,
    document_id: int | None = None,
    chapter: str | None = None,
    search: str | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = (
        db.query(Question)
        .options(joinedload(Question.source_document))
        .join(Document, Question.source_document_id == Document.id)
        .filter(Question.is_active == True)
    )

    if source_role:
        query = query.filter(Question.source_role == source_role)
    if subject:
        query = query.filter(Document.subject == subject)
    if document_id:
        query = query.filter(Question.source_document_id == document_id)
    if chapter:
        query = query.filter(Question.chapter == chapter)
    if search:
        query = query.filter(
            or_(
                Question.question_text.ilike(f"%{search}%"),
                Question.normalized_question_text.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    questions = (
        query
        .order_by(Document.subject, Question.chapter, Question.page_start, Question.id)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return QuestionListResponse(
        questions=[QuestionResponse.model_validate(q) for q in questions],
        total=total,
    )


@router.get("/questions/filter-options", response_model=QuestionFilterOptionsResponse)
def get_question_filter_options(db: Session = Depends(get_db)):
    rows = (
        db.query(Document.subject, Question.chapter)
        .join(Question, Question.source_document_id == Document.id)
        .filter(Question.is_active == True)
        .all()
    )

    subjects = sorted({subject for subject, _chapter in rows if subject})
    chapters = sorted({chapter for _subject, chapter in rows if chapter})
    chapters_by_subject: dict[str, list[str]] = {}
    for subject, chapter in rows:
        if not subject or not chapter:
            continue
        chapters_by_subject.setdefault(subject, [])
        if chapter not in chapters_by_subject[subject]:
            chapters_by_subject[subject].append(chapter)

    for subject in chapters_by_subject:
        chapters_by_subject[subject].sort()

    return QuestionFilterOptionsResponse(
        subjects=subjects,
        chapters=chapters,
        chapters_by_subject=chapters_by_subject,
    )


@router.get("/questions/{question_id}", response_model=QuestionResponse)
def get_question(question_id: int, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(404, "Question not found.")
    return question


@router.post("/questions/{question_id}/translate", response_model=QuestionTranslationResponse)
def translate_question(question_id: int, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(404, "Question not found.")
    try:
        translated_text = translate_question_to_korean(question.question_text)
    except Exception as e:
        raise HTTPException(500, f"Translation failed: {e}") from e
    return QuestionTranslationResponse(question_id=question.id, translated_text=translated_text)
