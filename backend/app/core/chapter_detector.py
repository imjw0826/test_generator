import re

from app.core.pdf_parser import PageText


CHAPTER_PATTERNS = [
    re.compile(r"^\s*(chapter\s+\d+\s*[:.\-]?\s+.{3,120})$", re.IGNORECASE),
    re.compile(r"^\s*((?:\d+\.)+\d+\s+.{3,120})$"),
    re.compile(r"^\s*(\d+\s+[A-Z][A-Za-z0-9 ,:;()\-]{3,120})$"),
]

QUESTION_LIKE = re.compile(r"^\s*(?:\d{1,3}[\.)]\s|[a-z][\.)]\s|Q\d+\b)", re.IGNORECASE)


def detect_page_chapters(pages: list[PageText]) -> dict[int, str | None]:
    chapters: dict[int, str | None] = {}
    current_chapter: str | None = None

    for page in pages:
        detected = _detect_chapter_on_page(page.raw_text)
        if detected:
            current_chapter = detected
        chapters[page.page_number] = current_chapter

    return chapters


def _detect_chapter_on_page(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:25]:
        if _is_heading_candidate(line):
            return _clean_heading(line)
    return None


def _is_heading_candidate(line: str) -> bool:
    if QUESTION_LIKE.match(line):
        return False
    if len(line) > 140:
        return False
    return any(pattern.match(line) for pattern in CHAPTER_PATTERNS)


def _clean_heading(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip(" -:")
