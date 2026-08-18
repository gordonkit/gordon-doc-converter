"""Unit tests for page-aware PDF semantic extraction."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
)

from gordon_doc_converter.content.models import LayoutAvailability, PageContentKind
from gordon_doc_converter.content.pdf import extract_pdf_content
from gordon_doc_converter.models import MetadataDetail


def _write_text_pdf(path: Path) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
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
    content.set_data(b"BT /F1 12 Tf 20 100 Td (Hello PDF) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(content)
    with path.open("wb") as stream:
        writer.write(stream)


def _write_image_pdf(path: Path) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=10, height=10)
    image = DecodedStreamObject()
    image.set_data(bytes([255, 0, 0]))
    image.update(
        {
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(1),
            NameObject("/Height"): NumberObject(1),
            NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
            NameObject("/BitsPerComponent"): NumberObject(8),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/XObject"): DictionaryObject({NameObject("/Im1"): writer._add_object(image)})}
    )
    content = DecodedStreamObject()
    content.set_data(b"q 1 0 0 1 0 0 cm /Im1 Do Q")
    page[NameObject("/Contents")] = writer._add_object(content)
    page[NameObject("/MediaBox")] = ArrayObject(
        [NumberObject(0), NumberObject(0), NumberObject(10), NumberObject(10)]
    )
    with path.open("wb") as stream:
        writer.write(stream)


def test_pdf_extracts_text_with_one_based_page_provenance(tmp_path: Path) -> None:
    source = tmp_path / "text.pdf"
    _write_text_pdf(source)

    content = extract_pdf_content(source)

    assert content.page_kinds == (PageContentKind.TEXT,)
    assert content.blocks[0].page_number == 1
    assert content.source_sha256 is not None
    assert len(content.source_sha256) == 64
    assert content.blocks[0].source_anchor is not None
    assert content.blocks[0].source_anchor.locator == "pdf-page"
    assert content.blocks[0].source_anchor.page_number == 1
    assert "Hello PDF" in content.blocks[0].text
    assert not any(warning.code == "OCR_REQUIRED" for warning in content.warnings)
    assert "PDF_READING_ORDER_INFERRED" in {warning.code for warning in content.warnings}


def test_pdf_layout_metadata_identifies_exact_physical_page_provider(tmp_path: Path) -> None:
    source = tmp_path / "layout.pdf"
    _write_text_pdf(source)

    content = extract_pdf_content(source, metadata_detail=MetadataDetail.LAYOUT)

    assert content.layout.availability is LayoutAvailability.AVAILABLE
    assert content.layout.provider == "pypdf"
    assert content.layout.confidence == "exact"


def test_image_only_pdf_is_explicitly_classified_as_ocr_required(tmp_path: Path) -> None:
    source = tmp_path / "scan.pdf"
    _write_image_pdf(source)

    content = extract_pdf_content(source)

    assert content.page_kinds == (PageContentKind.IMAGE,)
    assert "OCR_REQUIRED" in {warning.code for warning in content.warnings}
    if content.assets:
        assert content.assets[0].page_number == 1
        assert content.assets[0].filename.startswith("page-0001-image-0001")
        assert content.blocks[0].page_number == 1
    else:
        assert "PDF_IMAGE_EXTRACTION_INCOMPLETE" in {warning.code for warning in content.warnings}


def test_blank_pdf_page_is_disclosed_instead_of_silent_text_success(tmp_path: Path) -> None:
    source = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with source.open("wb") as stream:
        writer.write(stream)

    content = extract_pdf_content(source)

    assert content.page_kinds == (PageContentKind.EMPTY,)
    assert content.blocks == ()
    assert "PDF_EMPTY_PAGE" in {warning.code for warning in content.warnings}
