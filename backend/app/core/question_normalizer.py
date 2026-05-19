import re


def normalize_question_text(text: str) -> str:
    normalized = text.strip()
    normalized = re.sub(r"^\s*\d+[\.\)]\s*", "", normalized)
    normalized = re.sub(r"^\s*[a-zA-Z][\.\)]\s*", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.lower()
    return normalized
