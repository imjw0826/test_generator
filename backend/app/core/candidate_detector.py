import re
from dataclasses import dataclass


@dataclass
class CandidateBlock:
    page_number: int
    text: str
    section_hint: str | None = None
    chapter_hint: str | None = None


SECTION_KEYWORDS = [
    r"exercises?",
    r"problems?",
    r"review\s+questions?",
    r"practice",
    r"chapter\s+review",
    r"end[- ]of[- ]chapter",
    r"self[- ]?test",
    r"check\s+your\s+understanding",
    r"study\s+questions?",
    r"homework",
    r"assignments?",
]

SECTION_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:" + "|".join(SECTION_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

QUESTION_NUMBER_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:\d{1,3}[\.\)]\s|[a-z][\.\)]\s|Q\d+|#\d+)",
    re.MULTILINE,
)


def detect_candidates(pages: list[tuple]) -> list[CandidateBlock]:
    candidates: list[CandidateBlock] = []

    for page in pages:
        page_number, text, chapter_hint = _unpack_page_tuple(page)
        if not text or len(text.strip()) < 20:
            continue

        section_match = SECTION_PATTERN.search(text)
        number_matches = QUESTION_NUMBER_PATTERN.findall(text)

        if section_match:
            section_hint = section_match.group().strip()
            start = section_match.start()
            block_text = text[start:].strip()
            if block_text:
                candidates.append(CandidateBlock(
                    page_number=page_number,
                    text=block_text,
                    section_hint=section_hint,
                    chapter_hint=chapter_hint,
                ))
        elif len(number_matches) >= 2:
            candidates.append(CandidateBlock(
                page_number=page_number,
                text=text.strip(),
                section_hint=None,
                chapter_hint=chapter_hint,
            ))

    return candidates


def _unpack_page_tuple(page: tuple) -> tuple[int, str, str | None]:
    if len(page) == 2:
        page_number, text = page
        return page_number, text, None
    page_number, text, chapter_hint = page
    return page_number, text, chapter_hint
