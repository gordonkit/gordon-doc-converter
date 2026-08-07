"""Shared protocol implemented by all DOCX-to-PDF engines."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from gordon_doc_converter.models import (
    CommentMode,
    ConversionWarning,
    EngineName,
    EngineProbeResult,
    RevisionMode,
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
