from pydantic import BaseModel, Field

from app.schemas.question import QuestionResponse


class StudySetRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=100)
    subjects: list[str] | None = None
    chapters: list[str] | None = None
    tags: list[str] | None = None
    exclude_question_ids: list[int] | None = None


class ExamPdfRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=100)
    subject: str | None = None
    chapters: list[str] | None = None
    include_answers: bool = False


class StudySetResponse(BaseModel):
    questions: list[QuestionResponse]
    total_available: int
    total_selected: int
