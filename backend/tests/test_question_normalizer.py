from app.core.question_normalizer import normalize_question_text


def test_removes_leading_number_dot():
    assert normalize_question_text("1. What is a cell?") == "what is a cell?"


def test_removes_leading_number_paren():
    assert normalize_question_text("3) Describe mitosis.") == "describe mitosis."


def test_removes_leading_letter():
    assert normalize_question_text("a. Sub question") == "sub question"


def test_normalizes_whitespace():
    assert normalize_question_text("  too   many   spaces  ") == "too many spaces"


def test_lowercases():
    assert normalize_question_text("What Is DNA?") == "what is dna?"


def test_plain_text_unchanged():
    assert normalize_question_text("simple question") == "simple question"
