from datetime import datetime

from pydantic import BaseModel


class QuestionResponse(BaseModel):
    id: int
    source_document_id: int
    source_role: str
    subject: str | None = None
    chapter: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    question_number: str | None = None
    question_text: str
    tags: list[str] | None = None
    figure_refs: list[dict] | None = None
    extracted_confidence: float | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuestionListResponse(BaseModel):
    questions: list[QuestionResponse]
    total: int


class QuestionFilterOptionsResponse(BaseModel):
    subjects: list[str]
    chapters: list[str]
    chapters_by_subject: dict[str, list[str]]


class QuestionTranslationResponse(BaseModel):
    question_id: int
    translated_text: str


class ExtractionResultResponse(BaseModel):
    document_id: int
    status: str
    questions_extracted: int
