import random

from sqlalchemy.orm import Session, joinedload

from app.models.document import Document
from app.models.question import Question


def select_random_questions(
    db: Session,
    count: int = 10,
    subjects: list[str] | None = None,
    chapters: list[str] | None = None,
    tags: list[str] | None = None,
    exclude_question_ids: list[int] | None = None,
) -> list[Question]:
    query = (
        db.query(Question)
        .options(joinedload(Question.source_document))
        .join(Document, Question.source_document_id == Document.id)
        .filter(
            Question.is_active == True,
            Question.source_role == "textbook",
        )
    )

    if subjects:
        query = query.filter(Document.subject.in_(subjects))
    if chapters:
        query = query.filter(Question.chapter.in_(chapters))
    if exclude_question_ids:
        query = query.filter(Question.id.notin_(exclude_question_ids))
    if tags:
        for tag in tags:
            query = query.filter(Question.tags.contains(tag))

    candidates = query.all()

    if not candidates:
        return []

    actual_count = min(count, len(candidates))
    if chapters and len(chapters) > 1:
        return _balanced_sample_by_chapter(candidates, chapters, actual_count)

    return random.sample(candidates, actual_count)


def _balanced_sample_by_chapter(
    candidates: list[Question],
    chapters: list[str],
    count: int,
) -> list[Question]:
    by_chapter: dict[str, list[Question]] = {chapter: [] for chapter in chapters}
    for question in candidates:
        if question.chapter in by_chapter:
            by_chapter[question.chapter].append(question)

    selected: list[Question] = []
    selected_ids: set[int] = set()
    base_quota = count // len(chapters)
    remainder = count % len(chapters)

    for index, chapter in enumerate(chapters):
        quota = base_quota + (1 if index < remainder else 0)
        pool = by_chapter.get(chapter, [])
        picked = random.sample(pool, min(quota, len(pool)))
        selected.extend(picked)
        selected_ids.update(question.id for question in picked)

    deficit = count - len(selected)
    if deficit > 0:
        remaining = [question for question in candidates if question.id not in selected_ids]
        selected.extend(random.sample(remaining, min(deficit, len(remaining))))

    random.shuffle(selected)
    return selected
