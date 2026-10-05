import fitz
import pytest

from app.core.chapter_detector import detect_page_chapters
from app.core.pdf_parser import parse_pdf
from app.core.pdf_structure import headings_from_markdown, is_available, start_structure_analysis

requires_pdf_inspector = pytest.mark.skipif(not is_available(), reason="pdf-inspector not installed")


def _textbook_pdf(path) -> str:
    doc = fitz.open()
    first = doc.new_page()
    first.insert_text((72, 80), "Linear Algebra Notes", fontsize=8)
    first.insert_text((72, 120), "CHAPTER 1", fontsize=24)
    first.insert_text((72, 160), "Vectors and Matrices", fontsize=20)
    first.insert_text((72, 200), "1.1 Vector Spaces", fontsize=15)
    first.insert_text((72, 240), "A vector space is a set closed under addition and scalar multiplication.", fontsize=10)
    first.insert_text((72, 255), "We study bases, dimension, and linear maps in this section of the text.", fontsize=10)

    second = doc.new_page()
    second.insert_text((72, 80), "CHAPTER 1  Vectors and Matrices", fontsize=8)
    second.insert_text((72, 120), "Every basis of a finite dimensional space has the same number of vectors.", fontsize=10)
    second.insert_text((72, 135), "1. Show that the columns of an invertible matrix form a basis.", fontsize=10)
    second.insert_text((72, 175), "1.2 Linear Maps", fontsize=15)
    second.insert_text((72, 215), "A linear map preserves addition and scalar multiplication of vectors.", fontsize=10)

    third = doc.new_page()
    scan_source = fitz.open()
    scan_page = scan_source.new_page()
    scan_page.insert_text((72, 100), "2.1 Scanned Section " * 3, fontsize=12)
    third.insert_image(third.rect, pixmap=scan_page.get_pixmap(dpi=100))

    file_path = str(path / "textbook.pdf")
    doc.save(file_path)
    return file_path


def test_headings_are_read_from_markdown_headings_and_bold_lines():
    markdown = "\n".join([
        "*Running header in italics*",
        "# CHAPTER 1",
        "## **Vectors** and [Matrices](https://example.com)",
        "Body text that mentions 1.2 Linear Maps inline.",
        "**1.2 Linear Maps**",
        "1. A numbered question **with bold** words",
        "| 1.3 | table cell |",
    ])

    assert headings_from_markdown(markdown) == ["CHAPTER 1", "Vectors and Matrices", "1.2 Linear Maps"]


@requires_pdf_inspector
def test_structure_analysis_reports_headings_and_scanned_pages(tmp_path):
    job = start_structure_analysis(_textbook_pdf(tmp_path), timeout=60)

    structure = job.result()

    assert structure[1].headings == ["CHAPTER 1", "Vectors and Matrices", "1.1 Vector Spaces"]
    assert structure[2].headings == ["1.2 Linear Maps"]
    assert not structure[1].needs_ocr
    assert structure[3].needs_ocr
    assert structure[3].headings == []


@requires_pdf_inspector
def test_structure_analysis_failure_and_timeout_return_none(tmp_path):
    assert start_structure_analysis(str(tmp_path / "missing.pdf"), timeout=60).result() is None
    assert start_structure_analysis(_textbook_pdf(tmp_path), timeout=0).result() is None


@requires_pdf_inspector
def test_parse_pdf_keeps_pymupdf_text_and_tags_chapters_from_headings(tmp_path):
    pages = parse_pdf(_textbook_pdf(tmp_path), analyze_structure=True)

    # Stored text keeps PyMuPDF's line structure, so numbered questions stay on their own line.
    assert "\n1. Show that the columns of an invertible matrix form a basis." in pages[1].raw_text
    assert pages[0].headings == ["CHAPTER 1", "Vectors and Matrices", "1.1 Vector Spaces"]
    assert pages[2].needs_ocr
    # The running header on page 2 no longer overrides the section headings.
    assert detect_page_chapters(pages) == {
        1: "1.1 Vector Spaces",
        2: "1.2 Linear Maps",
        3: "1.2 Linear Maps",
    }


def test_parse_pdf_without_structure_analysis_leaves_headings_unset(tmp_path):
    pages = parse_pdf(_textbook_pdf(tmp_path), analyze_structure=False)

    assert [page.headings for page in pages] == [None, None, None]
    assert not any(page.needs_ocr for page in pages)
