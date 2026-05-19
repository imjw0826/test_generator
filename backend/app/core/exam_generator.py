import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.core.random_selector import select_random_questions
from app.core.solution_generator import generate_solutions_with_opus
from app.models.question import Question


PROJECT_NAME = "Study Question Generator"
PROJECT_URL = "imjw0826.github.io"


@dataclass
class GeneratedExam:
    path: Path
    filename: str
    media_type: str


def generate_exam_package(
    db: Session,
    count: int,
    subject: str | None = None,
    chapters: list[str] | None = None,
    include_answers: bool = False,
) -> GeneratedExam:
    questions = select_random_questions(
        db,
        count=count,
        subjects=[subject] if subject else None,
        chapters=chapters,
    )
    if not questions:
        raise ValueError("No questions available for the selected filters.")

    return _generate_exam_from_questions(
        questions=questions,
        subject=subject,
        chapters=chapters,
        include_answers=include_answers,
        filename_suffix="exam",
    )


def generate_solution_exam_package(
    db: Session,
    count: int,
    subject: str | None = None,
    chapters: list[str] | None = None,
) -> GeneratedExam:
    questions = select_random_questions(
        db,
        count=count,
        subjects=[subject] if subject else None,
        chapters=chapters,
    )
    if not questions:
        raise ValueError("No questions available for the selected filters.")

    solutions_by_question_id = generate_solutions_with_opus(questions)
    if not solutions_by_question_id:
        raise ValueError("No solutions were generated.")

    return _generate_exam_from_questions(
        questions=questions,
        subject=subject,
        chapters=chapters,
        include_answers=False,
        solutions_by_question_id=solutions_by_question_id,
        filename_suffix="solutions",
    )


def _generate_exam_from_questions(
    questions: list[Question],
    subject: str | None,
    chapters: list[str] | None,
    include_answers: bool,
    filename_suffix: str,
    solutions_by_question_id: dict[int, str] | None = None,
) -> GeneratedExam:
    actual_subject = subject or _first_present([q.subject for q in questions]) or "Untitled Subject"
    part_label = _part_label(chapters, questions)
    title = f"{actual_subject} ({part_label})" if part_label else actual_subject

    work_dir = settings.generated_exam_path / uuid.uuid4().hex
    work_dir.mkdir(parents=True, exist_ok=True)

    exam_tex = _build_exam_tex(
        title=title,
        questions=questions,
        include_answers=include_answers,
        solutions_by_question_id=solutions_by_question_id,
    )
    exam_pdf = _compile_tex(
        work_dir,
        filename_suffix,
        exam_tex,
    )

    safe_subject = _safe_filename(actual_subject)
    return GeneratedExam(
        path=exam_pdf,
        filename=f"{safe_subject}_{filename_suffix}.pdf",
        media_type="application/pdf",
    )


def _build_exam_tex(
    title: str,
    questions: list[Question],
    include_answers: bool,
    solutions_by_question_id: dict[int, str] | None = None,
) -> str:
    figure_state = {"next_number": 1}
    question_blocks = [
        _question_block(index, question, include_answers, figure_state, solutions_by_question_id)
        for index, question in enumerate(questions, start=1)
    ]
    subtitle = f"{len(questions)} questions | Source: {PROJECT_NAME} ({PROJECT_URL})"

    return "\n".join([
        r"\documentclass[11pt]{article}",
        r"\usepackage[margin=1in]{geometry}",
        r"\usepackage{amsmath,amssymb}",
        r"\usepackage{graphicx}",
        r"\setlength{\parindent}{0pt}",
        r"\setlength{\parskip}{0.6em}",
        r"\begin{document}",
        rf"\begin{{center}}\Large\textbf{{{_latex_escape(title)}}}\\[0.4em]\normalsize {_latex_escape(subtitle)}\end{{center}}",
        r"\vspace{0.5em}",
        *question_blocks,
        r"\end{document}",
        "",
    ])


def _question_block(
    index: int,
    question: Question,
    include_answers: bool,
    figure_state: dict[str, int],
    solutions_by_question_id: dict[int, str] | None = None,
) -> str:
    refs = question.figure_refs or []
    figure_numbers = list(range(figure_state["next_number"], figure_state["next_number"] + len(refs)))
    figure_state["next_number"] += len(refs)

    lines = [rf"\subsection*{{Problem {index}}}"]

    lines.append(_latex_text(question.question_text))
    if figure_numbers:
        joined = ", ".join(f"Figure {number}" for number in figure_numbers)
        lines.append(rf"\textit{{Uses: {joined}.}}")
    lines.extend(_figure_blocks(refs, figure_numbers))

    if include_answers:
        lines.append(r"\textbf{Answer.} " + _latex_text(_stored_answer(question)))

    question_id = getattr(question, "id", None)
    solution = (solutions_by_question_id or {}).get(question_id)
    if solution:
        lines.append(r"\textbf{Solution.} " + _latex_text(solution))

    return "\n".join(lines)


