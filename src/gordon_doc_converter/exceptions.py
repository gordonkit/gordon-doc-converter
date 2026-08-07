"""Stable project exceptions and error codes."""

from __future__ import annotations

from enum import StrEnum

from gordon_doc_converter.models_types import JsonValue


class ErrorCode(StrEnum):
    """Machine-readable error codes exposed by the public contract."""

    INVALID_INPUT = "INVALID_INPUT"
    OUTPUT_EXISTS = "OUTPUT_EXISTS"
    ENGINE_UNAVAILABLE = "ENGINE_UNAVAILABLE"
    ENGINE_FAILED = "ENGINE_FAILED"
    CONVERSION_TIMEOUT = "CONVERSION_TIMEOUT"
    UNSUPPORTED_ANNOTATION_MODE = "UNSUPPORTED_ANNOTATION_MODE"
    PDF_NOT_CREATED = "PDF_NOT_CREATED"
    PDF_VALIDATION_FAILED = "PDF_VALIDATION_FAILED"


class ConversionError(Exception):
    """Base exception with a stable code and safe public message."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        engine: str | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.engine = engine
        self.retryable = retryable

    def to_dict(self) -> dict[str, JsonValue]:
        """Return the stable JSON-compatible representation of the error."""
        return {
            "code": self.code.value,
            "message": self.message,
            "engine": self.engine,
            "retryable": self.retryable,
        }


class InvalidInputError(ConversionError):
    """Raised when a conversion request is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.INVALID_INPUT, message)


class EngineUnavailableError(ConversionError):
    """Raised when no requested conversion engine can run."""

    def __init__(self, message: str, *, engine: str | None = None) -> None:
        super().__init__(ErrorCode.ENGINE_UNAVAILABLE, message, engine=engine)


class EngineFailedError(ConversionError):
    """Raised when an available engine fails to render the document."""

    def __init__(self, message: str, *, engine: str, retryable: bool = False) -> None:
        super().__init__(
            ErrorCode.ENGINE_FAILED,
            message,
            engine=engine,
            retryable=retryable,
        )


class ConversionTimeoutError(ConversionError):
    """Raised when an engine exceeds the configured timeout."""

    def __init__(self, message: str, *, engine: str) -> None:
        super().__init__(
            ErrorCode.CONVERSION_TIMEOUT,
            message,
            engine=engine,
            retryable=True,
        )


class OutputExistsError(ConversionError):
    """Raised when overwrite is disabled and the output already exists."""

    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.OUTPUT_EXISTS, message)


class PdfNotCreatedError(ConversionError):
    """Raised when an engine does not produce a non-empty PDF."""

    def __init__(self, message: str, *, engine: str | None = None) -> None:
        super().__init__(ErrorCode.PDF_NOT_CREATED, message, engine=engine)


class PdfValidationError(ConversionError):
    """Raised when a produced or supplied PDF fails structural validation."""

    def __init__(self, message: str, *, engine: str | None = None) -> None:
        super().__init__(ErrorCode.PDF_VALIDATION_FAILED, message, engine=engine)


class UnsupportedAnnotationModeError(ConversionError):
    """Raised when a strict engine cannot honor requested annotation modes."""

    def __init__(self, message: str, *, engine: str) -> None:
        super().__init__(
            ErrorCode.UNSUPPORTED_ANNOTATION_MODE,
            message,
            engine=engine,
        )
