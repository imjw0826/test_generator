"""Layout analysis with pdf-inspector, run beside the PyMuPDF text/figure pass.

PyMuPDF stays the source of stored page text and figures: it keeps numbered
questions on their own lines, which pdf-inspector's paragraph reflow does not.
pdf-inspector contributes what PyMuPDF text lacks:

- headings detected from font size/weight (used for chapter detection), and
- per-page flags for scanned pages or broken font encodings.

The pdf-inspector call holds the GIL and is pathologically slow on some
table-heavy PDFs, so it runs in a child process: it overlaps with the PyMuPDF
pass, and a timeout kills it without stalling document processing.
"""

import importlib.util
import json
import logging
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
BOLD_LINE_PATTERN = re.compile(r"^\*\*(.+?)\*\*$")
EMPHASIS_PATTERN = re.compile(r"(?<![\w*])(\*{1,3})(\S(?:.*?\S)?)\1(?![\w*])")
LINK_PATTERN = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
MAX_HEADING_LENGTH = 200

# Self-contained so the child never imports the app (or re-runs a caller's
# __main__, as multiprocessing's spawn would). Prints one JSON document.
_WORKER_SOURCE = """
import json, sys
import pdf_inspector
result = pdf_inspector.extract_pages_markdown(sys.argv[1])
json.dump(
    [[p.page + 1, "" if p.needs_ocr else p.markdown, bool(p.needs_ocr), p.ocr_reason] for p in result.pages],
    sys.stdout,
)
"""


@dataclass
class PageStructure:
    page_number: int
    headings: list[str] = field(default_factory=list)
    needs_ocr: bool = False
    ocr_reason: str | None = None


def is_available() -> bool:
    return importlib.util.find_spec("pdf_inspector") is not None


def headings_from_markdown(markdown: str) -> list[str]:
    headings: list[str] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        match = HEADING_PATTERN.match(stripped)
        text = match.group(2) if match else None
        if text is None:
            bold = BOLD_LINE_PATTERN.match(stripped)
            text = bold.group(1) if bold else None
        if text is None:
            continue
        text = _plain_inline(text)
        if text and len(text) <= MAX_HEADING_LENGTH:
            headings.append(text)
    return headings


def _plain_inline(text: str) -> str:
    text = LINK_PATTERN.sub(r"\1", text)
    text = EMPHASIS_PATTERN.sub(r"\2", text)
    return re.sub(r"\s+", " ", text).strip()


class StructureJob:
    """Handle for an analysis running in a child process."""

    def __init__(self, process: subprocess.Popen, stderr_file, timeout: float):
        self._process = process
        self._stderr_file = stderr_file
        self._started = time.monotonic()
        self._deadline = self._started + timeout

    def result(self, max_wait: float | None = None) -> dict[int, PageStructure] | None:
        """Collect the analysis, waiting at most `max_wait` more seconds and never
        past the overall timeout; None (with the child killed) when it is late."""
        remaining = max(0.0, self._deadline - time.monotonic())
        if max_wait is not None:
            remaining = min(remaining, max_wait)
        try:
            stdout, _ = self._process.communicate(timeout=remaining)
        except subprocess.TimeoutExpired:
            logger.warning(
                "pdf-inspector analysis still running after %.1fs; using PyMuPDF heuristics only.",
                time.monotonic() - self._started,
            )
            self.cancel()
            return None

        try:
            if self._process.returncode != 0:
                logger.warning("pdf-inspector analysis failed: %s", self._stderr_tail() or self._process.returncode)
                return None
            payload = json.loads(stdout)
        except json.JSONDecodeError as e:
            logger.warning("pdf-inspector analysis returned invalid output: %s", e)
            return None
        finally:
            self._stderr_file.close()
        return {
            page_number: PageStructure(
                page_number=page_number,
                headings=headings_from_markdown(markdown),
                needs_ocr=needs_ocr,
                ocr_reason=ocr_reason,
            )
            for page_number, markdown, needs_ocr, ocr_reason in payload
        }

    def cancel(self) -> None:
        if self._process.poll() is None:
            self._process.kill()
        self._process.communicate()
        self._stderr_file.close()

    def _stderr_tail(self) -> str:
        self._stderr_file.seek(0)
        lines = self._stderr_file.read().decode("utf-8", "replace").strip().splitlines()
        return lines[-1] if lines else ""


def start_structure_analysis(file_path: str, timeout: float) -> StructureJob | None:
    if not is_available():
        return None
    # A file, not a pipe: a chatty child must never block on a full stderr pipe
    # while the parent is still busy with the PyMuPDF pass.
    stderr_file = tempfile.TemporaryFile()
    try:
        process = subprocess.Popen(
            [sys.executable, "-c", _WORKER_SOURCE, file_path],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=stderr_file,
        )
    except OSError as e:
        stderr_file.close()
        logger.warning("Could not start pdf-inspector analysis: %s", e)
        return None
    return StructureJob(process, stderr_file, timeout)
