import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.document import Document, DocumentRole, DocumentStatus
from app.models.question import Question
from app.core.random_selector import select_random_questions


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    session.add(Document(
        id=1, file_name="tb.pdf", original_name="tb.pdf",
        subject="Differential Equations",
        document_role=DocumentRole.textbook, file_path="x",
        status=DocumentStatus.extracted,
    ))

    for i in range(20):
        session.add(Question(
            source_document_id=1,
            source_role="textbook",
            question_text=f"Question {i+1}",
            normalized_question_text=f"question {i+1}",
            question_number=str(i + 1),
            chapter=f"ch{i % 3 + 1}",
            page_start=i + 1,
            is_active=True,
        ))

    session.commit()
    yield session
    session.close()


def test_basic_random_selection(db):
    result = select_random_questions(db, count=5)
    assert len(result) == 5
    ids = [q.id for q in result]
    assert len(set(ids)) == 5  # no duplicates


def test_count_exceeds_available(db):
    result = select_random_questions(db, count=100)
    assert len(result) == 20


def test_filter_by_chapter(db):
    result = select_random_questions(db, count=10, chapters=["ch1"])
    assert all(q.chapter == "ch1" for q in result)


def test_filter_by_subject(db):
    result = select_random_questions(db, count=10, subjects=["Differential Equations"])
    assert len(result) == 10
    assert all(q.subject == "Differential Equations" for q in result)


def test_balances_multiple_chapters(db):
    result = select_random_questions(db, count=10, chapters=["ch1", "ch2"])
    counts = {chapter: 0 for chapter in ["ch1", "ch2"]}
    for question in result:
        counts[question.chapter] += 1

    assert len(result) == 10
    assert counts == {"ch1": 5, "ch2": 5}


def test_exclude_question_ids(db):
    result = select_random_questions(db, count=5, exclude_question_ids=[1, 2, 3])
    ids = [q.id for q in result]
    assert 1 not in ids
    assert 2 not in ids
    assert 3 not in ids


def test_empty_result():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    result = select_random_questions(session, count=5)
    assert len(result) == 0
    session.close()
