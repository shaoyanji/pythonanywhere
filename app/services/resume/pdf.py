"""Resume PDF through pdfcpu, not Typst.

Typst is not available in the PythonAnywhere sandbox; pdfcpu is a single static
binary at ``~/.local/bin/pdfcpu`` there. The pipeline is

    variant resume.json -> translator -> pdfcpu JSON -> create -> validate
    -> optimize -> variants/<name>/build/resume.pdf

and it is deliberately dull: a clean single column, one font family, manual page
breaks. A valid readable PDF beats a pretty broken one.

Layout is computed here rather than by pdfcpu, because pdfcpu's text elements do
not wrap: every line is an absolutely positioned ``text`` element, so a wrong
line height is visible as overlap in exactly one place and nowhere else. Widths
are estimated from a small character-class table (no font binary, no AFM file) —
good enough to keep prose inside the margin, and the reason text can run a few
points short of the right edge.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app

from app.services.resume import store

# A4 in points, which is pdfcpu's default page size.
PAGE_WIDTH = 595.0
PAGE_HEIGHT = 842.0
MARGIN_X = 56.0
TOP_Y = 780.0
BOTTOM_Y = 64.0
TEXT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X

SIZE_NAME = 16.0
SIZE_TITLE = 11.0
SIZE_META = 9.0
SIZE_HEADING = 10.5
SIZE_BODY = 9.5

LEADING = 1.32

_NARROW = set("iljtfr.,;:'|!()[]{} ")
_WIDE = set("mwMW@%&")


class PdfError(Exception):
    pass


def pdfcpu_binary() -> str:
    """Resolve pdfcpu: explicit config, PATH, then the sandbox's user bin."""
    configured = current_app.config.get("PDFCPU_BIN")
    if configured:
        return str(configured)
    found = shutil.which("pdfcpu")
    if found:
        return found
    fallback = Path(os.path.expanduser("~/.local/bin/pdfcpu"))
    if fallback.is_file():
        return str(fallback)
    raise PdfError(
        "pdfcpu not found: install it into ~/.local/bin (eget MrRio/pdfcpu) or set PDFCPU_BIN"
    )


def ensure_pdfcpu() -> str:
    """Return a usable pdfcpu path, fetching a release binary with eget if the
    binary is absent. Never builds from source: a Go toolchain on the sandbox is
    not something this feature should need."""
    try:
        return pdfcpu_binary()
    except PdfError:
        pass

    target_dir = Path(os.path.expanduser("~/.local/bin"))
    target_dir.mkdir(parents=True, exist_ok=True)
    eget = shutil.which("eget")
    if not eget:
        raise PdfError(
            "pdfcpu is missing and eget is not installed: put pdfcpu on PATH (or in "
            "~/.local/bin) or install eget and re-run"
        )

    # eget picks the release asset for this OS/arch; archive extraction is left to
    # eget's own defaults, so a failure surfaces as a missing binary below rather
    # than a silent half-install.
    subprocess.run([eget, "MrRio/pdfcpu", "--to", str(target_dir)], check=False, capture_output=True, text=True)
    candidate = target_dir / "pdfcpu"
    if candidate.is_file():
        candidate.chmod(0o755)
        return str(candidate)
    raise PdfError(
        f"eget did not produce {candidate}: fetch the pdfcpu release binary by hand and place it there"
    )


def _char_width(character: str, size: float, bold: bool) -> float:
    if character in _NARROW:
        factor = 0.31
    elif character in _WIDE:
        factor = 0.85
    else:
        factor = 0.53
    width = size * factor
    return width * 1.06 if bold else width


def _measure(text: str, size: float, bold: bool = False) -> float:
    return sum(_char_width(character, size, bold) for character in text)


def _pt(size: float) -> int:
    """pdfcpu's text ``font.size`` is an integer field.

    0.11.1 rejects a float with ``json: cannot unmarshal number 16.0 into Go
    struct field FormFont.Pages.Content.text.Font.Size of type int``, and the
    build then fails after the content JSON has already been written. Rounding
    once, here, keeps measurement and output on the same number instead of
    serialising a size the renderer never used.
    """
    return int(round(size))


def wrap(text: str, width: float, size: float, bold: bool = False) -> list[str]:
    """Greedy word wrap against the estimated width. Words longer than the line
    are hard-split rather than allowed to overflow the margin."""
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if _measure(candidate, size, bold) <= width or not current:
            if _measure(candidate, size, bold) > width and not current:
                chunk = ""
                for character in word:
                    if _measure(chunk + character, size, bold) > width and chunk:
                        lines.append(chunk)
                        chunk = character
                    else:
                        chunk += character
                current = chunk
            else:
                current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


