"""Pandoc adapter that renders HTML and Markdown sources to DOCX."""

from __future__ import annotations

import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from gordon_doc_converter.exceptions import (
    ConversionTimeoutError,
    EngineFailedError,
    EngineUnavailableError,
)
from gordon_doc_converter.models import ConversionOptions, PageOrientation, SourceFormat
from gordon_doc_converter.process import ProcessStartError, ProcessTimeoutError, run_process

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_NS = {"w": _W}
ET.register_namespace("w", _W)
_A4_TWIPS = (11906, 16838)
_MARGIN_TWIPS = 1134
# Half-point units, matching the 10.5pt body size of the HTML print stylesheet.
_BODY_HALF_POINTS = "21"
_LATIN_FONT = "Segoe UI"
_EAST_ASIAN_FONT = "Microsoft JhengHei"
# GFM is the dialect our Markdown reader accepts, so Pandoc must read the same one.
_MARKDOWN_DIALECT = "gfm"


def _set_docx_page_layout(path: Path, orientation: PageOrientation) -> None:
    """Set A4 section properties in a Pandoc-generated OOXML package."""
    width, height = _A4_TWIPS
    if orientation is PageOrientation.LANDSCAPE:
        width, height = height, width
    with tempfile.TemporaryDirectory(prefix="gordon-docx-layout-") as directory:
        replacement = Path(directory) / path.name
        with ZipFile(path, "r") as source, ZipFile(replacement, "w", ZIP_DEFLATED) as target:
            for item in source.infolist():
                data = source.read(item.filename)
                if item.filename == "word/document.xml":
                    root = ET.fromstring(data)
                    sect_pr = root.find(".//w:sectPr", _NS)
                    if sect_pr is None:
                        sect_pr = ET.SubElement(root, f"{{{_W}}}sectPr")
                    page_size = sect_pr.find("w:pgSz", _NS)
                    if page_size is None:
                        page_size = ET.SubElement(sect_pr, f"{{{_W}}}pgSz")
                    page_size.set(f"{{{_W}}}w", str(width))
                    page_size.set(f"{{{_W}}}h", str(height))
                    margins = sect_pr.find("w:pgMar", _NS)
                    if margins is None:
                        margins = ET.SubElement(sect_pr, f"{{{_W}}}pgMar")
                    for side in ("top", "right", "bottom", "left"):
                        margins.set(f"{{{_W}}}{side}", str(_MARGIN_TWIPS))
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                target.writestr(item, data)
        replacement.replace(path)


def _apply_fonts(rpr: ET.Element) -> None:
    """Point one run-properties element at the Latin and CJK fonts we ship with."""
    fonts = rpr.find("w:rFonts", _NS)
    if fonts is None:
        fonts = ET.Element(f"{{{_W}}}rFonts")
        rpr.insert(0, fonts)
    for attribute in ("ascii", "hAnsi", "cs"):
        fonts.set(f"{{{_W}}}{attribute}", _LATIN_FONT)
    fonts.set(f"{{{_W}}}eastAsia", _EAST_ASIAN_FONT)


