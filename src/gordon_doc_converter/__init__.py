"""Public contracts for GordonKit Document Converter."""

from gordon_doc_converter.exceptions import ConversionError, ErrorCode
from gordon_doc_converter.models import (
    AnnotationAnchor,
    AnnotationKind,
    ArtifactResult,
    ArtifactStatus,
    ArtifactType,
    CommentMode,
    ConversionOptions,
    ConversionRequest,
    ConversionResult,
    DeploymentMode,
    EngineName,
    EngineProbeResult,
    NormalizedAnnotation,
    PdfValidationResult,
    RevisionMode,
    SourceFormat,
)

__all__ = [
    "AnnotationAnchor",
    "AnnotationKind",
    "ArtifactResult",
    "ArtifactStatus",
    "ArtifactType",
    "CommentMode",
    "ConversionError",
    "ConversionOptions",
    "ConversionRequest",
    "ConversionResult",
    "DeploymentMode",
    "EngineName",
    "EngineProbeResult",
    "ErrorCode",
    "NormalizedAnnotation",
    "PdfValidationResult",
    "RevisionMode",
    "SourceFormat",
]

__version__ = "0.1.0"
