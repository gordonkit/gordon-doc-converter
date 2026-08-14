"""Pandoc adapter for HTML and Markdown document sources."""

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
from gordon_doc_converter.models import (
    ArtifactType,
    ConversionOptions,
    PageOrientation,
    SourceFormat,
)
from gordon_doc_converter.process import ProcessStartError, ProcessTimeoutError, run_process

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_NS = {"w": _W}
ET.register_namespace("w", _W)
_A4_TWIPS = (11906, 16838)
_MARGIN_TWIPS = 1134


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


class PandocConverter:
    """Convert HTML or Markdown sources to A4 PDF or DOCX using Pandoc."""

    def __init__(self, executable: str | None = None) -> None:
        self._executable = executable or shutil.which("pandoc")
        self._pdf_engine = shutil.which("wkhtmltopdf")

    def convert(
        self,
        source_path: Path,
        output_path: Path,
        *,
        source_format: SourceFormat,
        artifact_type: ArtifactType,
        options: ConversionOptions,
    ) -> None:
        """Run Pandoc with bounded execution and apply the requested A4 layout."""
        if self._executable is None:
            raise EngineUnavailableError("Pandoc is required for HTML or Markdown conversion")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        input_format = "markdown" if source_format is SourceFormat.MARKDOWN else "html"
        arguments: list[str] = [
            self._executable,
            str(source_path),
            "--from",
            input_format,
            "--output",
            str(output_path),
        ]
        if artifact_type is ArtifactType.PDF:
            if self._pdf_engine is None:
                raise EngineUnavailableError("wkhtmltopdf is required for Pandoc PDF conversion")
            orientation = (
                "landscape" if options.page_orientation is PageOrientation.LANDSCAPE else "portrait"
            )
            arguments += [
                "--pdf-engine",
                self._pdf_engine,
                "--standalone",
                "--variable",
                "geometry:a4paper",
                "--variable",
                f"geometry:{orientation}",
            ]
        try:
            result = run_process(arguments, options.timeout_seconds)
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
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise EngineFailedError("Pandoc did not create the requested output", engine="pandoc")
        if artifact_type is ArtifactType.DOCX:
            _set_docx_page_layout(output_path, options.page_orientation)