class _Canvas:
    """Accumulates pages of absolutely positioned text elements."""

    def __init__(self) -> None:
        self.pages: list[list[dict]] = []
        self.page: list[dict] = []
        self.y = TOP_Y

    def _break(self) -> None:
        self.pages.append(self.page)
        self.page = []
        self.y = TOP_Y

    def ensure(self, needed: float) -> None:
        if self.y - needed < BOTTOM_Y:
            self._break()

    def text(self, value: str, x: float, size: float, y: float | None = None, bold: bool = False) -> None:
        line = {
            "value": value,
            "position": [round(x, 2), round(self.y if y is None else y, 2)],
            "font": {"name": "Helvetica-Bold" if bold else "Helvetica", "size": _pt(size)},
        }
        self.page.append(line)

    def line(self, value: str, size: float, bold: bool = False, x: float = MARGIN_X, indent: float = 0.0) -> None:
        size = _pt(size)
        for index, chunk in enumerate(wrap(value, TEXT_WIDTH - indent, size, bold)):
            self.ensure(size * LEADING)
            self.text(chunk, x + indent, size, bold=bold)
            self.y -= size * LEADING
        self.y -= size * 0.18

    def heading(self, value: str) -> None:
        # No rule under the heading: in the 0.16.1 JSON model a ``rect`` is a
        # textbox container and ``create`` rejects it without a font definition
        # ("content: pools: textbox missing font definition"). Rather than guess
        # at a schema that may change again, headings separate by weight and case.
        heading = _pt(SIZE_HEADING)
        self.ensure(heading * 3)
        self.y -= 4
        self.text(value.upper(), MARGIN_X, heading, bold=True)
        self.y -= heading * LEADING

    def bullet(self, value: str) -> None:
        indent = 11.0
        body = _pt(SIZE_BODY)
        chunks = wrap(value, TEXT_WIDTH - indent, body)
        for index, chunk in enumerate(chunks):
            self.ensure(body * LEADING)
            if index == 0:
                self.text("\u2022", MARGIN_X + 2, body)
            self.text(chunk, MARGIN_X + indent, body)
            self.y -= body * LEADING
        self.y -= body * 0.22

    def finish(self) -> list[list[dict]]:
        if self.page:
            self.pages.append(self.page)
        return self.pages or [[]]


def build_content(resume: dict) -> dict:
    """Translate a resume document into the pdfcpu JSON content model."""
    canvas = _Canvas()
    sections = resume.get("sections", {}) or {}

    canvas.text(str(resume.get("name", "")).strip(), MARGIN_X, SIZE_NAME, bold=True)
    canvas.y -= SIZE_NAME * LEADING
    title = str(resume.get("title", "")).strip()
    if title:
        canvas.text(title, MARGIN_X, SIZE_TITLE)
        canvas.y -= SIZE_TITLE * LEADING

    contact = resume.get("contact", {}) or {}
    line = "  |  ".join(str(contact.get(key, "")).strip() for key in ("email", "site", "location") if contact.get(key))
    if line:
        canvas.text(line, MARGIN_X, SIZE_META)
        canvas.y -= SIZE_META * LEADING
    canvas.y -= 6

    summary = str(resume.get("summary", "")).strip()
    if summary:
        canvas.heading("Summary")
        canvas.line(summary, SIZE_BODY)

    skills = sections.get("skills", []) or []
    if skills:
        canvas.heading("Skills")
        for skill in skills:
            name = str(skill.get("name", "")).strip()
            detail = str(skill.get("detail", "")).strip()
            if not name:
                continue
            canvas.line(f"{name} — {detail}" if detail else name, SIZE_BODY)

    experience = sections.get("experience", []) or []
    if experience:
        canvas.heading("Experience")
        for job in experience:
            heading = " — ".join(
                part for part in (str(job.get("role", "")).strip(), str(job.get("company", "")).strip()) if part
            )
            period = str(job.get("period", "")).strip()
            canvas.ensure(SIZE_BODY * 4)
            if heading:
                canvas.line(heading, SIZE_BODY, bold=True)
            if period:
                canvas.line(period, SIZE_META)
            for bullet in job.get("bullets", []) or []:
                text = str(bullet).strip()
                if text:
                    canvas.bullet(text)
            canvas.y -= 3

    projects = sections.get("projects", []) or []
    if projects:
        canvas.heading("Projects")
        for project in projects:
            name = str(project.get("name", "")).strip()
            summary_text = str(project.get("summary", "")).strip()
            canvas.ensure(SIZE_BODY * 3)
            if name:
                canvas.line(name, SIZE_BODY, bold=True)
            if summary_text:
                canvas.line(summary_text, SIZE_BODY, indent=6)

    education = sections.get("education", []) or []
    if education:
        canvas.heading("Education")
        for school in education:
            heading = " — ".join(
                part
                for part in (str(school.get("degree", "")).strip(), str(school.get("school", "")).strip())
                if part
            )
            if heading:
                canvas.line(heading, SIZE_BODY)
            period = str(school.get("period", "")).strip()
            if period:
                canvas.line(period, SIZE_META)

    pages = canvas.finish()
    return {"pages": {str(index + 1): {"content": {"text": page}} for index, page in enumerate(pages)}}


def _run(arguments: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise PdfError(
            f"{' '.join(Path(part).name for part in arguments[:2])} failed "
            f"({result.returncode}): {(result.stderr or result.stdout).strip()[:400]}"
        )
    return result


def build_pdf(name: str) -> dict:
    """Render, create, validate, optimize. Returns the status record it wrote."""
    resume = store.load_variant(name) or store.load_base()
    build_dir = store.variant_dir(name) / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    content = build_content(resume)
    json_path = build_dir / "resume.pdfcpu.json"
    raw_pdf = build_dir / "resume.raw.pdf"
    final_pdf = store.pdf_path(name)
    optimized = build_dir / "resume.optimized.pdf"
    json_path.write_text(json.dumps(content, indent=1), encoding="utf-8")

    binary = pdfcpu_binary()
    _run([binary, "create", str(json_path), str(raw_pdf)])
    validation = _run([binary, "validate", str(raw_pdf)])
    _run([binary, "optimize", str(raw_pdf), str(optimized)])
    shutil.move(str(optimized), str(final_pdf))
    raw_pdf.unlink(missing_ok=True)

    pages = len(content["pages"])
    status = {
        "variant": name,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "validate": "ok",
        "validate_output": (validation.stdout or "").strip().splitlines()[-1:] or ["ok"],
        "pages": pages,
        "size_bytes": final_pdf.stat().st_size,
        "pdfcpu": Path(binary).name,
    }
    store.write_status(name, status)
    return status
