"""Engine-neutral PDF validation."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from gordon_doc_converter.exceptions import ErrorCode
from gordon_doc_converter.models import ConversionFailure, PdfValidationResult


def _failure(
    code: ErrorCode,
    message: str,
    *,
    size: int = 0,
    page_count: int | None = None,
    encrypted: bool = False,
    parser_error: str | None = None,
) -> PdfValidationResult:
    return PdfValidationResult(
        valid=False,
        file_size=size,
        page_count=page_count,
        encrypted=encrypted,
        parser_error=parser_error,
        error=ConversionFailure(code=code, message=message),
    )


def validate_pdf(path: Path) -> PdfValidationResult:
    """Validate PDF existence, size, parseability, encryption, and page count.

    Parser details and sensitive file paths are intentionally excluded from the public
    failure message. The original parser exception is not raised because validation is a
    result-oriented boundary.
    """
    if not path.is_file():
        return _failure(ErrorCode.PDF_NOT_CREATED, "PDF output was not created")
    size = path.stat().st_size
    if size == 0:
        return _failure(ErrorCode.PDF_NOT_CREATED, "PDF output is empty")
    try:
        reader = PdfReader(path, strict=False)
        encrypted = reader.is_encrypted
        if encrypted:
            return _failure(
                ErrorCode.PDF_VALIDATION_FAILED,
                "encrypted PDFs are not supported",
                size=size,
                encrypted=True,
            )
        page_count = len(reader.pages)
    except (OSError, ValueError, EOFError) as exc:
        return _failure(
            ErrorCode.PDF_VALIDATION_FAILED,
            f"PDF could not be parsed ({type(exc).__name__})",
            size=size,
            parser_error=type(exc).__name__,
        )
    except Exception as exc:  # pypdf exposes several parser-specific exception subclasses.
        return _failure(
            ErrorCode.PDF_VALIDATION_FAILED,
            f"PDF could not be parsed ({type(exc).__name__})",
            size=size,
            parser_error=type(exc).__name__,
        )
    if page_count < 1:
        return _failure(
            ErrorCode.PDF_VALIDATION_FAILED,
            "PDF contains no pages",
            size=size,
            page_count=0,
        )
    return PdfValidationResult(
        valid=True,
        file_size=size,
        page_count=page_count,
        encrypted=False,
    )