def _restyle_reference_docx(path: Path) -> None:
    """Rewrite a reference document so headings and body text use CJK-capable fonts."""
    with tempfile.TemporaryDirectory(prefix="gordon-docx-reference-") as directory:
        replacement = Path(directory) / path.name
        with ZipFile(path, "r") as source, ZipFile(replacement, "w", ZIP_DEFLATED) as target:
            for item in source.infolist():
                data = source.read(item.filename)
                if item.filename == "word/styles.xml":
                    root = ET.fromstring(data)
                    defaults = root.find("w:docDefaults/w:rPrDefault/w:rPr", _NS)
                    if defaults is None:
                        defaults = root.find("w:docDefaults/w:rPrDefault", _NS)
                        if defaults is None:
                            rpr_default = ET.SubElement(
                                ET.SubElement(root, f"{{{_W}}}docDefaults"),
                                f"{{{_W}}}rPrDefault",
                            )
                            defaults = ET.SubElement(rpr_default, f"{{{_W}}}rPr")
                        else:
                            defaults = ET.SubElement(defaults, f"{{{_W}}}rPr")
                    _apply_fonts(defaults)
                    size = defaults.find("w:sz", _NS)
                    if size is None:
                        size = ET.SubElement(defaults, f"{{{_W}}}sz")
                    size.set(f"{{{_W}}}val", _BODY_HALF_POINTS)
                    # Named styles carry their own fonts, which would win over the defaults.
                    for style in root.findall("w:style", _NS):
                        run_properties = style.find("w:rPr", _NS)
                        if (
                            run_properties is not None
                            and run_properties.find("w:rFonts", _NS) is not None
                        ):
                            _apply_fonts(run_properties)
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                target.writestr(item, data)
        replacement.replace(path)


class PandocConverter:
    """Convert HTML or Markdown sources to A4 DOCX using Pandoc.

    PDF output does not come through here: Pandoc's HTML reader keeps only the body and
    the document metadata, which would discard the page setup a print document carries.
    """

    def __init__(self, executable: str | None = None) -> None:
        self._executable = executable or shutil.which("pandoc")

    def convert(
        self,
        source_path: Path,
        output_path: Path,
        *,
        source_format: SourceFormat,
        options: ConversionOptions,
    ) -> None:
        """Run Pandoc with bounded execution and apply the requested A4 layout."""
        if self._executable is None:
            raise EngineUnavailableError("Pandoc is required for HTML or Markdown conversion")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        input_format = _MARKDOWN_DIALECT if source_format is SourceFormat.MARKDOWN else "html"
        arguments: list[str] = [
            self._executable,
            str(source_path),
            "--from",
            input_format,
            "--output",
            str(output_path),
            # Relative image paths belong to the source document, not to our working directory.
            "--resource-path",
            str(source_path.parent),
        ]
        with tempfile.TemporaryDirectory(prefix="gordon-pandoc-") as directory:
            reference = self._reference_docx(Path(directory), options.timeout_seconds)
            if reference is not None:
                arguments += ["--reference-doc", str(reference)]
            self._run(arguments, options.timeout_seconds)
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise EngineFailedError("Pandoc did not create the requested output", engine="pandoc")
        _set_docx_page_layout(output_path, options.page_orientation)

    def _reference_docx(self, workspace: Path, timeout_seconds: float) -> Path | None:
        """Build a restyled copy of Pandoc's own reference document, or skip it on failure."""
        if self._executable is None:
            return None
        empty = workspace / "reference-source.md"
        empty.write_text("", encoding="utf-8", newline="\n")
        reference = workspace / "reference.docx"
        arguments = [
            self._executable,
            str(empty),
            "--from",
            _MARKDOWN_DIALECT,
            "--output",
            str(reference),
        ]
        try:
            result = run_process(arguments, timeout_seconds)
        except (ProcessStartError, ProcessTimeoutError):
            return None
        if result.returncode != 0 or not reference.is_file():
            return None
        try:
            _restyle_reference_docx(reference)
        except (OSError, ET.ParseError, ValueError):
            return None
        return reference

    def _run(self, arguments: list[str], timeout_seconds: float) -> None:
        """Execute one bounded Pandoc invocation and translate its failures."""
        try:
            result = run_process(arguments, timeout_seconds)
        except ProcessStartError as exc:
            raise EngineUnavailableError("Pandoc could not be started") from exc
        except ProcessTimeoutError as exc:
            raise ConversionTimeoutError("Pandoc conversion timed out", engine="pandoc") from exc
        if result.returncode != 0:
            detail = result.stderr.strip()
            message = "Pandoc conversion failed"
            if detail:
                message += f": {detail.splitlines()[-1][:240]}"
            raise EngineFailedError(message, engine="pandoc")
