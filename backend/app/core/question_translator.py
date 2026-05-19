import logging

from app.config import settings
from app.core.llm_runtime import create_messages_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Translate study questions into Korean.
Preserve the original structure, numbering, line breaks, LaTeX delimiters, LaTeX commands, equations, units, and figure markers.
Translate only natural-language prose. Do not solve the problem.
Wrap every mathematical expression in LaTeX inline delimiters \\( ... \\), and keep a normal space between Korean text and each math expression.
Do not add Markdown formatting. If the source contains Markdown such as **bold**, remove the Markdown markers and translate the text naturally.
Return only the translated question text."""


def translate_question_to_korean(question_text: str) -> str:
    client, model = create_messages_client(settings.llm_translation_model)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question_text}],
    )
    translated = response.content[0].text.strip()
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
