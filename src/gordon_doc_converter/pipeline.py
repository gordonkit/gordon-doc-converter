"""Engine-neutral DOCX-to-PDF orchestration pipeline."""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from time import perf_counter

from gordon_doc_converter.content import (
    extract_docx_content,
    extract_pdf_content,
    write_content_artifacts,
)
from gordon_doc_converter.engines.base import ConverterEngine, EngineExecutionResult
from gordon_doc_converter.environment import EnvironmentInfo
from gordon_doc_converter.exceptions import (
    ConversionError,
    EngineFailedError,
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
    ConversionRequest,
    ConversionResult,
    ConversionWarning,
    EngineName,
    EngineProbeResult,
    SourceFormat,
)
from gordon_doc_converter.policies import EngineRejection, engine_order, select_engines
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


def _exception_warning(error: ConversionError, engine: EngineName) -> ConversionWarning:
    return ConversionWarning(
        code="ENGINE_FALLBACK",
        message=f"{engine.value}: {error.message}",
        engine=engine,
    )


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


def _output_stem(request: ConversionRequest) -> Path:
    configured = request.options.output_path
    if configured is None:
        return request.source_path.with_suffix("")
    if len(request.artifacts) > 1 or configured.suffix.casefold() in {
        ".pdf",
        ".md",
        ".html",
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

    def convert(self, request: ConversionRequest) -> ConversionResult:
        """Convert one supported request without exposing adapter-specific failures."""
        if request.source_format is SourceFormat.PDF or request.artifacts != (ArtifactType.PDF,):
            return self._convert_artifacts(request)
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
                    execution = engine.convert(
                        request.source_path,
                        staging_path,
                        timeout_seconds=request.options.timeout_seconds,
                        revision_mode=request.options.revision_mode,
                        comment_mode=request.options.comment_mode,
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

    def _convert_artifacts(self, request: ConversionRequest) -> ConversionResult:
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
            if artifact in {ArtifactType.MARKDOWN, ArtifactType.HTML}
        )
        if content_types:
            try:
                content = (
                    extract_docx_content(
                        request.source_path,
                        revision_mode=request.options.revision_mode,
                        comment_mode=request.options.comment_mode,
                        include_annotation_metadata=(request.options.include_annotation_metadata),
                    )
                    if request.source_format is SourceFormat.DOCX
                    else extract_pdf_content(request.source_path)
                )
                stem = _output_stem(request)
                written = write_content_artifacts(
                    content,
                    stem,
                    content_types,
                    overwrite=request.options.overwrite,
                )
                warnings.extend(content.warnings)
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
                    path = written.annotation_sidecar
                    shared_items.append(ArtifactItem(path, path.stat().st_size, "application/json"))
                for artifact_type, path in written.artifacts:
                    media_type = (
                        "text/markdown; charset=utf-8"
                        if artifact_type is ArtifactType.MARKDOWN
                        else "text/html; charset=utf-8"
                    )
                    item = ArtifactItem(path, path.stat().st_size, media_type)
                    results[artifact_type] = ArtifactResult(
                        artifact_type,
                        ArtifactStatus.SUCCESS,
                        path,
                        path.stat().st_size,
                        tuple(content.warnings),
                        items=(item, *shared_items),
                    )
            except FileExistsError as exc:
                error: ConversionError = OutputExistsError("content output already exists")
                error.__cause__ = exc
                self._record_artifact_failures(results, content_types, error)
            except ConversionError as error:
                self._record_artifact_failures(results, content_types, error)
            except (OSError, ValueError) as exc:
                write_error = EngineFailedError(
                    "content artifact could not be written", engine="extractor"
                )
                write_error.__cause__ = exc
                self._record_artifact_failures(results, content_types, write_error)

        needs_pdf = any(
            artifact in {ArtifactType.PDF, ArtifactType.PAGE_IMAGES}
            for artifact in request.artifacts
        )
        if needs_pdf:
            with TemporaryDirectory(prefix="gordon-doc-artifacts-") as temporary:
                temporary_pdf = Path(temporary) / "source.pdf"
                pdf_source = request.source_path
                pdf_error: ConversionFailure | None = None
                if request.source_format is SourceFormat.DOCX:
                    pdf_request = ConversionRequest(
                        request.source_path,
                        SourceFormat.DOCX,
                        (ArtifactType.PDF,),
                        replace(
                            request.options,
                            output_path=temporary_pdf,
                            overwrite=True,
                        ),
                    )
                    pdf_result = self.convert(pdf_request)
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
