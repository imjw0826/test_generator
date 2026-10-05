import re

from app.core.pdf_parser import PageText


CHAPTER_PATTERNS = [
    re.compile(r"^\s*(chapter\s+\d+\s*[:.\-]?\s+.{3,120})$", re.IGNORECASE),
    re.compile(r"^\s*((?:\d+\.)+\d+\s+.{3,120})$"),
    re.compile(r"^\s*(\d+\s+[A-Z][A-Za-z0-9 ,:;()\-]{3,120})$"),
]

# "CHAPTER 3" set as its own heading line, with the title as the next heading.
CHAPTER_NUMBER_ONLY = re.compile(r"^\s*chapter\s+\d+\s*[:.\-]?\s*$", re.IGNORECASE)
NUMBERED_START = re.compile(r"^\s*(?:chapter\s+)?\d", re.IGNORECASE)
# Font-based headings drive detection only when they carry real chapter/section
# titles on at least this many pages; otherwise fall back to scanning text lines.
MIN_HEADING_CHAPTER_PAGES = 2

QUESTION_LIKE = re.compile(r"^\s*(?:\d{1,3}[\.)]\s|[a-z][\.)]\s|Q\d+\b)", re.IGNORECASE)

DOTTED_NUMBER = re.compile(r"^\s*\d+\.\d+\s")
# A page with this many "6.13 ..." style lines is a problem list, not a section start.
PROBLEM_LIST_MIN_LINES = 3
# Wrapped problem statements often break after one of these words.
TRAILING_FUNCTION_WORDS = {
    "a", "an", "and", "are", "as", "at", "by", "for", "from", "in", "is",
    "of", "on", "or", "the", "to", "was", "with",
}


def detect_page_chapters(pages: list[PageText]) -> dict[int, str | None]:
    heading_chapters = {
        page.page_number: _detect_chapter_from_headings(page.headings)
        for page in pages
        if page.headings
    }
    use_headings = sum(1 for title in heading_chapters.values() if title) >= MIN_HEADING_CHAPTER_PAGES

    chapters: dict[int, str | None] = {}
    current_chapter: str | None = None

    for page in pages:
        if use_headings:
            # Body lines are ignored here: running headers and numbered problems
            # would otherwise flip the tag on pages that carry no heading.
            detected = heading_chapters.get(page.page_number)
        else:
            detected = _detect_chapter_on_page(page.raw_text)
        if detected:
            current_chapter = detected
        chapters[page.page_number] = current_chapter

    return chapters


def _detect_chapter_from_headings(headings: list[str]) -> str | None:
    """Last chapter/section heading on the page: the one still in effect on the
    pages that follow, and the most specific when a chapter opens with a section."""
    detected: str | None = None
    index = 0
    while index < len(headings):
        heading = headings[index]
        if CHAPTER_NUMBER_ONLY.match(heading) and index + 1 < len(headings):
            title = headings[index + 1]
            combined = f"{heading.strip(' :.-')} {title}"
            if not NUMBERED_START.match(title) and _is_heading_candidate(combined):
                detected = _clean_heading(combined)
                index += 2
                continue
        if _is_heading_candidate(heading):
            detected = _clean_heading(heading)
        index += 1
    return detected


def _detect_chapter_on_page(text: str) -> str | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    is_problem_list = sum(1 for line in lines if DOTTED_NUMBER.match(line)) >= PROBLEM_LIST_MIN_LINES
    for line in lines[:25]:
        if is_problem_list and DOTTED_NUMBER.match(line):
            continue
        if _is_heading_candidate(line):
            return _clean_heading(line)
    return None


def _is_heading_candidate(line: str) -> bool:
    if QUESTION_LIKE.match(line):
        return False
    if len(line) > 140:
        return False
    if _looks_like_sentence(line):
        return False
    return any(pattern.match(line) for pattern in CHAPTER_PATTERNS)


def _looks_like_sentence(line: str) -> bool:
    """Numbered problem statements read as prose; section headings do not."""
    stripped = line.rstrip()
    if stripped.endswith((".", ",", "?", ";")):
        return True
    last_word = stripped.rsplit(None, 1)[-1].lower()
    return last_word in TRAILING_FUNCTION_WORDS


def _clean_heading(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip(" -:")
