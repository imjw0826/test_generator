#!/usr/bin/env python3
from __future__ import annotations

import io
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import fitz
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.database import get_db  # noqa: E402
from app.main import app  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="sqg-smoke-") as temp_root:
        temp_path = Path(temp_root)
        _redirect_runtime_dirs(temp_path)

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()

        def override_get_db():
            try:
                yield session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        try:
            _assert_health(client)
            doc_id = _upload_and_process(client)
            _extract_with_mocked_llm(client, doc_id)
            _assert_question_filters(client)
            _assert_random_set(client)
            _assert_exam_pdf(client)
        finally:
            app.dependency_overrides.clear()
            session.close()

    print("Full workflow smoke test passed.")
    return 0


def _redirect_runtime_dirs(temp_path: Path) -> None:
    settings.upload_dir = str(temp_path / "uploads")
    settings.figure_dir = str(temp_path / "figures")
    settings.generated_exam_dir = str(temp_path / "generated_exams")


def _assert_health(client: TestClient) -> None:
    response = client.get("/health")
    response.raise_for_status()
    assert response.json()["status"] == "ok"


def _upload_and_process(client: TestClient) -> int:
    response = client.post(
        "/api/upload",
        files={"file": ("workflow.pdf", io.BytesIO(_sample_pdf()), "application/pdf")},
        data={"document_role": "textbook", "subject": "Differential Equations"},
    )
    response.raise_for_status()
    doc = response.json()
    assert doc["subject"] == "Differential Equations"
    assert doc["status"] == "uploaded"

    process = client.post(f"/api/documents/{doc['id']}/process")
    process.raise_for_status()
    assert process.json()["status"] == "parsed"
    assert process.json()["page_count"] == 1
    return int(doc["id"])


def _extract_with_mocked_llm(client: TestClient, doc_id: int) -> None:
    with patch(
        "app.services.question_service.extract_questions_from_block",
        return_value=[
            {
                "question_number": "1",
                "question_text": r"Solve **the equation** \(x^2 = 4\).",
                "figure_ids": [],
                "confidence": 0.98,
            }
        ],
    ):
        response = client.post(f"/api/documents/{doc_id}/extract")
    response.raise_for_status()
    assert response.json()["status"] == "extracted"


def _assert_question_filters(client: TestClient) -> None:
    options = client.get("/api/questions/filter-options")
    options.raise_for_status()
    data = options.json()
    assert "Differential Equations" in data["subjects"]
    assert "2.5 Euler Cauchy Equations" in data["chapters_by_subject"]["Differential Equations"]

    questions = client.get(
        "/api/questions",
        params={
            "subject": "Differential Equations",
            "chapter": "2.5 Euler Cauchy Equations",
            "search": "equation",
        },
    )
    questions.raise_for_status()
    payload = questions.json()
    assert payload["total"] == 1
    assert payload["questions"][0]["subject"] == "Differential Equations"
    assert payload["questions"][0]["chapter"] == "2.5 Euler Cauchy Equations"


def _assert_random_set(client: TestClient) -> None:
    response = client.post(
        "/api/study-set/random",
        json={
            "count": 1,
            "subjects": ["Differential Equations"],
            "chapters": ["2.5 Euler Cauchy Equations"],
        },
    )
    response.raise_for_status()
    data = response.json()
    assert data["total_selected"] == 1
    assert data["questions"][0]["question_text"].startswith("Solve")


def _assert_exam_pdf(client: TestClient) -> None:
    response = client.post(
        "/api/study-set/exam-pdf",
        json={
            "count": 1,
            "subject": "Differential Equations",
            "chapters": ["2.5 Euler Cauchy Equations"],
            "include_answers": False,
        },
    )
    response.raise_for_status()
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 1000


def _sample_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    writer = fitz.TextWriter(page.rect)
    writer.append((72, 72), "2.5 Euler Cauchy Equations")
    writer.append((72, 110), "PROBLEM SET 2.5")
    writer.append((72, 140), "1. Solve the equation x^2 y'' + xy' - y = 0.")
    writer.write_text(page)
    buffer = io.BytesIO()
    doc.save(buffer)
    doc.close()
    return buffer.getvalue()


if __name__ == "__main__":
    raise SystemExit(main())
