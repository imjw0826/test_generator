import re
from collections import Counter


def clean_text(raw_text: str, headers: set[str] | None = None, footers: set[str] | None = None) -> str:
    lines = raw_text.split("\n")
    cleaned_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if headers and stripped in headers:
            continue
        if footers and stripped in footers:
            continue
        if _is_page_number_only(stripped):
            continue
        cleaned_lines.append(stripped)

    text = "\n".join(cleaned_lines)
    text = _fix_hyphenated_words(text)
    text = _normalize_whitespace(text)
    return text.strip()


def detect_headers_footers(pages_text: list[str], threshold: float = 0.4) -> tuple[set[str], set[str]]:
    if len(pages_text) < 3:
        return set(), set()

    first_lines: Counter[str] = Counter()
    last_lines: Counter[str] = Counter()

    for text in pages_text:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            first_lines[lines[0]] += 1
        if len(lines) > 1:
            last_lines[lines[-1]] += 1

    min_count = int(len(pages_text) * threshold)
    headers = {line for line, count in first_lines.items() if count >= min_count and not _is_content_line(line)}
    footers = {line for line, count in last_lines.items() if count >= min_count and not _is_content_line(line)}

    return headers, footers


def _is_page_number_only(line: str) -> bool:
    return bool(re.fullmatch(r"\d{1,4}", line))


def _is_content_line(line: str) -> bool:
    return len(line) > 80


def _fix_hyphenated_words(text: str) -> str:
    return re.sub(r"(\w)-\n(\w)", r"\1\2", text)


def _normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text
