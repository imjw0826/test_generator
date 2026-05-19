import enum
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DocumentRole(str, enum.Enum):
    textbook = "textbook"
    sample_exam = "sample_exam"


class PdfScope(str, enum.Enum):
    chapter = "chapter"
    full = "full"


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    parsed = "parsed"
    extracted = "extracted"
    failed = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    original_name: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str] = mapped_column(String, nullable=False, default="Uncategorized")
    document_role: Mapped[DocumentRole] = mapped_column(Enum(DocumentRole), nullable=False)
    pdf_scope: Mapped[PdfScope] = mapped_column(Enum(PdfScope), default=PdfScope.chapter, nullable=False)
    chapter_outline: Mapped[list | None] = mapped_column(JSON, nullable=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str] = mapped_column(String, default="application/pdf")
    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.uploaded)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    pages: Mapped[list["ParsedPage"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    questions: Mapped[list["Question"]] = relationship(back_populates="source_document", cascade="all, delete-orphan")


from app.models.parsed_page import ParsedPage  # noqa: E402
from app.models.question import Question  # noqa: E402
