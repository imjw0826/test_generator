from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.exam_generator import generate_exam_package, generate_solution_exam_package
from app.db.database import get_db
from app.core.random_selector import select_random_questions
from app.models.question import Question
from app.schemas.question import QuestionResponse
from app.schemas.random_set import ExamPdfRequest, StudySetRequest, StudySetResponse

router = APIRouter(prefix="/api", tags=["study-set"])


@router.post("/study-set/random", response_model=StudySetResponse)
def generate_random_set(
    request: StudySetRequest,
    db: Session = Depends(get_db),
):
    total_available = (
        db.query(Question)
        .filter(Question.is_active == True, Question.source_role == "textbook")
        .count()
    )

    selected = select_random_questions(
        db,
        count=request.count,
        subjects=request.subjects,
        chapters=request.chapters,
        tags=request.tags,
        exclude_question_ids=request.exclude_question_ids,
    )

    return StudySetResponse(
        questions=[QuestionResponse.model_validate(q) for q in selected],
        total_available=total_available,
        total_selected=len(selected),
    )


@router.post("/study-set/exam-pdf")
def generate_exam_pdf(
    request: ExamPdfRequest,
    db: Session = Depends(get_db),
):
    try:
        generated = generate_exam_package(
            db,
            count=request.count,
            subject=request.subject,
            chapters=request.chapters,
            include_answers=request.include_answers,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(500, str(e)) from e

    return FileResponse(
        generated.path,
        media_type=generated.media_type,
        filename=generated.filename,
    )


@router.post("/study-set/solutions-pdf")
def generate_solutions_pdf(
    request: ExamPdfRequest,
    db: Session = Depends(get_db),
):
    try:
        generated = generate_solution_exam_package(
            db,
            count=request.count,
            subject=request.subject,
            chapters=request.chapters,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(500, str(e)) from e

    return FileResponse(
        generated.path,
        media_type=generated.media_type,
        filename=generated.filename,
    )
