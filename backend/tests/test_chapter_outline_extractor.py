from app.core.chapter_outline_extractor import (
    _entries_from_payload,
    _iter_numbered_contents_entries,
    _resolve_contents_entries_to_page_ranges,
    _select_contents_pages,
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


def test_body_pages_are_not_selected_as_contents_pages():
    pages = [
        _page(1, "Cover"),
        _page(
            2,
            "\n".join([
                "CHAPTER 1 First-Order ODEs",
                "1.1 Basic Concepts. Modeling",
                "Physical System If we want to solve an engineering problem",
                "we first have to formulate the problem as a mathematical expression.",
            ]),
        ),
        _page(
            3,
            "\n".join([
                "1.2 Geometric Meaning of y' = f(x, y)",
                "Direction fields are useful for understanding solutions.",
                "This page has section headings, but it is not a contents page.",
            ]),
        ),
    ]

    assert _select_contents_pages(pages) == []


def test_llm_payload_rejects_long_body_paragraphs_disguised_as_chapters():
    payload = [
        {
            "title": (
                "Chapter 1 begins the study of ordinary differential equations "
                "by deriving them from physical problems and interpreting solutions "
                "and their graphs in terms of a given problem. This is body prose, not contents."
            ),
            "page_label": "2",
        },
        {"title": "CHAPTER 1 First-Order ODEs", "page_label": "2"},
    ]

    assert _entries_from_payload(payload) == [
        {"title": "CHAPTER 1 First-Order ODEs", "page_label": "2"}
    ]


def test_contents_entries_drop_dot_leaders_and_accept_spaced_page_numbers():
    contents_text = "\n".join([
        "PDF PAGE 2",
        "CHAPTER 1 Vectors and Matrices ..................",
        "1",
        "1.1 Vector Spaces ........ 3",
        "1.2 Linear Maps . . . . . . . 7",
    ])

    entries = _iter_numbered_contents_entries(contents_text)

    assert entries == [
        {"title": "CHAPTER 1 Vectors and Matrices", "page_label": "1"},
        {"title": "1.1 Vector Spaces", "page_label": "3"},
        {"title": "1.2 Linear Maps", "page_label": "7"},
    ]


def test_chapter_starting_right_after_contents_is_not_swallowed_by_contents_window():
    contents = "\n".join([
        "Contents",
        "CHAPTER 1 Vectors ........ 1",
        "1.1 Vector Spaces ........ 1",
        "1.2 Linear Maps ........ 3",
        "CHAPTER 2 Matrices ........ 5",
    ])
    pages = [
        _page(1, "Title page"),
        _page(2, contents),
        _page(3, "CHAPTER 1\nVectors\n1.1 Vector Spaces\nA vector space is a set."),
        _page(4, "More on vector spaces."),
        _page(5, "1.2 Linear Maps\nA linear map preserves sums."),
        _page(6, "Exercises"),
        _page(7, "CHAPTER 2\nMatrices\nA matrix is a rectangular array."),
    ]

    contents_pages = _select_contents_pages(pages)
    entries = _iter_numbered_contents_entries(contents)
    outline = _resolve_contents_entries_to_page_ranges(entries, pages, contents_pages=contents_pages)

    assert [page.page_number for page in contents_pages] == [2]
    assert [(item["title"], item["start_page"]) for item in outline] == [
        ("CHAPTER 1 Vectors", 3),
        ("1.1 Vector Spaces", 3),
        ("1.2 Linear Maps", 5),
        ("CHAPTER 2 Matrices", 7),
    ]
