import logging

from app.config import settings
from app.core.llm_runtime import create_text_message

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Translate study questions into Korean.
Preserve the original structure, numbering, line breaks, LaTeX delimiters, LaTeX commands, equations, units, and figure markers.
Translate only natural-language prose. Do not solve the problem.
Wrap every mathematical expression in LaTeX inline delimiters \\( ... \\), and keep a normal space between Korean text and each math expression.
Do not add Markdown formatting. If the source contains Markdown such as **bold**, remove the Markdown markers and translate the text naturally.
Return only the translated question text."""


def translate_question_to_korean(question_text: str) -> str:
    translated = create_text_message(
        settings.llm_translation_model,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question_text}],
        max_tokens=8000,
        effort=settings.llm_translation_effort,
    )
    if translated.startswith("```"):
        translated = translated.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return _cleanup_translation(translated)


def _cleanup_translation(text: str) -> str:
    return (
        text
        .replace("** ", "**")
        .replace(" **", "**")
        .replace("**", "")
        .strip()
    )
