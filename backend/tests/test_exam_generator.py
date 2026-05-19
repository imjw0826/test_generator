from types import SimpleNamespace

from app.core.exam_generator import _build_exam_tex, _latex_text, _part_label


def test_latex_text_escapes_plain_text_but_preserves_math():
    result = _latex_text(r"Find x_1 if \(x_1 + y = 2\) and 50% is known.")

    assert r"x\_1" in result
    assert r"\(x_1 + y = 2\)" in result
    assert r"50\%" in result


def test_latex_text_converts_markdown_bold_outside_math():
    result = _latex_text(r"Find **the value** of \(**x** + 1\).")

    assert r"\textbf{the value}" in result
    assert r"\(**x** + 1\)" in result
    assert "**the value**" not in result


def test_part_label_uses_numeric_chapter_range():
    questions = [
        SimpleNamespace(chapter="Section 2.5"),
        SimpleNamespace(chapter="Section 2.3"),
        SimpleNamespace(chapter="Section 2.4"),
    ]

    assert _part_label(None, questions) == "2.3--2.5"


def test_build_exam_tex_includes_header_question_and_figure_labels():
    question = SimpleNamespace(
        question_text=r"Solve \(x^2=4\).",
        figure_refs=[{"path": "/missing/figure.png", "caption": "Graph"}],
    )

    tex = _build_exam_tex(
        title="Math (2.3--2.5)",
        questions=[question],
        include_answers=True,
    )

    assert "Math (2.3--2.5)" in tex
    assert "1 questions" in tex
    assert "Study Question Generator" in tex
    assert r"Solve \(x^2=4\)." in tex
    assert "Uses: Figure 1." in tex
    assert "No stored answer is available." in tex
