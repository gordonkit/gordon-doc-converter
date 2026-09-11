"""LibreOffice integration coverage for office artifacts rebuilt from a PDF."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from gordon_doc_converter import (
    ArtifactStatus,
    ArtifactType,
    ConversionOptions,
    ConversionRequest,
    EngineName,
    SourceFormat,
    convert,
)
from gordon_doc_converter.service import probe_engines

pytestmark = pytest.mark.integration

_HEADING = "GordonKit PDF Rebuild"
_BODY = "Paragraph text the extraction must carry into the office artifact."


def _write_text_pdf(path: Path) -> None:
    """Write a one-page PDF whose text layer holds a heading and a paragraph."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    content = DecodedStreamObject()
    content.set_data(
        f"BT /F1 24 Tf 72 760 Td ({_HEADING}) Tj ET\nBT /F1 11 Tf 72 720 Td ({_BODY}) Tj ET".encode(
            "ascii"
        )
    )
    page[NameObject("/Contents")] = writer._add_object(content)
    with path.open("wb") as stream:
        writer.write(stream)


def _require_libreoffice() -> None:
    probe = next(iter(probe_engines((EngineName.LIBREOFFICE,))))
    if not probe.available:
        pytest.skip(probe.reason or "LibreOffice is unavailable")


def test_pdf_odt_is_a_readable_odf_package(tmp_path: Path) -> None:
    """A PDF with no editable model still produces an ODT LibreOffice itself wrote."""
    _require_libreoffice()
    source = tmp_path / "臺灣 報告.pdf"
    output = tmp_path / "臺灣 報告.odt"
    _write_text_pdf(source)

    result = convert(
        ConversionRequest(
            source,
            SourceFormat.PDF,
            (ArtifactType.ODT,),
            ConversionOptions(output_path=output),
        )
    )

    assert result.success is True, result.error
    assert result.artifacts[0].status is ArtifactStatus.SUCCESS
    assert output.is_file()
    with ZipFile(output) as package:
        # An ODF package stores its media type first and uncompressed; a Writer
        # document that LibreOffice saved as Writer/Web would name another type.
        assert package.read("mimetype") == b"application/vnd.oasis.opendocument.text"
        document = package.read("content.xml").decode("utf-8")
    assert _HEADING in document
    assert "LAYOUT_NOT_PRESERVED" in {warning.code for warning in result.warnings}


def test_pdf_docx_is_a_readable_ooxml_package(tmp_path: Path) -> None:
    """The DOCX route works through whichever engine the host carries.

    Pandoc renders it where installed; the container image has only LibreOffice and
    reaches the same artifact through the markup fallback, so this asserts the
    package rather than the engine that wrote it.
    """
    _require_libreoffice()
    source = tmp_path / "臺灣 報告.pdf"
    output = tmp_path / "臺灣 報告.docx"
    _write_text_pdf(source)

    result = convert(
        ConversionRequest(
            source,
            SourceFormat.PDF,
            (ArtifactType.DOCX,),
            ConversionOptions(output_path=output),
        )
    )

    assert result.success is True, result.error
    assert output.is_file()
    with ZipFile(output) as package:
        names = set(package.namelist())
        assert "word/document.xml" in names
        document = package.read("word/document.xml").decode("utf-8")
    assert _HEADING in document
    assert "LAYOUT_NOT_PRESERVED" in {warning.code for warning in result.warnings}
