"""Public application service for document conversion orchestration."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from gordon_doc_converter.engines.base import ConverterEngine
from gordon_doc_converter.engines.gotenberg import GotenbergEngine
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
from gordon_doc_converter.progress import ProgressCallback, ProgressEvent, ProgressState
from gordon_doc_converter.raster import PdfiumPageRenderer, PdfRasterizer


class DocumentConversionService:
    """Framework-independent service for single, batch, and engine-probe operations."""

    def __init__(
        self,
        engines: Iterable[ConverterEngine] | None = None,
        environment: EnvironmentInfo | None = None,
        *,
        gotenberg_url: str | None = None,
        rasterizer: PdfRasterizer | None = None,
    ) -> None:
        if engines is None:
            defaults: list[ConverterEngine] = [WordComEngine(), LibreOfficeEngine()]
            if gotenberg_url is not None:
                defaults.append(GotenbergEngine(gotenberg_url))
            configured_engines = tuple(defaults)
        else:
            configured_engines = tuple(engines)
        self._pipeline = ConversionPipeline(
            configured_engines,
            environment or detect_environment(),
            rasterizer or PdfRasterizer(PdfiumPageRenderer()),
        )

    def convert(
        self,
        request: ConversionRequest,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> ConversionResult:
        """Convert one request through policy-selected engines and stable result contracts."""
        return self._pipeline.convert(request, progress_callback=progress_callback)

    def convert_batch(
        self,
        requests: Iterable[ConversionRequest],
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[ConversionResult, ...]:
        """Convert requests sequentially so one item failure does not stop the batch."""
        queued = tuple(requests)
        results: list[ConversionResult] = []
        for index, request in enumerate(queued, start=1):
            if progress_callback is not None:
                progress_callback(
                    ProgressEvent(
                        "batch",
                        ProgressState.RUNNING,
                        "Converting batch item",
                        completed=index - 1,
                        total=len(queued),
                        source_name=request.source_path.name,
                    )
                )
            results.append(self.convert(request, progress_callback=progress_callback))
            if progress_callback is not None:
                progress_callback(
                    ProgressEvent(
                        "batch",
                        ProgressState.COMPLETED,
                        "Finished batch item",
                        completed=index,
                        total=len(queued),
                        source_name=request.source_path.name,
                    )
                )
        return tuple(results)

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
