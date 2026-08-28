"""Security tests for resource-bounded DOCX, ODT, PDF, and HTML source validation."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from pypdf import PdfWriter

from gordon_doc_converter.exceptions import InvalidInputError
from gordon_doc_converter.models import SourceFormat
from gordon_doc_converter.security import InputValidationLimits, validate_source_document

_CONTENT_TYPES = "<Types/>"
_RELS = "<Relationships/>"
_DOCUMENT = "<w:document xmlns:w='urn:test'><w:body/></w:document>"
_ODF_MIMETYPE = "application/vnd.oasis.opendocument.text"
_ODF_MANIFEST = (
    "<manifest:manifest xmlns:manifest='urn:oasis:names:tc:opendocument:xmlns:manifest:1.0'/>"
)
_ODF_CONTENT = (
    "<office:document-content xmlns:office='urn:oasis:names:tc:opendocument:xmlns:office:1.0'/>"
)


def _write_docx(path: Path, extras: dict[str, bytes] | None = None) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _RELS)
        archive.writestr("word/document.xml", _DOCUMENT)
        for name, content in (extras or {}).items():
            archive.writestr(name, content)


def _write_odt(path: Path, *, mimetype: str = _ODF_MIMETYPE) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("mimetype", mimetype)
        archive.writestr("META-INF/manifest.xml", _ODF_MANIFEST)
        archive.writestr("content.xml", _ODF_CONTENT)


def _write_pdf(path: Path, pages: int) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as stream:
        writer.write(stream)


def test_valid_docx_accepts_matching_mime_and_traditional_chinese_path(tmp_path: Path) -> None:
    path = tmp_path / "臺灣 文件.docx"
    _write_docx(path)

    validate_source_document(
        path,
        SourceFormat.DOCX,
        declared_mime_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )


def test_valid_odt_accepts_matching_mime_and_traditional_chinese_path(tmp_path: Path) -> None:
    path = tmp_path / "臺灣 文件.odt"
    _write_odt(path)

    validate_source_document(
        path,
        SourceFormat.ODT,
        declared_mime_type=_ODF_MIMETYPE,
    )


def test_odt_rejects_invalid_mimetype_and_missing_core_part(tmp_path: Path) -> None:
    wrong_mimetype = tmp_path / "wrong.odt"
    _write_odt(wrong_mimetype, mimetype="text/plain")
    with pytest.raises(InvalidInputError, match="mimetype"):
        validate_source_document(wrong_mimetype, SourceFormat.ODT)

    missing_content = tmp_path / "missing.odt"
    with ZipFile(missing_content, "w", ZIP_DEFLATED) as archive:
        archive.writestr("mimetype", _ODF_MIMETYPE)
        archive.writestr("META-INF/manifest.xml", _ODF_MANIFEST)
    with pytest.raises(InvalidInputError, match="core parts"):
        validate_source_document(missing_content, SourceFormat.ODT)


def test_docx_rejects_invalid_package_and_unsafe_member(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.docx"
    corrupt.write_bytes(b"not a zip")
    with pytest.raises(InvalidInputError, match="OOXML"):
        validate_source_document(corrupt, SourceFormat.DOCX)

    unsafe = tmp_path / "unsafe.docx"
    _write_docx(unsafe, {"../escape.bin": b"unsafe"})
    with pytest.raises(InvalidInputError, match="unsafe part"):
        validate_source_document(unsafe, SourceFormat.DOCX)


def test_docx_rejects_resource_limit_violations(tmp_path: Path) -> None:
    path = tmp_path / "large.docx"
    _write_docx(path, {"word/media/data.bin": b"x" * 2_000})

    with pytest.raises(InvalidInputError, match="expands beyond"):
        validate_source_document(
            path,
            SourceFormat.DOCX,
            limits=InputValidationLimits(max_uncompressed_size=1_000),
        )


def test_mime_and_file_size_must_match_policy(tmp_path: Path) -> None:
    path = tmp_path / "input.docx"
    _write_docx(path)

    with pytest.raises(InvalidInputError, match="MIME"):
        validate_source_document(path, SourceFormat.DOCX, declared_mime_type="application/pdf")
    with pytest.raises(InvalidInputError, match="file-size"):
        validate_source_document(
            path,
            SourceFormat.DOCX,
            limits=InputValidationLimits(max_file_size=1),
        )


def test_pdf_rejects_encryption_corruption_and_page_limit(tmp_path: Path) -> None:
    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"not a pdf")
    with pytest.raises(InvalidInputError, match="parsed"):
        validate_source_document(corrupt, SourceFormat.PDF)

    encrypted = tmp_path / "encrypted.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.encrypt("public-test-password")
    with encrypted.open("wb") as stream:
        writer.write(stream)
    with pytest.raises(InvalidInputError, match="encrypted"):
        validate_source_document(encrypted, SourceFormat.PDF)

    pages = tmp_path / "pages.pdf"
    _write_pdf(pages, 2)
    with pytest.raises(InvalidInputError, match="page limit"):
        validate_source_document(
            pages,
            SourceFormat.PDF,
            limits=InputValidationLimits(max_pdf_pages=1),
        )


def test_html_validates_extension_mime_and_size_without_container_checks(
    tmp_path: Path,
) -> None:
    source = tmp_path / "page.html"
    source.write_text("<p>內容</p>", encoding="utf-8")

    validate_source_document(source, SourceFormat.HTML, declared_mime_type="text/html")
    validate_source_document(
        source,
        SourceFormat.HTML,
        declared_mime_type="text/html; charset=utf-8",
    )

    with pytest.raises(InvalidInputError, match="MIME"):
        validate_source_document(source, SourceFormat.HTML, declared_mime_type="text/plain")
    with pytest.raises(InvalidInputError, match="file-size limit"):
        validate_source_document(
            source,
            SourceFormat.HTML,
            limits=InputValidationLimits(max_file_size=1),
        )

    mismatched = tmp_path / "page.txt"
    mismatched.write_text("<p>內容</p>", encoding="utf-8")
    with pytest.raises(InvalidInputError, match="extension"):
        validate_source_document(mismatched, SourceFormat.HTML)


def test_markdown_source_format_remains_outside_input_validation(tmp_path: Path) -> None:
    source = tmp_path / "note.md"
    source.write_text("# 標題\n", encoding="utf-8")

    with pytest.raises(InvalidInputError, match="not supported by input validation"):
        validate_source_document(source, SourceFormat.MARKDOWN)
