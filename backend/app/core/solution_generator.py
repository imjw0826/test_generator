import base64
import json
import logging
import mimetypes
from pathlib import Path

import anthropic

from app.config import settings
from app.core.llm_runtime import create_messages_client, selected_model_config
from app.models.question import Question

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Write concise Korean solutions for study questions.
Return only valid JSON as an array of objects:
[{"id": 123, "solution_text": "..."}]
Keep LaTeX math valid and preserve variables, units, and figure references. Do not include Markdown fences."""


def generate_solutions_with_opus(questions: list[Question]) -> dict[int, str]:
    if not questions:
        return {}

    client, model = create_messages_client(settings.llm_solution_model)
    payload = [
        {
            "id": question.id,
            "chapter": question.chapter,
            "question_text": question.question_text,
            "figures": _figure_context(question),
        }
        for question in questions
    ]

    for attempt in range(settings.llm_max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _build_user_content(payload, questions, model)}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            items = json.loads(raw)
            if not isinstance(items, list):
                raise ValueError("Expected a JSON array")

            solutions: dict[int, str] = {}
            for item in items:
                if not isinstance(item, dict):
                    continue
                question_id = int(item["id"])
                solution_text = str(item.get("solution_text") or "").strip()
                if solution_text:
                    solutions[question_id] = solution_text
            return solutions
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.warning(f"Solution generation attempt {attempt + 1} failed: {e}")
            if attempt == settings.llm_max_retries - 1:
                raise
        except anthropic.APIError:
            if attempt == settings.llm_max_retries - 1:
                raise

    return {}


def _figure_context(question: Question) -> list[dict]:
    figures = []
    for figure in question.figure_refs or []:
        figures.append({
            "id": figure.get("id"),
            "label": figure.get("label"),
            "caption": figure.get("caption"),
        })
    return figures


def _build_user_content(payload: list[dict], questions: list[Question], model: str) -> list[dict]:
    content: list[dict] = [
        {
            "type": "text",
            "text": "Generate solutions for these questions:\n"
            + json.dumps(payload, ensure_ascii=False),
        }
    ]

    if not selected_model_config(model).supports_vision:
        return content

    for question in questions:
        for figure in question.figure_refs or []:
            image = _image_block(figure)
            if not image:
                continue
            content.append({
                "type": "text",
                "text": f"Figure {figure.get('id')} for question id {question.id}:",
            })
            content.append(image)

    return content


def _image_block(figure: dict) -> dict | None:
    path = Path(str(figure.get("path") or ""))
    if not path.exists():
        return None

    media_type = mimetypes.guess_type(path.name)[0] or "image/png"
    if media_type not in {"image/jpeg", "image/png", "image/gif", "image/webp"}:
        media_type = "image/png"

    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.b64encode(path.read_bytes()).decode("ascii"),
        },
    }
