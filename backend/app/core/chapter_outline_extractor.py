import json
import logging
import re

from app.config import settings
from app.core.llm_runtime import LlmResponseError, create_text_message
from app.models.parsed_page import ParsedPage

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Extract the textbook contents from the provided contents page text.
Return only a valid JSON array. Each item:
{
  "title": "numbered chapter or section title exactly as shown",
  "page_label": "printed page number from the contents"
}
Rules:
- Use only entries that appear in the contents.
- Include every visible numbered chapter and section entry, for example "CHAPTER 8 Linear Algebra" and "8.1 Matrix Eigenvalue Problem".
- Exclude exercises, review questions, problems, answers, bibliography, index, and appendices unless they are the main requested content.
- Do not infer from ordinary page headings outside the contents."""


def detect_chapter_outline_with_sonnet(pages: list[ParsedPage], document_path: str | None = None) -> list[dict]:
    del document_path
    contents_pages = _select_contents_pages(pages)
    if not contents_pages:
        logger.warning("No text contents candidate pages found.")
        return []

    text = _build_outline_input(contents_pages)
    if not text.strip():
        return []

    local_entries = _iter_numbered_contents_entries(text)
    local_outline = _resolve_contents_entries_to_page_ranges(local_entries, pages, contents_pages=contents_pages)
    if len(local_outline) >= 2:
        return local_outline

    try:
        raw = create_text_message(
            settings.llm_outline_model,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
            max_tokens=16000,
            effort=settings.llm_outline_effort,
        )
    except LlmResponseError as e:
        logger.warning("Chapter outline LLM call returned no usable output: %s", e)
        return local_outline
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning("Chapter outline JSON parse failed: %s", e)
        return local_outline

    if not isinstance(payload, list):
        return local_outline

    entries = _entries_from_payload(payload)
    entries = _repair_missing_numbered_entries(entries, text)

    outline = _resolve_contents_entries_to_page_ranges(entries, pages, contents_pages=contents_pages)
    if outline:
        return outline

    logger.warning("Text contents extraction returned no resolved entries.")
    return []


def fallback_chapter_outline(pages: list[ParsedPage]) -> list[dict]:
    outline: list[dict] = []
    current: dict | None = None
    for page in pages:
        title = page.section_hint
        if title and (not current or current["title"] != title):
            if current:
                current["end_page"] = page.page_number - 1
                outline.append(current)
            current = {"title": title, "start_page": page.page_number, "end_page": page.page_number}
        elif current:
            current["end_page"] = page.page_number
    if current:
        outline.append(current)
    return outline


def _build_outline_input(pages: list[ParsedPage]) -> str:
    chunks = []
    for page in pages:
        text = _normalize_contents_page_text(page.raw_text or "")
        chunks.append(f"PDF PAGE {page.page_number}\n{text[:4500]}")
    return "\n\n".join(chunks)


def _normalize_contents_page_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        cleaned = line.replace("\t", " ").strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines)


def _entries_from_payload(payload) -> list[dict]:
    entries: list[dict] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        page_label = str(item.get("page_label") or "").strip()
        if _is_valid_contents_title(title) and not _is_excluded_contents_title(title):
            entries.append({"title": _clean_contents_title(title), "page_label": page_label})
    return entries


def _repair_missing_numbered_entries(entries: list[dict], contents_text: str) -> list[dict]:
    existing_numbers = {_extract_outline_number(entry["title"]) for entry in entries}
    repaired = list(entries)

    for match in _iter_numbered_contents_entries(contents_text):
        number = _extract_outline_number(match["title"])
        if not number or number in existing_numbers:
            continue
        if _is_excluded_contents_title(match["title"]):
            continue
        repaired.append(match)
        existing_numbers.add(number)

    repaired.sort(key=lambda entry: (
        _safe_int(entry.get("page_label")) if _safe_int(entry.get("page_label")) is not None else 999999,
        _outline_level(entry["title"]),
        _outline_number_sort_key(entry["title"]),
    ))
    return repaired


def _iter_numbered_contents_entries(text: str) -> list[dict]:
    candidates: list[dict] = []
    lines = [line.strip() for line in text.replace("\\n", "\n").splitlines() if line.strip()]
    i = 0

    while i < len(lines):
        line = lines[i]
        if line.startswith("PDF PAGE "):
            i += 1
            continue

        inline = _entry_from_single_line(line)
        if inline:
            candidates.append(inline)
            i += 1
            continue

        chapter_match = re.match(r"^(CHAPTER\s+\d+)\b\s*(.*)$", line, re.IGNORECASE)
        section_match = re.match(r"^(\d+(?:\.\d+)+)\s*(.*)$", line)
        marker_match = chapter_match or section_match
        if not marker_match:
            i += 1
            continue

        number = marker_match.group(1)
        title_parts = [marker_match.group(2).strip()] if marker_match.group(2).strip() else []
        j = i + 1
        page_label = None
        while j < len(lines):
            next_line = lines[j].strip()
            if next_line.startswith("PDF PAGE "):
                break
            if _looks_like_entry_start(next_line):
                break
            page_match = re.match(r"^(?P<title>.*?)(?:\.{2,}\s*|\s{2,})(?P<page>\d{1,4})$", next_line)
            if page_match and page_match.group("title").strip():
                title_parts.append(page_match.group("title").strip(" ."))
                page_label = page_match.group("page")
                j += 1
                break
            if re.fullmatch(r"\d{1,4}", next_line):
                page_label = next_line
                j += 1
                break
            title_parts.append(next_line.strip(" ."))
            j += 1

        if page_label and title_parts:
            title = _clean_contents_title(f"{number} {' '.join(title_parts)}")
            if _is_valid_contents_title(title) and not _is_excluded_contents_title(title):
                candidates.append({"title": title, "page_label": page_label})
            i = j
            continue

        i += 1

    return candidates


def _entry_from_single_line(line: str) -> dict | None:
    match = re.match(
        r"^(?P<title>(?:CHAPTER\s+\d+\b|\d+(?:\.\d+)+\b)\s+.{3,220}?)(?:\.{2,}|\s{2,})(?P<page>\d{1,4})$",
        line,
        re.IGNORECASE,
    )
    if not match:
        return None
    title = _clean_contents_title(match.group("title"))
    if not _is_valid_contents_title(title) or _is_excluded_contents_title(title):
        return None
    return {"title": title, "page_label": match.group("page")} if title else None


def _looks_like_entry_start(line: str) -> bool:
    return bool(re.match(r"^(?:CHAPTER\s+\d+\b|\d+(?:\.\d+)+\b)", line, re.IGNORECASE))


def _select_contents_pages(pages: list[ParsedPage]) -> list[ParsedPage]:
    front_matter = pages[: min(len(pages), 40)]
    explicit_contents: list[tuple[int, ParsedPage]] = []
    likely_contents: list[tuple[int, ParsedPage]] = []
    for page in front_matter:
        text = page.raw_text or ""
        has_contents_title = _has_contents_heading(text)
        looks_like_contents = _looks_like_contents_page(text)
        if not has_contents_title and not looks_like_contents:
            continue

        score = 5 if has_contents_title else 0
        score += min(5, len(re.findall(r"\.{2,}\s*\d+", text)))
        score += min(4, len(re.findall(r"^\s*\d+(?:\.\d+)*\s+.{3,80}\s+\d+\s*$", text, re.MULTILINE)))
        if has_contents_title:
            explicit_contents.append((score, page))
        else:
            likely_contents.append((score, page))

    scored = explicit_contents or likely_contents
    if not scored:
        return []

    best_page = max(scored, key=lambda item: item[0])[1].page_number
    start_page = best_page
    page_by_number = {page.page_number: page for page in front_matter}
    while start_page > 1:
        previous = page_by_number.get(start_page - 1)
        if not previous or not _looks_like_contents_page(previous.raw_text or ""):
            break
        start_page -= 1

    return [
        page
        for page in front_matter
        if start_page <= page.page_number <= best_page + 10
    ]


def _looks_like_contents_page(text: str) -> bool:
    if _has_contents_heading(text):
        return True
    numbered_entry_count = len(re.findall(r"^\s*(?:CHAPTER\s+\d+|\d+(?:\.\d+)+)\b", text, re.MULTILINE | re.IGNORECASE))
    page_number_line_count = len(re.findall(r"^\s*\d{1,4}\s*$", text, re.MULTILINE))
    return numbered_entry_count >= 3 and page_number_line_count >= 3


def _has_contents_heading(text: str) -> bool:
    for line in text.splitlines()[:12]:
        compact = re.sub(r"[^A-Za-z]+", "", line).lower()
        if compact in {"contents", "tableofcontents"}:
            return True
    return False


def _resolve_contents_entries_to_page_ranges(
    entries: list[dict],
    pages: list[ParsedPage],
    contents_pages: list[ParsedPage] | None = None,
) -> list[dict]:
    contents_page_numbers = {page.page_number for page in contents_pages or []}
    searchable_pages = [page for page in pages if page.page_number not in contents_page_numbers]
    resolved: list[dict] = []
    for entry in entries:
        title = entry["title"]
        start_page = _find_title_page(title, searchable_pages)
        label_page = _safe_int(entry.get("page_label"))
        resolved.append({
            "title": title,
            "page_label": entry.get("page_label") or None,
            "start_page": start_page,
            "label_page": label_page,
        })

    offset = _estimate_page_offset(resolved, contents_pages=contents_pages)
    for item in resolved:
        if item["label_page"] is not None and offset is not None:
            expected_page = item["label_page"] + offset
            if item["start_page"] is None or abs(item["start_page"] - expected_page) > 2:
                item["start_page"] = expected_page

    valid = [
        item
        for item in resolved
        if isinstance(item.get("start_page"), int) and 1 <= item["start_page"] <= len(pages)
    ]
    valid.sort(key=lambda item: (
        item["label_page"] if item.get("label_page") is not None else item["start_page"],
        _outline_level(item["title"]),
        _outline_number_sort_key(item["title"]),
        item["start_page"],
    ))

    outline: list[dict] = []
    for index, item in enumerate(valid):
        next_start = valid[index + 1]["start_page"] if index + 1 < len(valid) else len(pages) + 1
        end_page = max(item["start_page"], next_start - 1)
        outline.append({
            "title": item["title"],
            "start_page": item["start_page"],
            "end_page": min(end_page, len(pages)),
            "page_label": item.get("page_label"),
        })
    return _annotate_outline_hierarchy(_dedupe_outline(outline))


def _find_title_page(title: str, pages: list[ParsedPage]) -> int | None:
    target = _normalize_title(title)
    if not target:
        return None

    short_target = re.sub(r"^\d+(?:\.\d+)*\s*", "", target)
    for page in pages:
        page_text = _normalize_title(page.raw_text or "")
        if target in page_text or (short_target and short_target in page_text):
            return page.page_number
    return None


def _estimate_page_offset(items: list[dict], contents_pages: list[ParsedPage] | None = None) -> int | None:
    offsets = [
        int(item["start_page"]) - int(item["label_page"])
        for item in items
        if item.get("start_page") is not None and item.get("label_page") is not None
    ]
    plausible_offsets = [offset for offset in offsets if offset >= 0]
    if plausible_offsets:
        plausible_offsets.sort()
        return plausible_offsets[len(plausible_offsets) // 2]

    first_label = min(
        (int(item["label_page"]) for item in items if item.get("label_page") is not None),
        default=None,
    )
    if first_label is not None and contents_pages:
        first_content_page = max(page.page_number for page in contents_pages) + 1
        return max(0, first_content_page - first_label)

    if not offsets:
        return None
    offsets.sort()
    return offsets[len(offsets) // 2]


def _dedupe_outline(outline: list[dict]) -> list[dict]:
    seen: set[tuple[str, int, int]] = set()
    deduped: list[dict] = []
    for item in outline:
        key = (item["title"], item["start_page"], item["end_page"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _annotate_outline_hierarchy(outline: list[dict]) -> list[dict]:
    outline = sorted(outline, key=lambda item: (
        _safe_int(item.get("page_label")) if _safe_int(item.get("page_label")) is not None else item["start_page"],
        _outline_level(item["title"]),
        _outline_number_sort_key(item["title"]),
        item["start_page"],
    ))
    latest_by_level: dict[int, str] = {}
    annotated: list[dict] = []

    for item in outline:
        number = _extract_outline_number(item["title"])
        level = len(number.split(".")) if number else 1
        key = number or f"page-{item['start_page']}-{len(annotated)}"
        parent_key = None
        if number and "." in number:
            parent_key = ".".join(number.split(".")[:-1])
        elif level > 1:
            parent_key = latest_by_level.get(level - 1)

        item = {
            **item,
            "level": level,
            "key": key,
            "parent_key": parent_key,
        }
        latest_by_level[level] = key
        for deeper_level in [existing for existing in latest_by_level if existing > level]:
            del latest_by_level[deeper_level]
        annotated.append(item)

    return annotated


def _extract_outline_number(title: str) -> str | None:
    chapter_match = re.match(r"^\s*chapter\s+(\d+)\b", title, re.IGNORECASE)
    if chapter_match:
        return chapter_match.group(1)
    match = re.match(r"^\s*(\d+(?:\.\d+)*)\b", title)
    return match.group(1) if match else None


def _outline_number_sort_key(title: str) -> tuple[int, ...]:
    number = _extract_outline_number(title)
    if not number:
        return (9999,)
    return tuple(int(part) for part in number.split(".") if part.isdigit())


def _outline_level(title: str) -> int:
    number = _extract_outline_number(title)
    if not number:
        return 1
    return len(number.split("."))


def _clean_contents_title(title: str) -> str:
    title = re.sub(r"[\x00-\x1f\x7f]", " ", title)
    title = re.sub(r"\.{2,}\s*\d+\s*$", "", title)
    title = re.sub(r"\s+\d+\s*$", "", title)
    return re.sub(r"\s+", " ", title).strip(" -:")


def _is_valid_contents_title(title: str) -> bool:
    cleaned = _clean_contents_title(title)
    if not cleaned or len(cleaned) > 180:
        return False
    return bool(re.match(r"^(?:CHAPTER\s+\d+\b|\d+(?:\.\d+)+\b)", cleaned, re.IGNORECASE))


def _is_excluded_contents_title(title: str) -> bool:
    return bool(re.search(
        r"\b(chapter\s+\d+\s+review|review\s+questions?|questions?\s+and\s+problems?|exercises?|answers?|bibliography|index|appendix|summary\s+of\s+chapter)\b",
        title,
        re.IGNORECASE,
    ))


def _normalize_title(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z가-힣]+", " ", value)
    return re.sub(r"\s+", " ", value).strip().lower()


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
