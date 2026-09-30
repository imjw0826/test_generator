import json
import logging
from pathlib import Path

import anthropic

from app.config import settings
from app.core.llm_runtime import create_text_message

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "extract_questions.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text()

def extract_questions_from_block(
    text: str,
    page_number: int,
    page_image_base64: str | None = None,
    figures: list[dict] | None = None,
) -> list[dict]:
    for attempt in range(settings.llm_max_retries):
        try:
            content = _build_user_content(text, page_number, page_image_base64, figures)
            raw = create_text_message(
                settings.llm_model,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
                max_tokens=16000,
                effort=settings.llm_extraction_effort,
            )
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]

            questions = json.loads(_repair_json_escapes(raw))
            if not isinstance(questions, list):
                raise ValueError("Expected a JSON array")

            validated = []
            for q in questions:
                if not isinstance(q, dict):
                    continue
                if "question_text" not in q or not q["question_text"].strip():
                    continue
                q.setdefault("question_number", None)
                q.setdefault("figure_ids", [])
                q.setdefault("confidence", 0.5)
                if not isinstance(q["figure_ids"], list):
                    q["figure_ids"] = []
                q["figure_ids"] = [str(figure_id) for figure_id in q["figure_ids"][:10]]
                validated.append(q)

            return validated

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"LLM extraction attempt {attempt + 1} failed: {e}")
            continue
        except anthropic.APIStatusError as e:
            logger.error(f"Anthropic API error (status {e.status_code}): {e}")
            # Non-retryable errors: billing, auth, permissions
            if e.status_code in (400, 401, 403):
                raise
            if attempt == settings.llm_max_retries - 1:
                raise
            continue
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            if attempt == settings.llm_max_retries - 1:
                raise
            continue

    return []


def _build_user_content(
    text: str,
    page_number: int,
    page_image_base64: str | None,
    figures: list[dict] | None = None,
):
    if page_image_base64:
        text_content = (
            f"Page {page_number}\n\n"
            "Extract all student-solvable questions/problems from this page image. "
            "Read math, numbering, and figures directly from the image."
        )
        manifest = _figure_manifest(figures)
        if manifest:
            text_content += (
                "\n\nFigures detected on this page (each entry is id + location in the "
                "image). For every question, set figure_ids to the IDs of the figures "
                "that visually belong to that question, judging by their position. A "
                "figure usually belongs to the question whose text it sits within or "
                "directly beside. Use only IDs from this list; omit unrelated ones.\n"
                f"{manifest}"
            )
        return [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": page_image_base64,
                },
            },
            {"type": "text", "text": text_content},
        ]

    return (
        f"Page {page_number}\n\n"
        "Extract all student-solvable questions/problems from this text.\n\n"
        f"{text}"
    )


def _figure_manifest(figures: list[dict] | None) -> str:
    if not figures:
        return ""
    lines = []
    for figure in figures:
        figure_id = str(figure.get("id", "")).strip()
        if not figure_id:
            continue
        position = figure.get("position") or "position unknown"
        lines.append(f'- id="{figure_id}" — {position}')
    return "\n".join(lines)


def _repair_json_escapes(raw: str) -> str:
    """Scan character-by-character and double any backslash that does not form
    a valid JSON escape sequence.

    Valid JSON escapes after backslash:
      "  \\  /  b  f  n  r  t  uXXXX (exactly 4 hex digits)

    LaTeX commands like \\frac, \\sqrt, \\(, \\[ contain backslashes that are
    illegal in JSON strings.  This function fixes them so json.loads succeeds.

    Regex-based approaches fail when the LLM has already doubled some
    backslashes (e.g. \\\\sqrt) because the regex incorrectly re-processes
    the second backslash.  A character-by-character scanner avoids that.
    """
    _SIMPLE = frozenset('"' + '\\' + '/' + 'b' + 'f' + 'n' + 'r' + 't')
    _HEX = frozenset('0123456789abcdefABCDEF')

    out: list[str] = []
    i = 0
    n = len(raw)
    while i < n:
        ch = raw[i]
        if ch != '\\':
            out.append(ch)
            i += 1
            continue

        # ch is a backslash — decide whether it starts a valid escape
        if i + 1 >= n:
            # trailing backslash — double it
            out.append('\\\\')
            i += 1
            continue

        nxt = raw[i + 1]
        if nxt in _SIMPLE:
            # valid 2-char escape: keep as-is
            out.append(ch)
            out.append(nxt)
            i += 2
        elif nxt == 'u':
            # valid only if followed by exactly 4 hex digits
            hex_slice = raw[i + 2: i + 6]
            if len(hex_slice) == 4 and all(c in _HEX for c in hex_slice):
                out.append(raw[i: i + 6])
                i += 6
            else:
                # invalid \uXXX — double the backslash, leave 'u' for next iter
                out.append('\\\\')
                i += 1
        else:
            # any other char after backslash is invalid — double the backslash
            out.append('\\\\')
            i += 1

    return ''.join(out)
