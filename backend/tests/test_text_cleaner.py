from app.core.text_cleaner import clean_text, detect_headers_footers, _is_page_number_only


def test_clean_text_removes_page_numbers():
    raw = "123\nSome content here\n456"
    result = clean_text(raw)
    assert "123" not in result
    assert "456" not in result
    assert "Some content here" in result


def test_clean_text_removes_headers():
    raw = "BIOLOGY 101\nActual content here"
    result = clean_text(raw, headers={"BIOLOGY 101"})
    assert "BIOLOGY 101" not in result
    assert "Actual content here" in result


def test_clean_text_removes_footers():
    raw = "Content\nCopyright 2024"
    result = clean_text(raw, footers={"Copyright 2024"})
    assert "Copyright 2024" not in result
    assert "Content" in result


def test_clean_text_fixes_hyphenated_words():
    raw = "This is a hyphen-\nated word"
    result = clean_text(raw)
    assert "hyphenated" in result


def test_clean_text_normalizes_whitespace():
    raw = "Too   many    spaces"
    result = clean_text(raw)
    assert "Too many spaces" in result


def test_clean_text_collapses_blank_lines():
    raw = "Line 1\n\n\n\n\nLine 2"
    result = clean_text(raw)
    assert "\n\n\n" not in result


def test_detect_headers_footers():
    pages = [
        "Header Line\nContent page 1\nFooter Line",
        "Header Line\nContent page 2\nFooter Line",
        "Header Line\nContent page 3\nFooter Line",
        "Header Line\nContent page 4\nFooter Line",
    ]
    headers, footers = detect_headers_footers(pages)
    assert "Header Line" in headers
    assert "Footer Line" in footers


def test_detect_headers_footers_too_few_pages():
    pages = ["Page 1", "Page 2"]
    headers, footers = detect_headers_footers(pages)
    assert len(headers) == 0
    assert len(footers) == 0


def test_is_page_number_only():
    assert _is_page_number_only("42") is True
    assert _is_page_number_only("1") is True
    assert _is_page_number_only("9999") is True
    assert _is_page_number_only("12345") is False
    assert _is_page_number_only("abc") is False
    assert _is_page_number_only("12 ") is False
