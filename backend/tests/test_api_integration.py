import io
import pytest
import fitz
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.database import get_db
from app.main import app
from app.models.document import Document
from app.models.question import Question

from fastapi.testclient import TestClient


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    tw = fitz.TextWriter(page.rect)
    tw.append((72, 72), "Exercises")
    tw.append((72, 100), "1. What is osmosis?")
    tw.append((72, 130), "2. Describe mitosis.")
    tw.write_text(page)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def test_upload_pdf(client, sample_pdf):
    r = client.post(
        "/api/upload",
        files={"file": ("test.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        data={"document_role": "textbook", "subject": "Biology"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "uploaded"
    assert data["original_name"] == "test.pdf"
    assert data["document_role"] == "textbook"
    assert data["subject"] == "Biology"


def test_upload_rejects_non_pdf(client):
    r = client.post(
        "/api/upload",
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        data={"document_role": "textbook"},
    )
    assert r.status_code == 400


def test_document_list(client, sample_pdf):
    client.post(
        "/api/upload",
        files={"file": ("a.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        data={"document_role": "textbook"},
    )
    client.post(
        "/api/upload",
        files={"file": ("b.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        data={"document_role": "sample_exam"},
    )

    r = client.get("/api/documents")
    assert r.status_code == 200
    assert r.json()["total"] == 2

    r2 = client.get("/api/documents?role=textbook")
    assert r2.json()["total"] == 1


def test_document_not_found(client):
    r = client.get("/api/documents/999")
    assert r.status_code == 404


def test_process_document(client, sample_pdf):
    r = client.post(
        "/api/upload",
        files={"file": ("test.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        data={"document_role": "textbook"},
    )
    doc_id = r.json()["id"]

    r2 = client.post(f"/api/documents/{doc_id}/process")
    assert r2.status_code == 200
    assert r2.json()["status"] == "parsed"
    assert r2.json()["page_count"] == 1


def test_questions_endpoint_empty(client):
    r = client.get("/api/questions")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_reset_removes_all_uploaded_documents_and_questions(client, sample_pdf, db_session):
    first = client.post(
        "/api/upload",
        files={"file": ("a.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        data={"document_role": "textbook"},
    )
    second = client.post(
        "/api/upload",
        files={"file": ("b.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        data={"document_role": "sample_exam"},
    )
    db_session.add_all([
        Question(
            source_document_id=first.json()["id"],
            source_role="textbook",
            question_text="What is osmosis?",
            is_active=True,
        ),
        Question(
            source_document_id=second.json()["id"],
            source_role="sample_exam",
            question_text="Describe mitosis.",
            is_active=True,
        ),
    ])
    db_session.commit()

    response = client.delete("/api/reset")

    assert response.status_code == 200
    assert response.json()["reset"] is True
    assert db_session.query(Document).count() == 0
    assert db_session.query(Question).count() == 0


def test_study_set_empty(client):
    r = client.post("/api/study-set/random", json={"count": 5})
    assert r.status_code == 200
    assert r.json()["total_selected"] == 0


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_extract_questions_replaces_existing_rows_after_llm_returns(client, sample_pdf, db_session):
    upload_response = client.post(
        "/api/upload",
        files={"file": ("test.pdf", io.BytesIO(sample_pdf), "application/pdf")},
        data={"document_role": "textbook"},
    )
    doc_id = upload_response.json()["id"]

    process_response = client.post(f"/api/documents/{doc_id}/process")
    assert process_response.status_code == 200

    with patch(
        "app.services.question_service.extract_questions_from_block",
        return_value=[
            {
                "question_number": "1",
                "question_text": "What is osmosis?",
                "tags": ["biology"],
                "confidence": 0.9,
            }
        ],
    ) as extractor:
        first_extract = client.post(f"/api/documents/{doc_id}/extract")
        second_extract = client.post(f"/api/documents/{doc_id}/extract")

    assert first_extract.status_code == 200
    assert second_extract.status_code == 200
    assert extractor.call_count == 2

    questions = db_session.query(Question).filter_by(source_document_id=doc_id).all()
    assert len(questions) == 1
    assert questions[0].question_text == "What is osmosis?"
