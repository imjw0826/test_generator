from collections.abc import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False, "timeout": 30},
    echo=settings.debug,
)


@event.listens_for(engine, "connect")
def configure_sqlite(connection, _record) -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    cursor = connection.cursor()
    try:
        cursor.execute("PRAGMA busy_timeout = 30000")
        cursor.execute("PRAGMA journal_mode = WAL")
    finally:
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_runtime_schema() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    with engine.begin() as conn:
        if "documents" in table_names:
            columns = {col["name"] for col in inspector.get_columns("documents")}
            if "subject" not in columns:
                conn.execute(text("ALTER TABLE documents ADD COLUMN subject VARCHAR NOT NULL DEFAULT 'Uncategorized'"))
            if "pdf_scope" not in columns:
                conn.execute(text("ALTER TABLE documents ADD COLUMN pdf_scope VARCHAR NOT NULL DEFAULT 'chapter'"))
            if "chapter_outline" not in columns:
                conn.execute(text("ALTER TABLE documents ADD COLUMN chapter_outline JSON"))

        if "parsed_pages" in table_names:
            columns = {col["name"] for col in inspector.get_columns("parsed_pages")}
            if "figures" not in columns:
                conn.execute(text("ALTER TABLE parsed_pages ADD COLUMN figures JSON"))

        if "questions" in table_names:
            columns = {col["name"] for col in inspector.get_columns("questions")}
            if "figure_refs" not in columns:
                conn.execute(text("ALTER TABLE questions ADD COLUMN figure_refs JSON"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
