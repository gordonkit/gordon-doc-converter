"""Engine-neutral DOCX-to-PDF orchestration pipeline."""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from time import perf_counter

from gordon_doc_converter.content import (
    NormalizedContent,
    extract_docx_content,
    extract_html_content,
    extract_markdown_content,
    extract_odt_content,
    extract_pdf_content,
    write_content_artifacts,
    write_print_document,
)
from gordon_doc_converter.engines.base import (
    ConverterEngine,
    EngineExecutionResult,
    FileConverterEngine,
)
from gordon_doc_converter.engines.pandoc import PandocConverter
from gordon_doc_converter.engines.wkhtmltopdf import WkhtmltopdfConverter
from gordon_doc_converter.engines.word_com import WordComEngine
from gordon_doc_converter.environment import EnvironmentInfo
from gordon_doc_converter.exceptions import (
    ConversionError,
    EngineFailedError,
    EngineUnavailableError,
    ErrorCode,
    InvalidInputError,
    OutputExistsError,
    PdfNotCreatedError,
    PdfValidationError,
)
from gordon_doc_converter.models import (
    ArtifactItem,
    ArtifactResult,
    ArtifactStatus,
    ArtifactType,
    ConversionFailure,
    ConversionOptions,
    ConversionRequest,
    ConversionResult,
    ConversionWarning,
    DeploymentMode,
    EngineName,
    EngineProbeResult,
    SourceFormat,
)
from gordon_doc_converter.policies import EngineRejection, engine_order, select_engines
from gordon_doc_converter.progress import ProgressCallback, ProgressEvent, ProgressState
from gordon_doc_converter.raster import ImageFormat, PdfRasterizer, RasterOptions
from gordon_doc_converter.validation import validate_pdf


def _failure_from_exception(error: ConversionError) -> ConversionFailure:
    engine: EngineName | None = None
    if error.engine is not None:
        try:
            engine = EngineName(error.engine)
        except ValueError:
            engine = None
    return ConversionFailure(
        code=error.code,
        message=error.message,
        engine=engine,
        retryable=error.retryable,
    )


def _fallback_warning(rejection: EngineRejection) -> ConversionWarning:
    return ConversionWarning(
        code="ENGINE_FALLBACK",
        message=f"{rejection.engine.value}: {rejection.reason}",
        engine=rejection.engine,
    )


def _markup_fallback_warning(unavailable: str, error: EngineUnavailableError) -> ConversionWarning:
    """Report that LibreOffice rendered markup because the preferred engine is missing."""
    return ConversionWarning(
        code="ENGINE_FALLBACK",
        message=f"{unavailable}: {error.message}; rendered with LibreOffice instead",
        engine=EngineName.LIBREOFFICE,
    )


def _exception_warning(error: ConversionError, engine: EngineName) -> ConversionWarning:
    return ConversionWarning(
        code="ENGINE_FALLBACK",
        message=f"{engine.value}: {error.message}",
        engine=engine,
    )


def _publish_staged_artifact(staged: Path, output: Path, *, overwrite: bool) -> None:
    """Move a staged artifact onto its output path, across filesystems if need be.

    The staging directory is a temporary one, which in a container is routinely a
    different device from the mounted output directory. ``Path.rename`` raises
    ``OSError`` (EXDEV) across devices, so the bytes are copied and the source removed.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    if not overwrite and output.exists():
        raise OutputExistsError("output already exists")
    shutil.move(str(staged), str(output))


def _publish_pdf(source: Path, target: Path, *, overwrite: bool) -> None:
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise EngineFailedError(
            "requested PDF output directory could not be created",
            engine="orchestrator",
        ) from exc
    if not overwrite:
        target_created = False
        try:
            with source.open("rb") as source_stream, target.open("xb") as target_stream:
                target_created = True
                shutil.copyfileobj(source_stream, target_stream)
        except FileExistsError as exc:
            raise OutputExistsError("PDF output already exists") from exc
        except OSError as exc:
            if target_created:
                target.unlink(missing_ok=True)
            raise EngineFailedError(
                "validated PDF could not be written to the requested output",
                engine="orchestrator",
            ) from exc
        return

    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="wb",
            prefix=".gordon-doc-",
            suffix=".pdf",
            dir=target.parent,
            delete=False,
        ) as target_stream:
            temporary_path = Path(target_stream.name)
            with source.open("rb") as source_stream:
                shutil.copyfileobj(source_stream, target_stream)
            target_stream.flush()
            os.fsync(target_stream.fileno())
        os.replace(temporary_path, target)
    except OSError as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise EngineFailedError(
            "validated PDF could not replace the requested output",
            engine="orchestrator",
        ) from exc


def _fix_word_com_html_line_heights(path: Path) -> None:
    """Replace Word's overly tight line-height:80% with a readable 120%."""
    text = path.read_text(encoding="utf-8")
    fixed = text.replace("line-height:80%", "line-height:120%")
    if fixed != text:
        path.write_text(fixed, encoding="utf-8")


