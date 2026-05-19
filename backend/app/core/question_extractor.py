import json
import logging
from pathlib import Path

import anthropic

from app.config import settings
from app.core.llm_runtime import create_messages_client

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "extract_questions.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text()

def extract_questions_from_block(
    text: str,
    page_number: int,
    page_image_base64: str | None = None,
) -> list[dict]:
    client, model = create_messages_client(settings.llm_model)

    for attempt in range(settings.llm_max_retries):
        try:
            content = _build_user_content(text, page_number, page_image_base64)
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]

            questions = json.loads(raw)
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


def _build_user_content(text: str, page_number: int, page_image_base64: str | None):
    if page_image_base64:
        text_content = (
            f"Page {page_number}\n\n"
            "Extract all student-solvable questions/problems from this page image. "
            "Read math, numbering, and figures directly from the image."
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
