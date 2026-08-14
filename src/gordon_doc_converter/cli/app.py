"""Typer commands for the public document conversion service."""

from __future__ import annotations

import json
from collections.abc import Callable
from enum import IntEnum
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, TypeVar

import typer

from gordon_doc_converter.comparison import PdfComparisonService, PillowImageDiffer
from gordon_doc_converter.environment import detect_environment
from gordon_doc_converter.exceptions import ConversionError, ErrorCode
from gordon_doc_converter.models import (
    ArtifactType,
    CommentMode,
    ConversionOptions,
    ConversionRequest,
    ConversionResult,
    DeploymentMode,
    EngineName,
    EngineProbeResult,
    PageImageFormat,
    PageOrientation,
    RevisionMode,
)
from gordon_doc_converter.models_types import JsonValue
from gordon_doc_converter.raster import PdfiumPageRenderer, PdfRasterizer
from gordon_doc_converter.service import DocumentConversionService
from gordon_doc_converter.template import write_blank_html_template


class ExitCode(IntEnum):
    """Stable process exit codes exposed by the CLI."""

    SUCCESS = 0
    INPUT_ERROR = 2
    ENGINE_UNAVAILABLE = 3
    CONVERSION_FAILED = 4
    VALIDATION_FAILED = 5


app = typer.Typer(
    help="Diagnosable multi-engine DOCX-to-PDF conversion.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

CommandFunction = TypeVar("CommandFunction", bound=Callable[..., object])


def _command(name: str | None = None) -> Callable[[CommandFunction], CommandFunction]:
    """Expose Typer's runtime decorator without erasing command function types."""
    return app.command(name)


def _emit(payload: dict[str, JsonValue], human: str, *, json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        typer.echo(human)


def _error_exit_code(code: ErrorCode) -> ExitCode:
    if code in {ErrorCode.INVALID_INPUT, ErrorCode.OUTPUT_EXISTS}:
        return ExitCode.INPUT_ERROR
    if code in {ErrorCode.ENGINE_UNAVAILABLE, ErrorCode.UNSUPPORTED_ANNOTATION_MODE}:
        return ExitCode.ENGINE_UNAVAILABLE
    if code is ErrorCode.PDF_VALIDATION_FAILED:
        return ExitCode.VALIDATION_FAILED
    return ExitCode.CONVERSION_FAILED


def _conversion_exit_code(result: ConversionResult) -> ExitCode:
    if result.success:
        return ExitCode.SUCCESS
    if result.error is None:
        return ExitCode.CONVERSION_FAILED
    return _error_exit_code(result.error.code)


def _failure_payload(command: str, error: ConversionError) -> dict[str, JsonValue]:
    return {"command": command, "success": False, "error": error.to_dict()}


def _render_conversion(result: ConversionResult) -> str:
    if result.success:
        artifact = result.artifacts[0]
        engine = result.selected_engine.value if result.selected_engine else "unknown"
        return f"Converted with {engine}: {artifact.path}"
    message = result.error.message if result.error else "conversion failed"
    return f"Conversion failed: {message}"


def _render_probe(probe: EngineProbeResult) -> str:
    state = "available" if probe.available else "unavailable"
    details = probe.version or probe.reason
    return f"{probe.engine.value}: {state}" + (f" ({details})" if details else "")


def _make_options(
    *,
    output_path: Path | None,
    overwrite: bool,
    timeout_seconds: float,
    deployment_mode: DeploymentMode,
    engine: EngineName | None,
    revision_mode: RevisionMode,
    comment_mode: CommentMode,
    image_dpi: int = 144,
    image_format: PageImageFormat = PageImageFormat.PNG,
    image_quality: int = 90,
    image_pages: tuple[int, ...] | None = None,
    image_background: str = "#ffffff",
    page_orientation: PageOrientation = PageOrientation.PORTRAIT,
) -> ConversionOptions:
    return ConversionOptions(
        output_path=output_path,
        overwrite=overwrite,
        timeout_seconds=timeout_seconds,
        deployment_mode=deployment_mode,
        engine=engine,
        revision_mode=revision_mode,
        comment_mode=comment_mode,
        image_dpi=image_dpi,
        image_format=image_format,
        image_quality=image_quality,
        image_pages=image_pages,
        image_background=image_background,
        page_orientation=page_orientation,
    )


@_command()
def doctor(
    json_output: Annotated[
        bool, typer.Option("--json", help="Emit machine-readable JSON.")
    ] = False,
) -> None:
    """Diagnose the runtime environment and configured conversion engines."""
    environment = detect_environment()
    probes = DocumentConversionService().probe_engines()
    healthy = any(probe.available for probe in probes)
    payload: dict[str, JsonValue] = {
        "command": "doctor",
        "healthy": healthy,
        "environment": {
            "platform": environment.platform,
            "interactive": environment.interactive,
        },
        "engines": [probe.to_dict() for probe in probes],
    }
    lines = [
        f"Platform: {environment.platform}",
        f"Interactive session: {'yes' if environment.interactive else 'no'}",
        *(_render_probe(probe) for probe in probes),
    ]
    _emit(payload, "\n".join(lines), json_output=json_output)
    if not healthy:
        raise typer.Exit(ExitCode.ENGINE_UNAVAILABLE)


@_command()
def engines(
    json_output: Annotated[
        bool, typer.Option("--json", help="Emit machine-readable JSON.")
    ] = False,
) -> None:
    """List configured conversion engines and their capabilities."""
    probes = DocumentConversionService().probe_engines()
    payload: dict[str, JsonValue] = {
        "command": "engines",
        "engines": [probe.to_dict() for probe in probes],
    }
    _emit(payload, "\n".join(_render_probe(probe) for probe in probes), json_output=json_output)


@_command()
def template(
    output: Annotated[Path, typer.Argument(help="HTML template destination.")],
    orientation: Annotated[
        PageOrientation, typer.Option("--orientation", help="A4 page orientation.")
    ] = PageOrientation.PORTRAIT,
    overwrite: Annotated[bool, typer.Option(help="Replace an existing template.")] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Emit machine-readable JSON.")
    ] = False,
) -> None:
    """Create an editable blank A4 HTML document template."""
    try:
        write_blank_html_template(output, orientation=orientation, overwrite=overwrite)
    except (ConversionError, OSError, ValueError) as error:
        if isinstance(error, ConversionError):
            message = error.message
            code = _error_exit_code(error.code)
            payload = _failure_payload("template", error)
        else:
            message = str(error)
            code = ExitCode.INPUT_ERROR
            payload = {"command": "template", "success": False, "error": message}
        _emit(payload, f"Template failed: {message}", json_output=json_output)
        raise typer.Exit(code) from error
    payload = {
        "command": "template",
        "success": True,
        "path": str(output),
        "orientation": orientation.value,
    }
    _emit(payload, f"Created HTML template: {output}", json_output=json_output)


@_command()
def convert(
    source: Annotated[Path, typer.Argument(help="Source DOCX, PDF, HTML, or Markdown file.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Artifact destination.")
    ] = None,
    artifact_types: Annotated[
        list[ArtifactType] | None,
        typer.Option("--to", help="Artifact target; repeat for multiple targets."),
    ] = None,
    engine: Annotated[
        EngineName | None, typer.Option(help="Require one conversion engine.")
    ] = None,
    deployment_mode: Annotated[
        DeploymentMode, typer.Option("--mode", help="Engine selection policy.")
    ] = DeploymentMode.DESKTOP,
    revision_mode: Annotated[
        RevisionMode, typer.Option("--revisions", help="Tracked-revision rendering mode.")
    ] = RevisionMode.FINAL,
    comment_mode: Annotated[
        CommentMode, typer.Option("--comments", help="Comment rendering mode.")
    ] = CommentMode.OMIT,
    timeout_seconds: Annotated[
        float, typer.Option("--timeout", min=0.001, help="Conversion timeout in seconds.")
    ] = 120.0,
    overwrite: Annotated[bool, typer.Option(help="Replace an existing output safely.")] = False,
    image_dpi: Annotated[int, typer.Option("--dpi", min=1, max=600)] = 144,
    image_format: Annotated[PageImageFormat, typer.Option("--image-format")] = (
        PageImageFormat.PNG
    ),
    image_quality: Annotated[int, typer.Option("--quality", min=1, max=100)] = 90,
    image_pages: Annotated[
        list[int] | None, typer.Option("--page", min=1, help="One-based page; repeatable.")
    ] = None,
    image_background: Annotated[str, typer.Option("--background")] = "#ffffff",
    page_orientation: Annotated[
        PageOrientation, typer.Option("--orientation", help="A4 page orientation.")
    ] = PageOrientation.PORTRAIT,
    gotenberg_url: Annotated[
        str | None, typer.Option("--gotenberg-url", help="Optional Gotenberg base URL.")
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Emit machine-readable JSON.")
    ] = False,
) -> None:
    """Convert one document."""
    try:
        options = _make_options(
            output_path=output,
            overwrite=overwrite,
            timeout_seconds=timeout_seconds,
            deployment_mode=deployment_mode,
            engine=engine,
            revision_mode=revision_mode,
            comment_mode=comment_mode,
            image_dpi=image_dpi,
            image_format=image_format,
            image_quality=image_quality,
            image_pages=tuple(image_pages) if image_pages else None,
            image_background=image_background,
            page_orientation=page_orientation,
        )
        artifacts = tuple(artifact_types) if artifact_types else None
        request = ConversionRequest.from_source(source, artifacts=artifacts, options=options)
    except ConversionError as error:
        _emit(
            _failure_payload("convert", error),
            f"Input error: {error.message}",
            json_output=json_output,
        )
        raise typer.Exit(_error_exit_code(error.code)) from error

    service = (
        DocumentConversionService()
        if gotenberg_url is None
        else DocumentConversionService(gotenberg_url=gotenberg_url)
    )
    result = service.convert(request)
    payload: dict[str, JsonValue] = {
        "command": "convert",
        "success": result.success,
        "result": result.to_dict(),
    }
    _emit(payload, _render_conversion(result), json_output=json_output)
    exit_code = _conversion_exit_code(result)
    if exit_code:
        raise typer.Exit(exit_code)


@_command()
def compare(
    left: Annotated[Path, typer.Argument(help="Left PDF file.")],
    right: Annotated[Path, typer.Argument(help="Right PDF file.")],
    dpi: Annotated[int, typer.Option(min=1, max=600)] = 144,
    diff_directory: Annotated[
        Path | None, typer.Option("--diff-dir", help="Directory for differing-page PNGs.")
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Emit machine-readable JSON.")
    ] = False,
) -> None:
    """Compare two PDFs by structure, fonts, size, and rendered pixels."""
    service = PdfComparisonService(
        PdfRasterizer(PdfiumPageRenderer()),
        PillowImageDiffer(),
    )
    try:
        report = service.compare(
            left,
            right,
            dpi=dpi,
            diff_directory=diff_directory,
        )
    except ConversionError as error:
        _emit(
            _failure_payload("compare", error),
            f"Comparison failed: {error.message}",
            json_output=json_output,
        )
        raise typer.Exit(_error_exit_code(error.code)) from error
    payload: dict[str, JsonValue] = {
        "command": "compare",
        "success": True,
        "report": report.to_dict(),
    }
    human = (
        "PDFs are visually equal."
        if report.equal
        else "PDFs differ; inspect the machine-readable report or diff images."
    )
    _emit(payload, human, json_output=json_output)


@_command()
def batch(
    sources: Annotated[list[Path], typer.Argument(help="One or more source DOCX files.")],
    output_directory: Annotated[
        Path | None, typer.Option("--output-dir", help="Directory for generated PDFs.")
    ] = None,
    engine: Annotated[
        EngineName | None, typer.Option(help="Require one conversion engine.")
    ] = None,
    deployment_mode: Annotated[
        DeploymentMode, typer.Option("--mode", help="Engine selection policy.")
    ] = DeploymentMode.DESKTOP,
    revision_mode: Annotated[
        RevisionMode, typer.Option("--revisions", help="Tracked-revision rendering mode.")
    ] = RevisionMode.FINAL,
    comment_mode: Annotated[
        CommentMode, typer.Option("--comments", help="Comment rendering mode.")
    ] = CommentMode.OMIT,
    timeout_seconds: Annotated[
        float, typer.Option("--timeout", min=0.001, help="Per-file timeout in seconds.")
    ] = 120.0,
    overwrite: Annotated[bool, typer.Option(help="Replace existing outputs safely.")] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Emit machine-readable JSON.")
    ] = False,
) -> None:
    """Convert multiple documents sequentially with isolated item failures."""
    requests: list[ConversionRequest] = []
    try:
        for source in sources:
            output = None
            if output_directory is not None:
                output = output_directory / source.with_suffix(".pdf").name
            options = _make_options(
                output_path=output,
                overwrite=overwrite,
                timeout_seconds=timeout_seconds,
                deployment_mode=deployment_mode,
                engine=engine,
                revision_mode=revision_mode,
                comment_mode=comment_mode,
            )
            requests.append(ConversionRequest.from_source(source, options=options))
    except ConversionError as error:
        _emit(
            _failure_payload("batch", error),
            f"Input error: {error.message}",
            json_output=json_output,
        )
        raise typer.Exit(_error_exit_code(error.code)) from error

    results = DocumentConversionService().convert_batch(requests)
    success = all(result.success for result in results)
    payload: dict[str, JsonValue] = {
        "command": "batch",
        "success": success,
        "results": [result.to_dict() for result in results],
    }
    succeeded = sum(result.success for result in results)
    human = f"Converted {succeeded}/{len(results)} documents."
    _emit(payload, human, json_output=json_output)
    if not success:
        codes = [_conversion_exit_code(result) for result in results if not result.success]
        raise typer.Exit(max(codes, default=ExitCode.CONVERSION_FAILED))


@_command("version")
def version_command(
    json_output: Annotated[
        bool, typer.Option("--json", help="Emit machine-readable JSON.")
    ] = False,
) -> None:
    """Show the installed package version."""
    package_version = version("gordon-doc-converter")
    payload: dict[str, JsonValue] = {
        "command": "version",
        "version": package_version,
    }
    _emit(payload, f"gordon-doc {package_version}", json_output=json_output)


def main() -> None:
    """Run the command-line application."""
    app()


if __name__ == "__main__":
    main()
