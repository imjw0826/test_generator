from app.core.candidate_detector import detect_candidates


def test_detects_exercise_section():
    pages = [
        (1, "Introduction to biology"),
        (2, "Exercises\n1. What is a cell?\n2. Describe mitosis."),
    ]
    candidates = detect_candidates(pages)
    assert len(candidates) == 1
    assert candidates[0].page_number == 2
    assert "Exercises" in (candidates[0].section_hint or "")


def test_detects_review_questions():
    pages = [
        (1, "Review Questions\n1. Define osmosis.\n2. Explain diffusion."),
    ]
    candidates = detect_candidates(pages)
    assert len(candidates) == 1
    assert candidates[0].section_hint is not None
    assert "review" in candidates[0].section_hint.lower()


def test_detects_numbered_questions_without_keyword():
    pages = [
        (1, "1. First question here?\n2. Second question?\n3. Third question?"),
    ]
    candidates = detect_candidates(pages)
    assert len(candidates) == 1


def test_skips_short_pages():
    pages = [
        (1, "Short"),
        (2, ""),
    ]
    candidates = detect_candidates(pages)
    assert len(candidates) == 0


def test_skips_non_question_content():
    pages = [
        (1, "This is a long paragraph about biology that doesn't contain any questions or exercise markers and has no numbered items."),
    ]
    candidates = detect_candidates(pages)
    assert len(candidates) == 0


def test_multiple_pages():
    pages = [
        (1, "Chapter 1 text"),
        (2, "Exercises\n1. Q1\n2. Q2"),
        (3, "Chapter 2 text"),
        (4, "Problems\n1. P1\n2. P2\n3. P3"),
    ]
    candidates = detect_candidates(pages)
    assert len(candidates) == 2
    assert candidates[0].page_number == 2
    assert candidates[1].page_number == 4
