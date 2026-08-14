"""Shared protocols implemented by conversion engines."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from gordon_doc_converter.models import (
    ArtifactType,
    CommentMode,
    ConversionWarning,
    EngineName,
    EngineProbeResult,
    RevisionMode,
    SourceFormat,
)


@dataclass(frozen=True, slots=True)
class EngineExecutionResult:
    """Bounded, adapter-neutral facts produced by an engine invocation."""

    engine: EngineName
    output_path: Path
    duration_seconds: float
    warnings: tuple[ConversionWarning, ...] = ()


class ConverterEngine(Protocol):
    """Narrow contract for a DOCX-to-PDF rendering adapter."""

    @property
    def name(self) -> EngineName:
        """Return the engine's stable public name."""
        ...

    def probe(self) -> EngineProbeResult:
        """Report availability and supported annotation modes."""
        ...

    def convert(
        self,
        source_path: Path,
        output_path: Path,
        *,
        timeout_seconds: float,
        revision_mode: RevisionMode,
        comment_mode: CommentMode,
    ) -> EngineExecutionResult:
        """Render one DOCX to PDF or raise a project conversion exception."""
        ...


@runtime_checkable
class FileConverterEngine(ConverterEngine, Protocol):
    """Capability contract for office-file conversions."""

    def convert_file(
        self,
        source_path: Path,
        output_path: Path,
        *,
        source_format: SourceFormat,
        artifact_type: ArtifactType,
        timeout_seconds: float,
    ) -> EngineExecutionResult:
        """Convert an office document to another supported file artifact."""
        ...
