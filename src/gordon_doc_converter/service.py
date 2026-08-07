"""Public application service for document conversion orchestration."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from gordon_doc_converter.engines.base import ConverterEngine
from gordon_doc_converter.engines.libreoffice import LibreOfficeEngine
from gordon_doc_converter.engines.word_com import WordComEngine
from gordon_doc_converter.environment import EnvironmentInfo, detect_environment
from gordon_doc_converter.models import (
    ConversionRequest,
    ConversionResult,
    EngineName,
    EngineProbeResult,
)
from gordon_doc_converter.pipeline import ConversionPipeline


class DocumentConversionService:
    """Framework-independent service for single, batch, and engine-probe operations."""

    def __init__(
        self,
        engines: Iterable[ConverterEngine] | None = None,
        environment: EnvironmentInfo | None = None,
    ) -> None:
        configured_engines = (
            (WordComEngine(), LibreOfficeEngine()) if engines is None else tuple(engines)
        )
        self._pipeline = ConversionPipeline(
            configured_engines,
            environment or detect_environment(),
        )

    def convert(self, request: ConversionRequest) -> ConversionResult:
        """Convert one request through policy-selected engines and stable result contracts."""
        return self._pipeline.convert(request)

    def convert_batch(self, requests: Iterable[ConversionRequest]) -> tuple[ConversionResult, ...]:
        """Convert requests sequentially so one item failure does not stop the batch."""
        return tuple(self.convert(request) for request in requests)

    def probe_engines(
        self,
        names: Sequence[EngineName] = tuple(EngineName),
    ) -> tuple[EngineProbeResult, ...]:
        """Probe known or explicitly requested engines without raising adapter failures."""
        return self._pipeline.probe_engines(names)


def convert(request: ConversionRequest) -> ConversionResult:
    """Convert one document using the default local engine registry and environment policy."""
    return DocumentConversionService().convert(request)


def convert_batch(requests: Iterable[ConversionRequest]) -> tuple[ConversionResult, ...]:
    """Convert documents sequentially using one default service instance."""
    return DocumentConversionService().convert_batch(requests)


def probe_engines(
    names: Sequence[EngineName] = tuple(EngineName),
) -> tuple[EngineProbeResult, ...]:
    """Probe requested engines using the default local engine registry."""
    return DocumentConversionService().probe_engines(names)
