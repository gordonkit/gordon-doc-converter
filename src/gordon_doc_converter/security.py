"""Resource-bounded source document validation shared by library and API routes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile, is_zipfile

from gordon_doc_converter.exceptions import InvalidInputError
from gordon_doc_converter.models import SourceFormat
from gordon_doc_converter.validation import validate_pdf

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_ODT_MIME = "application/vnd.oasis.opendocument.text"
_PDF_MIME = "application/pdf"
_REQUIRED_DOCX_PARTS = frozenset({"[Content_Types].xml", "_rels/.rels", "word/document.xml"})
_REQUIRED_ODT_PARTS = frozenset({"mimetype", "META-INF/manifest.xml", "content.xml"})


@dataclass(frozen=True, slots=True)
class InputValidationLimits:
    """Upper bounds applied before parsing or extracting untrusted documents."""

    max_file_size: int = 50 * 1024 * 1024
    max_zip_entries: int = 10_000
    max_uncompressed_size: int = 200 * 1024 * 1024
    max_compression_ratio: float = 1_000.0
    max_pdf_pages: int = 1_000

    def __post_init__(self) -> None:
        if (
            self.max_file_size <= 0
            or self.max_zip_entries <= 0
            or self.max_uncompressed_size <= 0
            or self.max_compression_ratio <= 0
            or self.max_pdf_pages <= 0
        ):
            raise InvalidInputError("input validation limits must be greater than zero")


_DEFAULT_INPUT_LIMITS = InputValidationLimits()


def _validate_member_name(name: str) -> None:
    member = PurePosixPath(name.replace("\\", "/"))
    if member.is_absolute() or ".." in member.parts:
        raise InvalidInputError("DOCX package contains an unsafe part name")


def _validate_docx(path: Path, limits: InputValidationLimits) -> None:
    if not is_zipfile(path):
        raise InvalidInputError("DOCX input is not a valid OOXML ZIP package")
    try:
        with ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > limits.max_zip_entries:
                raise InvalidInputError("DOCX package contains too many parts")
            total_uncompressed = 0
            names: set[str] = set()
            for member in members:
                _validate_member_name(member.filename)
                names.add(member.filename)
                if member.flag_bits & 0x1:
                    raise InvalidInputError("encrypted DOCX packages are not supported")
                total_uncompressed += member.file_size
                if total_uncompressed > limits.max_uncompressed_size:
                    raise InvalidInputError("DOCX package expands beyond the configured limit")
                if member.file_size > 0:
                    compressed_size = max(member.compress_size, 1)
                    ratio = member.file_size / compressed_size
                    if ratio > limits.max_compression_ratio:
                        raise InvalidInputError("DOCX package has a suspicious compression ratio")
            if not _REQUIRED_DOCX_PARTS.issubset(names):
                raise InvalidInputError("DOCX package is missing required OOXML parts")
    except BadZipFile as exc:
        raise InvalidInputError("DOCX input is not a valid OOXML ZIP package") from exc


def _validate_odt(path: Path, limits: InputValidationLimits) -> None:
    if not is_zipfile(path):
        raise InvalidInputError("ODT input is not a valid ODF ZIP package")
    try:
        with ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > limits.max_zip_entries:
                raise InvalidInputError("ODT package contains too many parts")
            total_uncompressed = 0
            names: set[str] = set()
            for member in members:
                _validate_member_name(member.filename)
                names.add(member.filename)
                if member.flag_bits & 0x1:
                    raise InvalidInputError("encrypted ODT packages are not supported")
                total_uncompressed += member.file_size
                if total_uncompressed > limits.max_uncompressed_size:
                    raise InvalidInputError("ODT package expands beyond the configured limit")
                if member.file_size > 0:
                    compressed_size = max(member.compress_size, 1)
                    ratio = member.file_size / compressed_size
                    if ratio > limits.max_compression_ratio:
                        raise InvalidInputError("ODT package has a suspicious compression ratio")
            if "mimetype" not in names:
                raise InvalidInputError("ODT package is missing the mimetype part")
            if archive.read("mimetype").decode("utf-8") != _ODT_MIME:
                raise InvalidInputError("ODT package has an invalid mimetype")
            if not _REQUIRED_ODT_PARTS.issubset(names):
                raise InvalidInputError("ODT package is missing required core parts")
    except (BadZipFile, UnicodeDecodeError) as exc:
        raise InvalidInputError("ODT input is not a valid ODF ZIP package") from exc


def _validate_pdf(path: Path, limits: InputValidationLimits) -> None:
    result = validate_pdf(path)
    if not result.valid:
        message = result.error.message if result.error is not None else "PDF validation failed"
        raise InvalidInputError(message)
    if result.page_count is not None and result.page_count > limits.max_pdf_pages:
        raise InvalidInputError("PDF input exceeds the configured page limit")


def validate_source_document(
    path: Path,
    source_format: SourceFormat,
    *,
    declared_mime_type: str | None = None,
    limits: InputValidationLimits = _DEFAULT_INPUT_LIMITS,
) -> None:
    """Validate extension, MIME, size, and container structure for an untrusted source."""
    if not path.is_file():
        raise InvalidInputError("source document does not exist")
    if path.suffix.casefold() != f".{source_format.value}":
        raise InvalidInputError("source extension does not match the declared format")
    if path.stat().st_size > limits.max_file_size:
        raise InvalidInputError("source document exceeds the configured file-size limit")
    expected_mime = {
        SourceFormat.DOCX: _DOCX_MIME,
        SourceFormat.ODT: _ODT_MIME,
        SourceFormat.PDF: _PDF_MIME,
    }.get(source_format)
    if expected_mime is None:
        raise InvalidInputError("source format is not supported by input validation")
    if declared_mime_type is not None:
        normalized_mime = declared_mime_type.partition(";")[0].strip().casefold()
        if normalized_mime != expected_mime:
            raise InvalidInputError("declared MIME type does not match the source format")
    if source_format is SourceFormat.DOCX:
        _validate_docx(path, limits)
    elif source_format is SourceFormat.ODT:
        _validate_odt(path, limits)
    else:
        _validate_pdf(path, limits)