def _figure_blocks(refs: list[dict], figure_numbers: list[int]) -> list[str]:
    blocks: list[str] = []
    figure_root = settings.figure_path.resolve()
    for ref, number in zip(refs, figure_numbers):
        raw_path = str(ref.get("path") or "")
        if not raw_path:
            continue
        try:
            resolved = Path(raw_path).resolve()
            resolved.relative_to(figure_root)
        except (ValueError, OSError):
            continue
        if not resolved.exists():
            continue
        caption = ref.get("caption") or ref.get("label") or f"Figure {number}"
        blocks.extend([
            r"\begin{center}",
            r"\centering",
            rf"\includegraphics[width=0.85\linewidth]{{{_latex_path(str(resolved))}}}",
            rf"\par\small\textit{{Figure {number}. {_latex_escape(str(caption))}}}",
            r"\end{center}",
        ])
    return blocks


def _compile_tex(
    work_dir: Path,
    stem: str,
    tex: str,
) -> Path:
    tex_path = work_dir / f"{stem}.tex"
    tex_path.write_text(tex, encoding="utf-8")

    engine = _find_latex_engine()
    if not engine:
        raise RuntimeError("No LaTeX engine found. Install tectonic or xelatex to generate real LaTeX PDFs.")

    if engine == "tectonic":
        command = [engine, tex_path.name]
        runs = 1
    else:
        command = [
            engine,
            "-no-shell-escape",
            "-interaction=nonstopmode",
            "-halt-on-error",
            tex_path.name,
        ]
        runs = 2

    for _ in range(runs):
        result = subprocess.run(
            command,
            cwd=work_dir,
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )
        if result.returncode != 0:
            raise RuntimeError(f"LaTeX failed: {(result.stderr or result.stdout)[-1200:]}")

    pdf_path = work_dir / f"{stem}.pdf"
    if not pdf_path.exists():
        raise RuntimeError("LaTeX finished without producing a PDF.")
    return pdf_path


def _find_latex_engine() -> str | None:
    for engine in ("tectonic", "xelatex", "lualatex", "pdflatex"):
        if shutil.which(engine):
            return engine
    return None


def _stored_answer(question: Question) -> str:
    answer = getattr(question, "answer_text", None)
    return str(answer).strip() if answer else "No stored answer is available."


def _part_label(chapters: list[str] | None, questions: list[Question]) -> str | None:
    values = chapters or [q.chapter for q in questions if q.chapter]
    cleaned = [str(value).strip() for value in values if value]
    if not cleaned:
        return None

    numeric_parts = [_extract_part_number(value) for value in cleaned]
    numeric_parts = [part for part in numeric_parts if part]
    if numeric_parts:
        ordered = sorted(set(numeric_parts), key=_part_sort_key)
        return ordered[0] if len(ordered) == 1 else f"{ordered[0]}--{ordered[-1]}"

    unique = sorted(set(cleaned))
    return unique[0] if len(unique) == 1 else f"{unique[0]}--{unique[-1]}"


def _extract_part_number(value: str) -> str | None:
    match = re.search(r"\b(\d+(?:\.\d+)*)\b", value)
    return match.group(1) if match else None


def _part_sort_key(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split(".") if part.isdigit())


def _first_present(values: list[str | None]) -> str | None:
    for value in values:
        if value:
            return value
    return None


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")
    return safe or "exam"


MATH_PATTERN = re.compile(r"(\\\(.+?\\\)|\\\[.+?\\\]|\$\$.+?\$\$|\$.+?\$)", re.DOTALL)


def _latex_text(value: str) -> str:
    pieces: list[str] = []
    last = 0
    for match in MATH_PATTERN.finditer(value):
        pieces.append(_latex_plain_text(value[last:match.start()]))
        pieces.append(match.group(0))
        last = match.end()
    pieces.append(_latex_plain_text(value[last:]))
    return "".join(pieces).replace("\n", r"\par " + "\n")


def _latex_plain_text(value: str) -> str:
    pieces: list[str] = []
    last = 0
    for match in re.finditer(r"\*\*(.+?)\*\*", value, flags=re.DOTALL):
        pieces.append(_latex_escape(value[last:match.start()]))
        pieces.append(r"\textbf{" + _latex_escape(match.group(1)) + "}")
        last = match.end()
    pieces.append(_latex_escape(value[last:]))
    return "".join(pieces)


def _latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def _latex_path(value: str) -> str:
    return value.replace("\\", "/").replace(" ", r"\space ")
