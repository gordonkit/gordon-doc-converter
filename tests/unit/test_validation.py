"""Tests for engine-neutral PDF validation."""

from pathlib import Path

from pypdf import PdfWriter

from gordon_doc_converter.exceptions import ErrorCode
from gordon_doc_converter.validation import validate_pdf


def _write_pdf(path: Path, *, pages: int = 1, password: str | None = None) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    if password is not None:
        writer.encrypt(password)
    with path.open("wb") as stream:
        writer.write(stream)


def test_valid_pdf_reports_size_and_page_count(tmp_path: Path) -> None:
    path = tmp_path / "臺灣 文件.pdf"
    _write_pdf(path, pages=2)

    result = validate_pdf(path)

    assert result.valid is True
    assert result.file_size > 0
    assert result.page_count == 2
    assert result.encrypted is False
    assert result.error is None


def test_missing_pdf_maps_to_not_created(tmp_path: Path) -> None:
    result = validate_pdf(tmp_path / "missing.pdf")

    assert result.valid is False
    assert result.error is not None
    assert result.error.code is ErrorCode.PDF_NOT_CREATED


def test_empty_pdf_maps_to_not_created(tmp_path: Path) -> None:
    path = tmp_path / "empty.pdf"
    path.touch()

    result = validate_pdf(path)

    assert result.error is not None
    assert result.error.code is ErrorCode.PDF_NOT_CREATED


def test_corrupt_pdf_maps_to_validation_failure(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"not a pdf")

    result = validate_pdf(path)

    assert result.valid is False
    assert result.error is not None
    assert result.error.code is ErrorCode.PDF_VALIDATION_FAILED
    assert str(path) not in result.error.message
    assert result.parser_error is not None


def test_encrypted_pdf_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "encrypted.pdf"
    _write_pdf(path, password="public-test-password")

    result = validate_pdf(path)

    assert result.valid is False
    assert result.encrypted is True
    assert result.error is not None
    assert result.error.code is ErrorCode.PDF_VALIDATION_FAILED


def test_zero_page_pdf_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "zero-pages.pdf"
    _write_pdf(path, pages=0)

    result = validate_pdf(path)

    assert result.valid is False
    assert result.page_count == 0
    assert result.error is not None
    assert result.error.code is ErrorCode.PDF_VALIDATION_FAILED


def test_validation_error_serializes_to_json() -> None:
    result = validate_pdf(Path("does-not-exist.pdf"))
    payload = result.to_dict()
    error = payload["error"]

    assert isinstance(error, dict)
    assert error["code"] == "PDF_NOT_CREATED"