_OFFICE_FILE_ARTIFACTS = frozenset({ArtifactType.PDF, ArtifactType.DOCX, ArtifactType.ODT})
_RENDERED_MARKUP_ARTIFACTS = (
    ArtifactType.PDF,
    ArtifactType.DOCX,
    ArtifactType.ODT,
    ArtifactType.PAGE_IMAGES,
)
_MARKUP_ARTIFACT_SUFFIXES = {
    ArtifactType.PDF: ".pdf",
    ArtifactType.DOCX: ".docx",
    ArtifactType.ODT: ".odt",
}
_MARKUP_MEDIA_TYPES = {
    ArtifactType.PDF: "application/pdf",
    ArtifactType.DOCX: ("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ArtifactType.ODT: "application/vnd.oasis.opendocument.text",
}
# Semantic outputs each markup source extracts without a rendering engine. A
# source never lists its own format, which would not be a conversion.
_SEMANTIC_MARKUP_ARTIFACTS: dict[SourceFormat, tuple[ArtifactType, ...]] = {
    SourceFormat.HTML: (ArtifactType.MARKDOWN, ArtifactType.YAML, ArtifactType.JSON),
    SourceFormat.MARKDOWN: (ArtifactType.HTML, ArtifactType.YAML, ArtifactType.JSON),
}
_CONTENT_MEDIA_TYPES = {
    ArtifactType.MARKDOWN: "text/markdown; charset=utf-8",
    ArtifactType.HTML: "text/html; charset=utf-8",
    ArtifactType.YAML: "application/yaml; charset=utf-8",
    ArtifactType.JSON: "application/json; charset=utf-8",
}
_JSONL_MEDIA_TYPE = "application/jsonl; charset=utf-8"


def _content_media_type(artifact_type: ArtifactType, *, json_lines: bool) -> str:
    if artifact_type is ArtifactType.JSON and json_lines:
        return _JSONL_MEDIA_TYPE
    return _CONTENT_MEDIA_TYPES[artifact_type]


def _output_stem(request: ConversionRequest) -> Path:
    configured = request.options.output_path
    if configured is None:
        return request.source_path.with_suffix("")
    if len(request.artifacts) > 1 or configured.suffix.casefold() in {
        ".pdf",
        ".docx",
        ".odt",
        ".md",
        ".html",
        ".yaml",
        ".yml",
        ".json",
        ".jsonl",
    }:
        return configured.with_suffix("")
    return configured


class ConversionPipeline:
    """Coordinate engine probing, selection, fallback, validation, and publication."""

    def __init__(
        self,
        engines: Iterable[ConverterEngine],
        environment: EnvironmentInfo,
        rasterizer: PdfRasterizer | None = None,
    ) -> None:
        registry: dict[EngineName, ConverterEngine] = {}
        for engine in engines:
            if engine.name in registry:
                raise InvalidInputError(f"duplicate engine registration: {engine.name.value}")
            registry[engine.name] = engine
        self._engines: Mapping[EngineName, ConverterEngine] = registry
        self._environment = environment
        self._rasterizer = rasterizer

    def probe_engines(self, names: Sequence[EngineName]) -> tuple[EngineProbeResult, ...]:
        """Probe requested engines while mapping adapter failures to safe results."""
        results: list[EngineProbeResult] = []
        for name in names:
            engine = self._engines.get(name)
            if engine is None:
                results.append(
                    EngineProbeResult(
                        engine=name,
                        available=False,
                        reason="engine adapter is not configured",
                    )
                )
                continue
            try:
                result = engine.probe()
            except Exception:
                result = EngineProbeResult(
                    engine=name,
                    available=False,
                    reason="engine probe failed",
                )
            if result.engine is not name:
                result = EngineProbeResult(
                    engine=name,
                    available=False,
                    reason="engine returned a mismatched probe identity",
                )
            results.append(result)
        return tuple(results)

    def _failure_result(
        self,
        request: ConversionRequest,
        error: ConversionError,
        *,
        output_path: Path | None,
        attempted_engines: tuple[EngineName, ...] = (),
        warnings: tuple[ConversionWarning, ...] = (),
        fallback_reason: str | None = None,
        selected_engine: EngineName | None = None,
        started: float,
    ) -> ConversionResult:
        failure = _failure_from_exception(error)
        artifacts = tuple(
            ArtifactResult(
                artifact_type=artifact,
                status=ArtifactStatus.FAILED,
                path=output_path if artifact is ArtifactType.PDF else None,
                warnings=warnings,
                error=failure,
            )
            for artifact in request.artifacts
        )
        return ConversionResult(
            success=False,
            source_format=request.source_format,
            artifacts=artifacts,
            selected_engine=selected_engine,
            attempted_engines=attempted_engines,
            warnings=warnings,
            error=failure,
            fallback_reason=fallback_reason,
            duration_seconds=perf_counter() - started,
            requested_revision_mode=request.options.revision_mode,
            requested_comment_mode=request.options.comment_mode,
        )

    @staticmethod
    def _report(
        callback: ProgressCallback | None,
        phase: str,
        message: str,
        *,
        state: ProgressState = ProgressState.RUNNING,
        engine: EngineName | None = None,
        artifact: ArtifactType | None = None,
    ) -> None:
        if callback is not None:
            callback(ProgressEvent(phase, state, message, engine=engine, artifact=artifact))

    def convert(
        self,
        request: ConversionRequest,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> ConversionResult:
        """Convert one supported request without exposing adapter-specific failures."""
        self._report(progress_callback, "validation", "Validating conversion request")
        if request.source_format in {SourceFormat.HTML, SourceFormat.MARKDOWN}:
            result = self._convert_markup(request, progress_callback)
        elif (
            request.source_format is SourceFormat.ODT or ArtifactType.ODT in request.artifacts
        ) and set(request.artifacts) <= _OFFICE_FILE_ARTIFACTS:
            result = self._convert_office_files(request, progress_callback)
        elif request.source_format in {SourceFormat.ODT, SourceFormat.PDF} or request.artifacts != (
            ArtifactType.PDF,
        ):
            result = self._convert_artifacts(request, progress_callback)
        else:
            result = self._convert_pdf(request, progress_callback)
        self._report(
            progress_callback,
            "conversion",
            "Conversion completed" if result.success else "Conversion failed",
            state=ProgressState.COMPLETED if result.success else ProgressState.FAILED,
        )
        return result

    def _convert_pdf(
        self,
        request: ConversionRequest,
        progress_callback: ProgressCallback | None,
    ) -> ConversionResult:
        """Convert one DOCX to PDF through a policy-selected rendering engine."""
        started = perf_counter()
        output_path = request.options.output_path or request.source_path.with_suffix(".pdf")
        order: tuple[EngineName, ...] = ()
        try:
            if request.source_format is not SourceFormat.DOCX or request.artifacts != (
                ArtifactType.PDF,
            ):
                raise InvalidInputError("only DOCX-to-PDF conversion is currently implemented")
            if not request.source_path.is_file():
                raise InvalidInputError("source DOCX file does not exist")
            if output_path.suffix.casefold() != ".pdf":
                raise InvalidInputError("PDF output must use the .pdf extension")
            if output_path.exists() and not request.options.overwrite:
                raise OutputExistsError("PDF output already exists")
            order = engine_order(request.options, self._environment)
            self._report(progress_callback, "engine-selection", "Selecting rendering engine")
            probes = self.probe_engines(order)
            selection = select_engines(request.options, self._environment, probes)
        except ConversionError as error:
            return self._failure_result(
                request,
                error,
                output_path=output_path,
                attempted_engines=order,
                started=started,
            )

        warnings: list[ConversionWarning] = []
        attempted: list[EngineName] = []
        fallback_reason: str | None = None
        rejected = {item.engine: item for item in selection.rejected}
        first_selected = order.index(selection.engines[0])
        for name in order[:first_selected]:
            rejection = rejected.get(name)
            if rejection is None:
                continue
            attempted.append(name)
            warning = _fallback_warning(rejection)
            warnings.append(warning)
            if fallback_reason is None:
                fallback_reason = warning.message

        with TemporaryDirectory(prefix="gordon-doc-pipeline-") as temporary:
            workspace = Path(temporary)
            for index, name in enumerate(selection.engines):
                attempted.append(name)
                engine = self._engines[name]
                staging_path = workspace / f"attempt-{index + 1}.pdf"
                try:
                    self._report(
                        progress_callback,
                        "rendering",
                        f"Rendering with {name.value}",
                        engine=name,
                        artifact=ArtifactType.PDF,
                    )
                    execution = engine.convert(
                        request.source_path,
                        staging_path,
                        timeout_seconds=request.options.timeout_seconds,
                        revision_mode=request.options.revision_mode,
                        comment_mode=request.options.comment_mode,
                    )
                    self._report(
                        progress_callback,
                        "pdf-validation",
                        "Validating rendered PDF",
                        engine=name,
                        artifact=ArtifactType.PDF,
                    )
                    output_size = self._validate_execution(execution, name, staging_path)
                except ConversionError as error:
                    if selection.allow_fallback and index + 1 < len(selection.engines):
                        warning = _exception_warning(error, name)
                        warnings.append(warning)
                        if fallback_reason is None:
                            fallback_reason = warning.message
                        continue
                    return self._failure_result(
                        request,
                        error,
                        output_path=output_path,
                        attempted_engines=tuple(attempted),
                        warnings=tuple(warnings),
                        fallback_reason=fallback_reason,
                        started=started,
                    )
                except Exception as cause:
                    try:
                        raise EngineFailedError(
                            "conversion engine raised an unexpected failure",
                            engine=name.value,
                        ) from cause
                    except EngineFailedError as error:
                        if selection.allow_fallback and index + 1 < len(selection.engines):
                            warning = _exception_warning(error, name)
                            warnings.append(warning)
                            if fallback_reason is None:
                                fallback_reason = warning.message
                            continue
                        return self._failure_result(
                            request,
                            error,
                            output_path=output_path,
                            attempted_engines=tuple(attempted),
                            warnings=tuple(warnings),
                            fallback_reason=fallback_reason,
                            started=started,
                        )

                warnings.extend(execution.warnings)
                try:
                    self._report(
                        progress_callback,
                        "publication",
                        "Publishing validated PDF",
                        engine=name,
                        artifact=ArtifactType.PDF,
                    )
                    _publish_pdf(
                        staging_path,
                        output_path,
                        overwrite=request.options.overwrite,
                    )
                except ConversionError as error:
                    return self._failure_result(
                        request,
                        error,
                        output_path=output_path,
                        attempted_engines=tuple(attempted),
                        warnings=tuple(warnings),
                        fallback_reason=fallback_reason,
                        selected_engine=name,
                        started=started,
                    )
                artifact_warnings = tuple(warnings)
                return ConversionResult(
                    success=True,
                    source_format=request.source_format,
                    artifacts=(
                        ArtifactResult(
                            artifact_type=ArtifactType.PDF,
                            status=ArtifactStatus.SUCCESS,
                            path=output_path,
                            size_bytes=output_size,
                            warnings=artifact_warnings,
                        ),
                    ),
                    selected_engine=name,
                    attempted_engines=tuple(attempted),
                    warnings=artifact_warnings,
                    fallback_reason=fallback_reason,
                    duration_seconds=perf_counter() - started,
                    requested_revision_mode=request.options.revision_mode,
                    effective_revision_mode=request.options.revision_mode,
                    requested_comment_mode=request.options.comment_mode,
                    effective_comment_mode=request.options.comment_mode,
                )

        raise AssertionError("engine selection produced no executable engine")

    def _convert_office_files(
        self,
        request: ConversionRequest,
        progress_callback: ProgressCallback | None,
        *,
        output_stem: Path | None = None,
    ) -> ConversionResult:
        """Convert DOCX/ODT files through the LibreOffice file adapter."""
        started = perf_counter()
        supported = set(_OFFICE_FILE_ARTIFACTS)
        if request.source_format not in {SourceFormat.DOCX, SourceFormat.ODT}:
            error: ConversionError = InvalidInputError(
                "office file conversion requires a DOCX or ODT source"
            )
            return self._failure_result(request, error, output_path=None, started=started)
        if set(request.artifacts) - supported:
            error = InvalidInputError("office file conversion supports only PDF, DOCX, and ODT")
            return self._failure_result(request, error, output_path=None, started=started)
        if not request.source_path.is_file():
            error = InvalidInputError("source office file does not exist")
            return self._failure_result(request, error, output_path=None, started=started)
        if request.options.engine not in {None, EngineName.LIBREOFFICE}:
            error = InvalidInputError("DOCX and ODT file conversion requires LibreOffice")
            return self._failure_result(request, error, output_path=None, started=started)
        engine = self._engines.get(EngineName.LIBREOFFICE)
        if engine is None:
            error = EngineFailedError(
                "LibreOffice file conversion adapter is not configured",
                engine=EngineName.LIBREOFFICE.value,
            )
            return self._failure_result(request, error, output_path=None, started=started)
        if not isinstance(engine, FileConverterEngine):
            error = EngineFailedError(
                "configured LibreOffice adapter does not support file conversion",
                engine=EngineName.LIBREOFFICE.value,
            )
            return self._failure_result(request, error, output_path=None, started=started)
        try:
            probe = engine.probe()
        except Exception as cause:
            error = EngineFailedError(
                "LibreOffice file conversion probe failed",
                engine=EngineName.LIBREOFFICE.value,
            )
            error.__cause__ = cause
            return self._failure_result(request, error, output_path=None, started=started)
        if not probe.available:
            error = EngineFailedError(
                probe.reason or "LibreOffice is unavailable",
                engine=EngineName.LIBREOFFICE.value,
            )
            return self._failure_result(request, error, output_path=None, started=started)

        results: list[ArtifactResult] = []
        with TemporaryDirectory(prefix="gordon-doc-office-") as temporary:
            workspace = Path(temporary)
            for index, artifact_type in enumerate(request.artifacts):
                suffix = ".pdf" if artifact_type is ArtifactType.PDF else f".{artifact_type.value}"
                output = (
                    request.options.output_path
                    if output_stem is None
                    and len(request.artifacts) == 1
                    and request.options.output_path is not None
                    else (output_stem or _output_stem(request)).with_suffix(suffix)
                )
                if output.suffix.casefold() != suffix:
                    results.append(
                        ArtifactResult(
                            artifact_type,
                            ArtifactStatus.FAILED,
                            error=_failure_from_exception(
                                InvalidInputError(f"{artifact_type.value} output must use {suffix}")
                            ),
                        )
                    )
                    continue
                if output.exists() and not request.options.overwrite:
                    results.append(
                        ArtifactResult(
                            artifact_type,
                            ArtifactStatus.FAILED,
                            error=_failure_from_exception(
                                OutputExistsError("conversion output already exists")
                            ),
                        )
                    )
                    continue
                staged = workspace / f"output-{index}{suffix}"
                try:
                    self._report(
                        progress_callback,
                        "rendering",
                        f"Creating {artifact_type.value} artifact",
                        engine=EngineName.LIBREOFFICE,
                        artifact=artifact_type,
                    )
                    execution = engine.convert_file(
                        request.source_path,
                        staged,
                        source_format=request.source_format,
                        artifact_type=artifact_type,
                        timeout_seconds=request.options.timeout_seconds,
                    )
                    if (
                        execution.engine is not EngineName.LIBREOFFICE
                        or execution.output_path != staged
                    ):
                        raise EngineFailedError(
                            "LibreOffice returned a mismatched file conversion result",
                            engine=EngineName.LIBREOFFICE.value,
                        )
                    _publish_staged_artifact(staged, output, overwrite=request.options.overwrite)
                    size = output.stat().st_size
                    media_type = (
                        "application/pdf"
                        if artifact_type is ArtifactType.PDF
                        else (
                            "application/vnd.oasis.opendocument.text"
                            if artifact_type is ArtifactType.ODT
                            else (
                                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )
                        )
                    )
                    results.append(
                        ArtifactResult(
                            artifact_type,
                            ArtifactStatus.SUCCESS,
                            output,
                            size,
                            items=(ArtifactItem(output, size, media_type),),
                        )
                    )
                except ConversionError as error:
                    results.append(
                        ArtifactResult(
                            artifact_type,
                            ArtifactStatus.FAILED,
                            error=_failure_from_exception(error),
                        )
                    )
        successful = all(item.status is ArtifactStatus.SUCCESS for item in results)
        first_error = next((item.error for item in results if item.error is not None), None)
        return ConversionResult(
            success=successful,
            source_format=request.source_format,
            artifacts=tuple(results),
            selected_engine=EngineName.LIBREOFFICE if successful else None,
            attempted_engines=(EngineName.LIBREOFFICE,),
            error=first_error,
            duration_seconds=perf_counter() - started,
            requested_revision_mode=request.options.revision_mode,
            effective_revision_mode=(request.options.revision_mode if successful else None),
            requested_comment_mode=request.options.comment_mode,
            effective_comment_mode=(request.options.comment_mode if successful else None),
        )

    def _convert_markup(
        self,
        request: ConversionRequest,
        progress_callback: ProgressCallback | None,
    ) -> ConversionResult:
        """Convert HTML or Markdown to rendered A4 documents or semantic artifacts."""
        started = perf_counter()
        semantic = _SEMANTIC_MARKUP_ARTIFACTS.get(request.source_format, ())
        invalid = set(request.artifacts) - set(_RENDERED_MARKUP_ARTIFACTS) - set(semantic)
        if invalid:
            message = (
                "HTML sources support only PDF, DOCX, ODT, page image, Markdown, YAML, "
                "and JSON outputs"
                if request.source_format is SourceFormat.HTML
                else "Markdown sources support only PDF, DOCX, ODT, page image, HTML, YAML, "
                "and JSON outputs"
            )
            return self._failure_result(
                request,
                InvalidInputError(message),
                output_path=None,
                started=started,
            )
        if not request.source_path.is_file():
            return self._failure_result(
                request,
                InvalidInputError("source markup file does not exist"),
                output_path=None,
                started=started,
            )

        collected: dict[ArtifactType, ArtifactResult] = {}
        warnings: list[ConversionWarning] = []
        content_types = tuple(item for item in request.artifacts if item in semantic)
        if content_types:
            warnings.extend(
                self._write_semantic_artifacts(
                    request,
                    content_types,
                    collected,
                    progress_callback,
                )
            )
        rendered_types = tuple(item for item in request.artifacts if item not in semantic)
        if rendered_types:
            rendered_warnings = self._render_markup_artifacts(
                request,
                rendered_types,
                collected,
                progress_callback,
            )
            seen = {(warning.code, warning.message) for warning in warnings}
            warnings.extend(
                warning
                for warning in rendered_warnings
                if (warning.code, warning.message) not in seen
            )

        results = tuple(
            collected[artifact] for artifact in request.artifacts if artifact in collected
        )
        success = all(item.status is ArtifactStatus.SUCCESS for item in results)
        first_error = next((item.error for item in results if item.error is not None), None)
        return ConversionResult(
            success=success,
            source_format=request.source_format,
            artifacts=results,
            warnings=tuple(warnings),
            error=first_error,
            duration_seconds=perf_counter() - started,
        )

    def _render_markup_artifacts(
        self,
        request: ConversionRequest,
        artifact_types: tuple[ArtifactType, ...],
        results: dict[ArtifactType, ArtifactResult],
        progress_callback: ProgressCallback | None,
    ) -> tuple[ConversionWarning, ...]:
        """Render markup to validated A4 documents through the engine each artifact needs."""
        warnings: tuple[ConversionWarning, ...] = ()
        with TemporaryDirectory(prefix="gordon-doc-markup-") as temporary:
            workspace = Path(temporary)
            print_source = request.source_path
            docx_source = request.source_path
            render_format = request.source_format
            if request.source_format is SourceFormat.MARKDOWN:
                # Markdown reaches the engines as our own print-ready HTML, so both
                # markup sources render with the same A4 page setup and CJK fonts.
                try:
                    self._report(
                        progress_callback,
                        "content-extraction",
                        "Preparing print-ready markup",
                    )
                    content = self._extract_content(request)
                    print_source = write_print_document(
                        content,
                        workspace / "intermediate",
                        orientation=request.options.page_orientation,
                    )
                    # Pandoc renders its own title block from the head metadata, so the
                    # copy it reads leaves the visible one out.
                    docx_source = write_print_document(
                        content,
                        workspace / "intermediate-docx",
                        orientation=request.options.page_orientation,
                        metadata_block=False,
                    )
                    render_format = SourceFormat.HTML
                    warnings = content.warnings
                except ConversionError as error:
                    failure = _failure_from_exception(error)
                    for artifact_type in artifact_types:
                        results[artifact_type] = ArtifactResult(
                            artifact_type,
                            ArtifactStatus.FAILED,
                            error=failure,
                        )
                    return warnings
            rendered_pdf: Path | None = None
            for artifact_type in artifact_types:
                if artifact_type is ArtifactType.PAGE_IMAGES:
                    continue
                suffix = _MARKUP_ARTIFACT_SUFFIXES[artifact_type]
                output = (
                    request.options.output_path
                    if len(request.artifacts) == 1 and request.options.output_path is not None
                    else _output_stem(request).with_suffix(suffix)
                )
                if output.suffix.casefold() != suffix:
                    results[artifact_type] = ArtifactResult(
                        artifact_type,
                        ArtifactStatus.FAILED,
                        error=_failure_from_exception(
                            InvalidInputError(
                                f"{artifact_type.value} output must use the {suffix} extension"
                            )
                        ),
                    )
                    continue
                if output.exists() and not request.options.overwrite:
                    results[artifact_type] = ArtifactResult(
                        artifact_type,
                        ArtifactStatus.FAILED,
                        error=_failure_from_exception(OutputExistsError("output already exists")),
                    )
                    continue
                staged = workspace / f"output{suffix}"
                try:
                    self._report(
                        progress_callback,
                        "rendering",
                        f"Creating {artifact_type.value} artifact",
                        artifact=artifact_type,
                    )
                    warnings += self._render_markup_file(
                        print_source if artifact_type is not ArtifactType.DOCX else docx_source,
                        staged,
                        source_format=render_format,
                        artifact_type=artifact_type,
                        options=request.options,
                    )
                    if artifact_type is ArtifactType.PDF:
                        validation = validate_pdf(staged)
                        if not validation.valid:
                            raise PdfValidationError("generated PDF failed validation")
                    _publish_staged_artifact(staged, output, overwrite=request.options.overwrite)
                    if artifact_type is ArtifactType.PDF:
                        rendered_pdf = output
                    size = output.stat().st_size
                    results[artifact_type] = ArtifactResult(
                        artifact_type,
                        ArtifactStatus.SUCCESS,
                        output,
                        size,
                        items=(ArtifactItem(output, size, _MARKUP_MEDIA_TYPES[artifact_type]),),
                    )
                except ConversionError as error:
                    results[artifact_type] = ArtifactResult(
                        artifact_type,
                        ArtifactStatus.FAILED,
                        error=_failure_from_exception(error),
                    )
            if ArtifactType.PAGE_IMAGES in artifact_types:
                self._rasterize_markup(
                    request,
                    workspace,
                    print_source,
                    rendered_pdf,
                    results,
                    progress_callback,
                )
        return warnings

    def _render_markup_file(
        self,
        source_path: Path,
        output_path: Path,
        *,
        source_format: SourceFormat,
        artifact_type: ArtifactType,
        options: ConversionOptions,
    ) -> tuple[ConversionWarning, ...]:
        """Render one markup file through the engine that owns its artifact type.

        wkhtmltopdf and Pandoc render markup with the highest fidelity, but neither ships
        in the container image, so an installation without them falls back to LibreOffice
        and reports the substitution. LibreOffice reads the same print HTML and keeps the
        A4 page setup; its table borders and heading fonts differ from wkhtmltopdf.
        """
        if artifact_type is ArtifactType.PDF:
            # The PDF engine reads the document itself, keeping its stylesheet intact.
            try:
                WkhtmltopdfConverter().convert(source_path, output_path, options=options)
            except EngineUnavailableError as error:
                self._render_markup_with_libreoffice(
                    source_path,
                    output_path,
                    source_format=source_format,
                    artifact_type=artifact_type,
                    options=options,
                )
                return (_markup_fallback_warning("wkhtmltopdf", error),)
            return ()
        if artifact_type is ArtifactType.DOCX:
            try:
                PandocConverter().convert(
                    source_path,
                    output_path,
                    source_format=source_format,
                    options=options,
                )
            except EngineUnavailableError as error:
                self._render_markup_with_libreoffice(
                    source_path,
                    output_path,
                    source_format=source_format,
                    artifact_type=artifact_type,
                    options=options,
                )
                return (_markup_fallback_warning("pandoc", error),)
            return ()
        # LibreOffice reads our print CSS, so ODT keeps the A4 page setup Pandoc cannot carry.
        self._render_markup_with_libreoffice(
            source_path,
            output_path,
            source_format=source_format,
            artifact_type=artifact_type,
            options=options,
        )
        return ()

    def _render_markup_with_libreoffice(
        self,
        source_path: Path,
        output_path: Path,
        *,
        source_format: SourceFormat,
        artifact_type: ArtifactType,
        options: ConversionOptions,
    ) -> None:
        """Render print HTML through LibreOffice, the engine every deployment carries."""
        engine = self._markup_file_engine()
        execution = engine.convert_file(
            source_path,
            output_path,
            source_format=source_format,
            artifact_type=artifact_type,
            timeout_seconds=options.timeout_seconds,
        )
        if execution.engine is not EngineName.LIBREOFFICE or execution.output_path != output_path:
            raise EngineFailedError(
                "LibreOffice returned a mismatched file conversion result",
                engine=EngineName.LIBREOFFICE.value,
            )

    def _markup_file_engine(self) -> FileConverterEngine:
        """Return a probed LibreOffice file adapter, or explain why markup cannot use one."""
        engine = self._engines.get(EngineName.LIBREOFFICE)
        if engine is None or not isinstance(engine, FileConverterEngine):
            raise EngineFailedError(
                "LibreOffice file conversion adapter is not configured",
                engine=EngineName.LIBREOFFICE.value,
            )
        try:
            probe = engine.probe()
        except Exception as cause:
            error = EngineFailedError(
                "LibreOffice file conversion probe failed",
                engine=EngineName.LIBREOFFICE.value,
            )
            error.__cause__ = cause
            raise error from cause
        if not probe.available:
            raise EngineFailedError(
                probe.reason or "LibreOffice is unavailable",
                engine=EngineName.LIBREOFFICE.value,
            )
        return engine

    def _rasterize_markup(
        self,
        request: ConversionRequest,
        workspace: Path,
        print_source: Path,
        rendered_pdf: Path | None,
        results: dict[ArtifactType, ArtifactResult],
        progress_callback: ProgressCallback | None,
    ) -> None:
        """Rasterize markup pages, reusing a requested PDF instead of rendering twice."""
        try:
            if self._rasterizer is None:
                raise InvalidInputError("page-image output requires a configured rasterizer")
            source = rendered_pdf
            if source is None:
                source = workspace / "pages.pdf"
                self._report(
                    progress_callback,
                    "rendering",
                    "Rendering pages for rasterization",
                    artifact=ArtifactType.PAGE_IMAGES,
                )
                WkhtmltopdfConverter().convert(
                    print_source,
                    source,
                    options=request.options,
                )
                validation = validate_pdf(source)
                if not validation.valid:
                    raise PdfValidationError("generated PDF failed validation")
            directory = (
                request.options.output_path
                if len(request.artifacts) == 1 and request.options.output_path is not None
                else _output_stem(request).with_name(f"{_output_stem(request).name}.pages")
            )
            self._report(
                progress_callback,
                "rasterization",
                "Rendering PDF pages as images",
                artifact=ArtifactType.PAGE_IMAGES,
            )
            images = self._rasterizer.rasterize(
                source,
                directory,
                options=RasterOptions(
                    dpi=request.options.image_dpi,
                    image_format=ImageFormat(request.options.image_format.value),
                    quality=request.options.image_quality,
                    pages=request.options.image_pages,
                    background=request.options.image_background,
                    overwrite=request.options.overwrite,
                ),
            )
        except ConversionError as error:
            self._record_artifact_failures(results, (ArtifactType.PAGE_IMAGES,), error)
            return
        items = tuple(
            ArtifactItem(
                image.path,
                image.size_bytes,
                "image/png" if image.image_format is ImageFormat.PNG else "image/jpeg",
                image.page_number,
                image.width_pixels,
                image.height_pixels,
                image.sha256,
            )
            for image in images
        )
        results[ArtifactType.PAGE_IMAGES] = ArtifactResult(
            ArtifactType.PAGE_IMAGES,
            ArtifactStatus.SUCCESS,
            directory,
            sum(item.size_bytes for item in items),
            items=items,
        )

    @staticmethod
    def _should_use_word_com_html(request: ConversionRequest) -> bool:
        """Check whether Word COM should be attempted for HTML output."""
        if request.source_format is not SourceFormat.DOCX:
            return False
        if request.options.engine is EngineName.WORD_COM:
            return True
        if request.options.engine is not None:
            return False
        if request.options.deployment_mode is not DeploymentMode.DESKTOP:
            return False
        return sys.platform == "win32"

    @staticmethod
    def _get_word_com_engine() -> WordComEngine:
        """Return a fresh Word COM engine adapter."""
        return WordComEngine()

    @staticmethod
    def _html_output_path(request: ConversionRequest) -> Path:
        """Determine the HTML output path for a Word COM HTML conversion."""
        if len(request.artifacts) == 1 and request.options.output_path is not None:
            return request.options.output_path
        return _output_stem(request).with_suffix(".html")

    def _extract_content(self, request: ConversionRequest) -> NormalizedContent:
        """Extract normalized semantic content for one supported source format."""
        if request.source_format is SourceFormat.DOCX:
            return extract_docx_content(
                request.source_path,
                revision_mode=request.options.revision_mode,
                comment_mode=request.options.comment_mode,
                include_annotation_metadata=request.options.include_annotation_metadata,
                metadata_detail=request.options.metadata_detail,
            )
        if request.source_format is SourceFormat.ODT:
            return extract_odt_content(
                request.source_path,
                revision_mode=request.options.revision_mode,
                comment_mode=request.options.comment_mode,
                include_annotation_metadata=request.options.include_annotation_metadata,
                metadata_detail=request.options.metadata_detail,
            )
        if request.source_format is SourceFormat.HTML:
            return extract_html_content(
                request.source_path,
                metadata_detail=request.options.metadata_detail,
            )
        if request.source_format is SourceFormat.MARKDOWN:
            return extract_markdown_content(
                request.source_path,
                metadata_detail=request.options.metadata_detail,
            )
        return extract_pdf_content(
            request.source_path,
            metadata_detail=request.options.metadata_detail,
        )

    def _write_semantic_artifacts(
        self,
        request: ConversionRequest,
        content_types: tuple[ArtifactType, ...],
        results: dict[ArtifactType, ArtifactResult],
        progress_callback: ProgressCallback | None,
    ) -> tuple[ConversionWarning, ...]:
        """Extract and serialize semantic artifacts sharing one asset directory."""
        try:
            self._report(progress_callback, "content-extraction", "Extracting semantic content")
            content = self._extract_content(request)
            self._report(progress_callback, "serialization", "Writing semantic artifacts")
            written = write_content_artifacts(
                content,
                _output_stem(request),
                content_types,
                overwrite=request.options.overwrite,
                json_lines=request.options.json_lines,
            )
        except FileExistsError as exc:
            error: ConversionError = OutputExistsError("content output already exists")
            error.__cause__ = exc
            self._record_artifact_failures(results, content_types, error)
            return ()
        except ConversionError as error:
            self._record_artifact_failures(results, content_types, error)
            return ()
        except (OSError, ValueError) as exc:
            write_error = EngineFailedError(
                "content artifact could not be written", engine="extractor"
            )
            write_error.__cause__ = exc
            self._record_artifact_failures(results, content_types, write_error)
            return ()

        shared_items: list[ArtifactItem] = []
        if written.asset_directory is not None:
            for path in sorted(written.asset_directory.iterdir()):
                if path.is_file():
                    shared_items.append(
                        ArtifactItem(
                            path=path,
                            size_bytes=path.stat().st_size,
                            media_type=(
                                "application/json"
                                if path.suffix == ".json"
                                else "application/octet-stream"
                            ),
                        )
                    )
        if written.annotation_sidecar is not None:
            sidecar = written.annotation_sidecar
            shared_items.append(ArtifactItem(sidecar, sidecar.stat().st_size, "application/json"))
        for artifact_type, path in written.artifacts:
            size = path.stat().st_size
            media_type = _content_media_type(artifact_type, json_lines=request.options.json_lines)
            item = ArtifactItem(path, size, media_type)
            results[artifact_type] = ArtifactResult(
                artifact_type,
                ArtifactStatus.SUCCESS,
                path,
                size,
                tuple(content.warnings),
                items=(item, *shared_items),
            )
        return content.warnings

    def _convert_artifacts(
        self,
        request: ConversionRequest,
        progress_callback: ProgressCallback | None,
    ) -> ConversionResult:
        """Produce independent semantic and raster artifacts with partial-failure reporting."""
        started = perf_counter()
        results: dict[ArtifactType, ArtifactResult] = {}
        warnings: list[ConversionWarning] = []
        selected_engine: EngineName | None = None
        attempted_engines: tuple[EngineName, ...] = ()
        fallback_reason: str | None = None

        if not request.source_path.is_file():
            return self._failure_result(
                request,
                InvalidInputError("source document does not exist"),
                output_path=None,
                started=started,
            )

        content_types = tuple(
            artifact
            for artifact in request.artifacts
            if artifact
            in {
                ArtifactType.MARKDOWN,
                ArtifactType.HTML,
                ArtifactType.YAML,
                ArtifactType.JSON,
            }
        )

        office_types = tuple(
            artifact
            for artifact in request.artifacts
            if artifact in {ArtifactType.DOCX, ArtifactType.ODT}
        )
        if office_types:
            office_result = self._convert_office_files(
                replace(request, artifacts=office_types),
                progress_callback,
                output_stem=_output_stem(request),
            )
            for artifact in office_result.artifacts:
                results[artifact.artifact_type] = artifact
            warnings.extend(office_result.warnings)
            selected_engine = office_result.selected_engine or selected_engine
            attempted_engines = office_result.attempted_engines or attempted_engines

        html_via_word_com = ArtifactType.HTML in content_types and self._should_use_word_com_html(
            request
        )
        if html_via_word_com:
            html_output = self._html_output_path(request)
            try:
                self._report(
                    progress_callback,
                    "rendering",
                    "Rendering HTML with Word COM",
                    engine=EngineName.WORD_COM,
                    artifact=ArtifactType.HTML,
                )
                word_com = self._get_word_com_engine()
                if request.options.overwrite and html_output.exists():
                    html_output.unlink()
                word_com.convert_file(
                    request.source_path,
                    html_output,
                    source_format=request.source_format,
                    artifact_type=ArtifactType.HTML,
                    timeout_seconds=request.options.timeout_seconds,
                )
                _fix_word_com_html_line_heights(html_output)
                size = html_output.stat().st_size
                results[ArtifactType.HTML] = ArtifactResult(
                    ArtifactType.HTML,
                    ArtifactStatus.SUCCESS,
                    html_output,
                    size,
                    items=(ArtifactItem(html_output, size, "text/html; charset=utf-8"),),
                )
                selected_engine = EngineName.WORD_COM
                content_types = tuple(ct for ct in content_types if ct is not ArtifactType.HTML)
            except ConversionError as html_error:
                if request.options.engine is EngineName.WORD_COM:
                    self._record_artifact_failures(results, (ArtifactType.HTML,), html_error)
                    content_types = tuple(ct for ct in content_types if ct is not ArtifactType.HTML)
                else:
                    html_via_word_com = False

        if content_types:
            warnings.extend(
                self._write_semantic_artifacts(
                    request,
                    content_types,
                    results,
                    progress_callback,
                )
            )

        needs_pdf = any(
            artifact in {ArtifactType.PDF, ArtifactType.PAGE_IMAGES}
            for artifact in request.artifacts
        )
        if needs_pdf:
            with TemporaryDirectory(prefix="gordon-doc-artifacts-") as temporary:
                temporary_pdf = Path(temporary) / "source.pdf"
                pdf_source = request.source_path
                pdf_error: ConversionFailure | None = None
                if request.source_format in {SourceFormat.DOCX, SourceFormat.ODT}:
                    pdf_request = ConversionRequest(
                        request.source_path,
                        request.source_format,
                        (ArtifactType.PDF,),
                        replace(
                            request.options,
                            output_path=temporary_pdf,
                            overwrite=True,
                        ),
                    )
                    pdf_result = self.convert(
                        pdf_request,
                        progress_callback=progress_callback,
                    )
                    selected_engine = pdf_result.selected_engine
                    attempted_engines = pdf_result.attempted_engines
                    fallback_reason = pdf_result.fallback_reason
                    warnings.extend(pdf_result.warnings)
                    if pdf_result.success:
                        pdf_source = temporary_pdf
                    else:
                        pdf_error = pdf_result.error
                else:
                    validation = validate_pdf(pdf_source)
                    if not validation.valid:
                        pdf_error = validation.error

                if ArtifactType.PDF in request.artifacts:
                    if pdf_error is not None:
                        results[ArtifactType.PDF] = ArtifactResult(
                            ArtifactType.PDF,
                            ArtifactStatus.FAILED,
                            error=pdf_error,
                        )
                    else:
                        output = (
                            request.options.output_path
                            if len(request.artifacts) == 1
                            and request.options.output_path is not None
                            else _output_stem(request).with_suffix(".pdf")
                        )
                        try:
                            if output.suffix.casefold() != ".pdf":
                                raise InvalidInputError("PDF output must use the .pdf extension")
                            if request.source_format is SourceFormat.PDF and (
                                output.resolve() == request.source_path.resolve()
                            ):
                                raise OutputExistsError("PDF input and output paths are identical")
                            _publish_pdf(
                                pdf_source,
                                output,
                                overwrite=request.options.overwrite,
                            )
                            size = output.stat().st_size
                            results[ArtifactType.PDF] = ArtifactResult(
                                ArtifactType.PDF,
                                ArtifactStatus.SUCCESS,
                                output,
                                size,
                                items=(ArtifactItem(output, size, "application/pdf"),),
                            )
                        except ConversionError as error:
                            self._record_artifact_failures(results, (ArtifactType.PDF,), error)

                if ArtifactType.PAGE_IMAGES in request.artifacts:
                    if pdf_error is not None:
                        results[ArtifactType.PAGE_IMAGES] = ArtifactResult(
                            ArtifactType.PAGE_IMAGES,
                            ArtifactStatus.FAILED,
                            error=pdf_error,
                        )
                    elif self._rasterizer is None:
                        self._record_artifact_failures(
                            results,
                            (ArtifactType.PAGE_IMAGES,),
                            InvalidInputError("page-image output requires a configured rasterizer"),
                        )
                    else:
                        directory = (
                            request.options.output_path
                            if len(request.artifacts) == 1
                            and request.options.output_path is not None
                            else _output_stem(request).with_name(
                                f"{_output_stem(request).name}.pages"
                            )
                        )
                        try:
                            self._report(
                                progress_callback,
                                "rasterization",
                                "Rendering PDF pages as images",
                                artifact=ArtifactType.PAGE_IMAGES,
                            )
                            images = self._rasterizer.rasterize(
                                pdf_source,
                                directory,
                                options=RasterOptions(
                                    dpi=request.options.image_dpi,
                                    image_format=ImageFormat(request.options.image_format.value),
                                    quality=request.options.image_quality,
                                    pages=request.options.image_pages,
                                    background=request.options.image_background,
                                    overwrite=request.options.overwrite,
                                ),
                            )
                            items = tuple(
                                ArtifactItem(
                                    image.path,
                                    image.size_bytes,
                                    (
                                        "image/png"
                                        if image.image_format is ImageFormat.PNG
                                        else "image/jpeg"
                                    ),
                                    image.page_number,
                                    image.width_pixels,
                                    image.height_pixels,
                                    image.sha256,
                                )
                                for image in images
                            )
                            results[ArtifactType.PAGE_IMAGES] = ArtifactResult(
                                ArtifactType.PAGE_IMAGES,
                                ArtifactStatus.SUCCESS,
                                directory,
                                sum(item.size_bytes for item in items),
                                items=items,
                            )
                        except ConversionError as error:
                            self._record_artifact_failures(
                                results, (ArtifactType.PAGE_IMAGES,), error
                            )

        ordered = tuple(results[artifact] for artifact in request.artifacts)
        successful = all(item.status is ArtifactStatus.SUCCESS for item in ordered)
        first_error = next((item.error for item in ordered if item.error is not None), None)
        return ConversionResult(
            success=successful,
            source_format=request.source_format,
            artifacts=ordered,
            selected_engine=selected_engine,
            attempted_engines=attempted_engines,
            warnings=tuple(warnings),
            error=first_error,
            fallback_reason=fallback_reason,
            duration_seconds=perf_counter() - started,
            requested_revision_mode=request.options.revision_mode,
            effective_revision_mode=(
                request.options.revision_mode if selected_engine is not None else None
            ),
            requested_comment_mode=request.options.comment_mode,
            effective_comment_mode=(
                request.options.comment_mode if selected_engine is not None else None
            ),
        )

    @staticmethod
    def _record_artifact_failures(
        results: dict[ArtifactType, ArtifactResult],
        artifacts: tuple[ArtifactType, ...],
        error: ConversionError,
    ) -> None:
        failure = _failure_from_exception(error)
        for artifact in artifacts:
            results[artifact] = ArtifactResult(
                artifact,
                ArtifactStatus.FAILED,
                error=failure,
            )

    @staticmethod
    def _validate_execution(
        execution: EngineExecutionResult,
        expected_engine: EngineName,
        expected_path: Path,
    ) -> int:
        if execution.engine is not expected_engine or execution.output_path != expected_path:
            raise EngineFailedError(
                "conversion engine returned a mismatched execution result",
                engine=expected_engine.value,
            )
        validation = validate_pdf(expected_path)
        if validation.valid:
            return validation.file_size
        if validation.error is not None and validation.error.code is ErrorCode.PDF_NOT_CREATED:
            raise PdfNotCreatedError(
                "conversion engine did not create a non-empty PDF",
                engine=expected_engine.value,
            )
        raise PdfValidationError(
            "conversion engine created an invalid PDF",
            engine=expected_engine.value,
        )
