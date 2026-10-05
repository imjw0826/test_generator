from app.core.chapter_detector import detect_page_chapters
from app.core.pdf_parser import PageText


def _page(number: int, text: str) -> PageText:
    return PageText(page_number=number, raw_text=text, figures=[])


def test_textbook_section_heading_is_detected():
    pages = [
        _page(1, "SEC. 2.5\nEuler–Cauchy Equations\n71\n2.5 Euler–Cauchy Equations\nEuler–Cauchy equations are ODEs"),
        _page(2, "72\nCHAP. 2\nSecond-Order Linear ODEs\nCase II."),
    ]
    assert detect_page_chapters(pages) == {1: "2.5 Euler–Cauchy Equations", 2: "2.5 Euler–Cauchy Equations"}


def test_numbered_problems_do_not_become_chapters():
    pages = [
        _page(1, "CHAPTER 6 PROBLEMS\nCONCEPT-STUDY GUIDE PROBLEMS\n6.1 When a substance has completed a cycle, v, u,"),
        _page(2, "HOMEWORK PROBLEMS\nEntropy of a Pure Substance\n6.13 Determine the entropy for these states.\n6.21 Do Problem 6.20 using\n6.22 Air"),
        _page(3, "6.27 A 1 kg steel piston/cylinder contains ammonia at\n50C, 20% quality.\n6.28 Water in a piston\n6.29 Air"),
        _page(4, "6.110 Water in a piston/cylinder, shown in Fig. P6.110, is\nat 1 MPa"),
    ]
    chapters = detect_page_chapters(pages)
    assert set(chapters.values()) == {"CHAPTER 6 PROBLEMS"}


def _analysed_page(number: int, text: str, headings: list[str]) -> PageText:
    return PageText(page_number=number, raw_text=text, figures=[], headings=headings)


def test_font_headings_combine_split_chapter_titles_and_ignore_running_headers():
    pages = [
        _analysed_page(1, "Contents\n1 Vectors 3", ["Contents"]),
        _analysed_page(2, "CHAPTER 1\nVectors and Matrices", ["CHAPTER 1", "Vectors and Matrices", "Example 1"]),
        _analysed_page(3, "CHAPTER 1  Vectors and Matrices\n2.5 kg of sand is poured", []),
        _analysed_page(4, "CHAPTER 1  Vectors and Matrices\n1.2 Linear Maps", ["1.2 Linear Maps", "EXERCISES"]),
        _analysed_page(5, "CHAPTER 1  Vectors and Matrices\n3 Apples Are Counted", []),
    ]

    assert detect_page_chapters(pages) == {
        1: None,
        2: "CHAPTER 1 Vectors and Matrices",
        3: "CHAPTER 1 Vectors and Matrices",
        4: "1.2 Linear Maps",
        5: "1.2 Linear Maps",
    }


def test_text_lines_are_used_when_font_headings_carry_no_chapters():
    pages = [
        _analysed_page(1, "2.5 Euler–Cauchy Equations\nEuler–Cauchy equations are ODEs", ["Example 1"]),
        _analysed_page(2, "2.6 Existence and Uniqueness\nTheory of solutions", []),
    ]

    assert detect_page_chapters(pages) == {1: "2.5 Euler–Cauchy Equations", 2: "2.6 Existence and Uniqueness"}
