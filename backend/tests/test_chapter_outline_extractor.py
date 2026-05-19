from app.core.chapter_outline_extractor import (
    _iter_numbered_contents_entries,
    _resolve_contents_entries_to_page_ranges,
)
from app.models.parsed_page import ParsedPage


def _page(page_number: int, raw_text: str = "") -> ParsedPage:
    return ParsedPage(
        document_id=1,
        page_number=page_number,
        raw_text=raw_text,
        cleaned_text=raw_text,
        section_hint=None,
        figures=[],
    )


def test_contents_parser_recovers_multiline_chapter_and_sections():
    contents_text = """
PDF PAGE 20
CHAPTER 8
Linear Algebra: Matrix Eigenvalue Problems      322
8.1
The Matrix Eigenvalue Problem.
Determining Eigenvalues and Eigenvectors
323
8.2
Some Applications of Eigenvalue Problems
329
8.3
Symmetric, Skew-Symmetric, and Orthogonal Matrices
334
Chapter 8 Review Questions and Problems
352
Summary of Chapter 8
353
"""

    entries = _iter_numbered_contents_entries(contents_text)

    assert {entry["title"] for entry in entries} == {
        "CHAPTER 8 Linear Algebra: Matrix Eigenvalue Problems",
        "8.1 The Matrix Eigenvalue Problem Determining Eigenvalues and Eigenvectors",
        "8.2 Some Applications of Eigenvalue Problems",
        "8.3 Symmetric, Skew-Symmetric, and Orthogonal Matrices",
    }
    assert [entry["page_label"] for entry in entries] == ["322", "323", "329", "334"]


def test_contents_resolution_prefers_consistent_page_offset_over_false_title_match():
    pages = [_page(page_number) for page_number in range(1, 381)]
    pages[19] = _page(20, "CHAPTER 8\nLinear Algebra: Matrix Eigenvalue Problems      322")
    pages[280] = _page(281, "Preface note mentioning Linear Algebra: Matrix Eigenvalue Problems")
    pages[348] = _page(
        349,
        "8.1 The Matrix Eigenvalue Problem Determining Eigenvalues and Eigenvectors",
    )

    entries = [
        {"title": "CHAPTER 8 Linear Algebra: Matrix Eigenvalue Problems", "page_label": "322"},
        {
            "title": "8.1 The Matrix Eigenvalue Problem Determining Eigenvalues and Eigenvectors",
            "page_label": "323",
        },
    ]

    outline = _resolve_contents_entries_to_page_ranges(entries, pages, contents_pages=[pages[19]])

    assert outline[0]["title"] == "CHAPTER 8 Linear Algebra: Matrix Eigenvalue Problems"
    assert outline[0]["start_page"] == 348
    assert outline[1]["start_page"] == 349
