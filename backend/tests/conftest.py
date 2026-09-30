import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def isolated_storage_dirs(tmp_path, monkeypatch):
    """Keep tests away from the real data/ directories.

    /api/reset and document deletion remove files under these paths, so tests
    that hit them must never point at backend/data.
    """
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "figure_dir", str(tmp_path / "figures"))
    monkeypatch.setattr(settings, "generated_exam_dir", str(tmp_path / "generated_exams"))
