"""Framework-neutral progress events for long-running conversions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from gordon_doc_converter.models import ArtifactType, EngineName


class ProgressState(StrEnum):
    """Lifecycle state of one observable conversion phase."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ProgressEvent:
    """One safe progress update without sensitive source paths."""

    phase: str
    state: ProgressState
    message: str
    engine: EngineName | None = None
    artifact: ArtifactType | None = None
    completed: int | None = None
    total: int | None = None
    source_name: str | None = None


ProgressCallback = Callable[[ProgressEvent], None]
