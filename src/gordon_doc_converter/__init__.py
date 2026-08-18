"""Public contracts for GordonKit Document Converter."""

from gordon_doc_converter.comparison import (
    PdfComparisonReport,
    PdfComparisonService,
    PillowImageDiffer,
)
from gordon_doc_converter.exceptions import ConversionError, ErrorCode
from gordon_doc_converter.models import (
    AnnotationAnchor,
    AnnotationKind,
    ArtifactItem,
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
    PageImageFormat,
    PdfValidationResult,
    RevisionMode,
    SourceFormat,
)
from gordon_doc_converter.raster import (
    PageImageArtifact,
    PdfiumPageRenderer,
    PdfRasterizer,
    RasterOptions,
)
from gordon_doc_converter.service import (
    DocumentConversionService,
    convert,
    convert_batch,
    probe_engines,
)

__all__ = [
    "AnnotationAnchor",
    "AnnotationKind",
    "ArtifactResult",
    "ArtifactItem",
    "ArtifactStatus",
    "ArtifactType",
    "CommentMode",
    "ConversionError",
    "ConversionOptions",
    "ConversionRequest",
    "ConversionResult",
    "DeploymentMode",
    "DocumentConversionService",
    "EngineName",
    "EngineProbeResult",
    "ErrorCode",
    "NormalizedAnnotation",
    "PdfValidationResult",
    "PageImageArtifact",
    "PageImageFormat",
    "PdfComparisonReport",
    "PdfComparisonService",
    "PdfiumPageRenderer",
    "PdfRasterizer",
    "PillowImageDiffer",
    "RasterOptions",
    "RevisionMode",
    "SourceFormat",
    "convert",
    "convert_batch",
    "probe_engines",
]

__version__ = "0.5.1"
