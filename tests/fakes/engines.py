"""Fake engines used by policy and future orchestration tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from gordon_doc_converter.engines.base import EngineExecutionResult
from gordon_doc_converter.models import (
    CommentMode,
    EngineName,
    EngineProbeResult,
    RevisionMode,
)


@dataclass
class FakeEngine:
    """Configurable in-memory implementation of the engine protocol."""

    name: EngineName
    probe_result: EngineProbeResult
    calls: list[tuple[Path, Path]] = field(default_factory=list)

    def probe(self) -> EngineProbeResult:
        """Return the configured probe result."""
        return self.probe_result

    def convert(
        self,
        source_path: Path,
        output_path: Path,
        *,
        timeout_seconds: float,
        revision_mode: RevisionMode,
        comment_mode: CommentMode,
    ) -> EngineExecutionResult:
        """Record the call and return a deterministic successful result."""
        del timeout_seconds, revision_mode, comment_mode
        self.calls.append((source_path, output_path))
        return EngineExecutionResult(self.name, output_path, 0.0)
