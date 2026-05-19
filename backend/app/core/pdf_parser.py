import base64
from dataclasses import dataclass
from pathlib import Path
import re

import fitz  # PyMuPDF


@dataclass
class PageFigure:
    id: str
    page_number: int
    path: str
    url: str
    bbox: list[float]
    label: str | None = None
    caption: str | None = None


@dataclass
class PageText:
    page_number: int
    raw_text: str
    figures: list[PageFigure]


def parse_pdf(
    file_path: str,
    figure_output_dir: Path | None = None,
    figure_url_prefix: str | None = None,
) -> list[PageText]:
    pages: list[PageText] = []
    with fitz.open(file_path) as doc:
        for i, page in enumerate(doc):
            page_number = i + 1
            text, figures = _extract_page_content(
                page=page,
                page_number=page_number,
                figure_output_dir=figure_output_dir,
                figure_url_prefix=figure_url_prefix,
            )
            pages.append(PageText(page_number=page_number, raw_text=text, figures=figures))
    return pages


def get_page_count(file_path: str) -> int:
    with fitz.open(file_path) as doc:
        return len(doc)


def render_page_png_base64(file_path: str, page_number: int, zoom: float = 2.0) -> str:
    with fitz.open(file_path) as doc:
        page = doc.load_page(page_number - 1)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return base64.b64encode(pixmap.tobytes("png")).decode("ascii")


def _extract_page_content(
    page: fitz.Page,
    page_number: int,
    figure_output_dir: Path | None,
    figure_url_prefix: str | None,
) -> tuple[str, list[PageFigure]]:
    page_dict = page.get_text("dict", sort=True)
    blocks = sorted(page_dict.get("blocks", []), key=lambda b: (b["bbox"][1], b["bbox"][0]))

    lines: list[str] = []
    figures: list[PageFigure] = []

    for block in blocks:
        block_type = block.get("type")
        if block_type == 0:
            text = _text_from_block(block)
            if text:
                lines.append(text)
        elif block_type == 1 and figure_output_dir and figure_url_prefix:
            figure = _save_figure_block(block, page_number, len(figures) + 1, figure_output_dir, figure_url_prefix)
            if figure:
                figures.append(figure)
                lines.append(_figure_marker(figure))

    return "\n".join(lines), figures


def _text_from_block(block: dict) -> str:
    text_lines: list[str] = []
    for line in block.get("lines", []):
        line_text = _text_from_line(line)
        if line_text:
            text_lines.append(line_text)
    return "\n".join(text_lines).strip()


def _text_from_line(line: dict) -> str:
    spans = line.get("spans", [])
    if not spans:
        return ""

    baseline = max(_span_origin_y(span) for span in spans)
    normal_size = max(float(span.get("size") or 0) for span in spans)
    parts: list[str] = []

    for span in spans:
        text = str(span.get("text", ""))
        if not text:
            continue

        size = float(span.get("size") or normal_size)
        origin_y = _span_origin_y(span)
        if normal_size and size <= normal_size * 0.85 and origin_y < baseline - normal_size * 0.15:
            parts.append(f"^{{{text}}}")
        else:
            parts.append(text)

    return "".join(parts).strip()


def _span_origin_y(span: dict) -> float:
    origin = span.get("origin")
    if isinstance(origin, (list, tuple)) and len(origin) >= 2:
        return float(origin[1])
    bbox = span.get("bbox") or [0, 0, 0, 0]
    return float(bbox[3])


def _save_figure_block(
    block: dict,
    page_number: int,
    figure_index: int,
    figure_output_dir: Path,
    figure_url_prefix: str,
) -> PageFigure | None:
    image_bytes = block.get("image")
    if not image_bytes:
        return None

    ext = _safe_image_ext(str(block.get("ext") or "png"))
    figure_id = f"p{page_number:03d}_fig{figure_index:02d}"
    file_name = f"{figure_id}.{ext}"
    figure_output_dir.mkdir(parents=True, exist_ok=True)
    figure_path = figure_output_dir / file_name
    figure_path.write_bytes(image_bytes)

    bbox = [round(float(v), 2) for v in block.get("bbox", [])]
    return PageFigure(
        id=figure_id,
        page_number=page_number,
        path=str(figure_path),
        url=f"{figure_url_prefix.rstrip('/')}/{file_name}",
        bbox=bbox,
    )


def _safe_image_ext(ext: str) -> str:
    ext = ext.lower().strip().lstrip(".")
    return ext if re.fullmatch(r"[a-z0-9]{2,5}", ext) else "png"


def _figure_marker(figure: PageFigure) -> str:
    return f'[[FIGURE id="{figure.id}" page="{figure.page_number}" url="{figure.url}"]]'
