"""Engine-neutral request, result, capability, and validation models."""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import StrEnum
from pathlib import Path
from typing import Self, cast

from gordon_doc_converter.exceptions import ErrorCode, InvalidInputError
from gordon_doc_converter.models_types import JsonValue


class SourceFormat(StrEnum):
    """Supported source document formats across the public roadmap."""

    DOCX = "docx"
    PDF = "pdf"


class ArtifactType(StrEnum):
    """Artifact types represented by the forward-compatible result contract."""

    PDF = "pdf"
    MARKDOWN = "markdown"
    HTML = "html"
    PAGE_IMAGES = "images"


class ArtifactStatus(StrEnum):
    """Outcome of one requested artifact."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class DeploymentMode(StrEnum):
    """Engine selection policy modes."""

    DESKTOP = "desktop"
    SERVER = "server"
    CONTAINER = "container"
    STRICT_WORD = "strict-word"
    STRICT_LIBREOFFICE = "strict-libreoffice"


class EngineName(StrEnum):
    """Stable names for DOCX-to-PDF engines."""

    WORD_COM = "word-com"
    LIBREOFFICE = "libreoffice"
    GOTENBERG = "gotenberg"


class RevisionMode(StrEnum):
    """Requested handling for tracked revisions."""

    FINAL = "final"
    ORIGINAL = "original"
    MARKUP = "markup"


class CommentMode(StrEnum):
    """Requested handling for document comments."""

    OMIT = "omit"
    APPENDIX = "appendix"
    MARKUP = "markup"


class AnnotationKind(StrEnum):
    """Normalized annotation categories shared by future output routes."""

    COMMENT = "comment"
    INSERTION = "insertion"
    DELETION = "deletion"


def _json_value(value: object) -> JsonValue:
    if isinstance(value, JsonModel):
        return value.to_dict()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if value is None or isinstance(value, str | int | float | bool):
        return cast("JsonValue", value)
    raise TypeError(f"unsupported JSON value type: {type(value).__name__}")


class JsonModel:
    """Mixin for deterministic JSON-compatible dataclass serialization."""

    def to_dict(self) -> dict[str, JsonValue]:
        """Serialize every public field using stable primitive values."""
        # Concrete subclasses are dataclasses; typing cannot express a dataclass-only mixin.
        model_fields = fields(self)  # type: ignore[arg-type]
        return {field.name: _json_value(getattr(self, field.name)) for field in model_fields}


@dataclass(frozen=True, slots=True)
class ConversionWarning(JsonModel):
    """A non-fatal, machine-readable conversion warning."""

    code: str
    message: str
    engine: EngineName | None = None


@dataclass(frozen=True, slots=True)
class ConversionFailure(JsonModel):
    """A serialized failure safe for normal library and CLI consumers."""

    code: ErrorCode
    message: str
    engine: EngineName | None = None
    retryable: bool = False


@dataclass(frozen=True, slots=True)
class AnnotationAnchor(JsonModel):
    """Normalized source offsets for an annotation, when representable."""

    start: int | None = None
    end: int | None = None
    exact: bool = True

    def __post_init__(self) -> None:
        if self.start is not None and self.start < 0:
            raise InvalidInputError("annotation anchor start cannot be negative")
        if self.end is not None and self.end < 0:
            raise InvalidInputError("annotation anchor end cannot be negative")
        if self.start is not None and self.end is not None and self.end < self.start:
            raise InvalidInputError("annotation anchor end cannot precede start")


@dataclass(frozen=True, slots=True)
class NormalizedAnnotation(JsonModel):
    """Engine-neutral comment or tracked-revision metadata."""

    annotation_id: str
    kind: AnnotationKind
    source_order: int
    anchor: AnnotationAnchor = AnnotationAnchor()
    text: str | None = None
    author: str | None = None
    timestamp: str | None = None

    def __post_init__(self) -> None:
        if not self.annotation_id:
            raise InvalidInputError("annotation_id cannot be empty")
        if self.source_order < 0:
            raise InvalidInputError("annotation source_order cannot be negative")


@dataclass(frozen=True, slots=True)
class ConversionOptions(JsonModel):
    """Cross-engine conversion behavior requested by a caller."""

    output_path: Path | None = None
    overwrite: bool = False
    timeout_seconds: float = 120.0
    deployment_mode: DeploymentMode = DeploymentMode.DESKTOP
    engine: EngineName | None = None
    container_engine: EngineName = EngineName.LIBREOFFICE
    revision_mode: RevisionMode = RevisionMode.FINAL
    comment_mode: CommentMode = CommentMode.OMIT
    include_annotation_metadata: bool = False

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise InvalidInputError("timeout_seconds must be greater than zero")
        if self.container_engine is EngineName.WORD_COM:
            raise InvalidInputError("container_engine cannot be word-com")


@dataclass(frozen=True, slots=True)
class ConversionRequest(JsonModel):
    """An engine-neutral request for one source and one or more artifacts."""

    source_path: Path
    source_format: SourceFormat
    artifacts: tuple[ArtifactType, ...] = (ArtifactType.PDF,)
    options: ConversionOptions = ConversionOptions()

    def __post_init__(self) -> None:
        if not self.artifacts:
            raise InvalidInputError("at least one artifact type is required")
        if len(set(self.artifacts)) != len(self.artifacts):
            raise InvalidInputError("artifact types must not contain duplicates")
        if self.source_path.suffix.casefold() != f".{self.source_format.value}":
            raise InvalidInputError("source extension does not match source_format")

    @classmethod
    def from_source(
        cls,
        source_path: Path,
        *,
        artifacts: tuple[ArtifactType, ...] | None = None,
        options: ConversionOptions | None = None,
    ) -> Self:
        """Create a request by inferring the allowlisted source format."""
        suffix = source_path.suffix.casefold().lstrip(".")
        try:
            source_format = SourceFormat(suffix)
        except ValueError as exc:
            raise InvalidInputError("source must have a .docx or .pdf extension") from exc
        if artifacts is None:
            if source_format is SourceFormat.PDF:
                raise InvalidInputError("PDF input requires an explicit artifact target")
            artifacts = (ArtifactType.PDF,)
        return cls(
            source_path=source_path,
            source_format=source_format,
            artifacts=artifacts,
            options=options or ConversionOptions(),
        )


@dataclass(frozen=True, slots=True)
class ArtifactResult(JsonModel):
    """Independent result for one requested artifact."""

    artifact_type: ArtifactType
    status: ArtifactStatus
    path: Path | None = None
    size_bytes: int | None = None
    warnings: tuple[ConversionWarning, ...] = ()
    error: ConversionFailure | None = None


@dataclass(frozen=True, slots=True)
class ConversionResult(JsonModel):
    """Stable aggregate result supporting success and partial failure."""

    success: bool
    source_format: SourceFormat
    artifacts: tuple[ArtifactResult, ...]
    selected_engine: EngineName | None = None
    attempted_engines: tuple[EngineName, ...] = ()
    warnings: tuple[ConversionWarning, ...] = ()
    error: ConversionFailure | None = None
    fallback_reason: str | None = None
    duration_seconds: float = 0.0
    requested_revision_mode: RevisionMode = RevisionMode.FINAL
    effective_revision_mode: RevisionMode | None = None
    requested_comment_mode: CommentMode = CommentMode.OMIT
    effective_comment_mode: CommentMode | None = None
    annotations: tuple[NormalizedAnnotation, ...] = ()


@dataclass(frozen=True, slots=True)
class EngineProbeResult(JsonModel):
    """Availability and capability report from a conversion engine."""

    engine: EngineName
    available: bool
    version: str | None = None
    executable: Path | None = None
    reason: str | None = None
    revision_modes: tuple[RevisionMode, ...] = ()
    comment_modes: tuple[CommentMode, ...] = ()

    def supports(self, revision_mode: RevisionMode, comment_mode: CommentMode) -> bool:
        """Return whether both requested annotation modes are declared supported."""
        return revision_mode in self.revision_modes and comment_mode in self.comment_modes


@dataclass(frozen=True, slots=True)
class PdfValidationResult(JsonModel):
    """Validation facts for a produced or supplied PDF."""

    valid: bool
    file_size: int
    page_count: int | None
    encrypted: bool
    parser_error: str | None = None
    error: ConversionFailure | None = None
