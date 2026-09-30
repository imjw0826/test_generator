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
