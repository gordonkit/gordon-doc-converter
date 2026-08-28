"""CLI help, JSON contract, and stable exit-code tests."""

from __future__ import annotations

import importlib
import json
import re
from collections.abc import Iterable, Sequence
from pathlib import Path

import pytest
from pypdf import PdfWriter
from typer.testing import CliRunner

from gordon_doc_converter.cli import app
from gordon_doc_converter.environment import EnvironmentInfo
from gordon_doc_converter.exceptions import ErrorCode
from gordon_doc_converter.models import (
    ArtifactResult,
    ArtifactStatus,
    ArtifactType,
    ConversionFailure,
    ConversionRequest,
    ConversionResult,
    EngineName,
    EngineProbeResult,
    SourceFormat,
)
from gordon_doc_converter.progress import ProgressCallback, ProgressEvent, ProgressState

cli_module = importlib.import_module("gordon_doc_converter.cli.app")
runner = CliRunner()
ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def _plain_text(value: str) -> str:
    return ANSI_ESCAPE.sub("", value)


def _write_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as stream:
        writer.write(stream)


def _probe(name: EngineName, *, available: bool) -> EngineProbeResult:
    return EngineProbeResult(
        engine=name,
        available=available,
        version="1.0" if available else None,
        reason=None if available else "not installed",
    )


def _result(
    *,
    success: bool,
    error_code: ErrorCode | None = None,
    output_path: Path | None = None,
) -> ConversionResult:
    failure = None
    if error_code is not None:
        failure = ConversionFailure(code=error_code, message="safe failure")
    return ConversionResult(
        success=success,
        source_format=SourceFormat.DOCX,
        artifacts=(
            ArtifactResult(
                artifact_type=ArtifactType.PDF,
                status=ArtifactStatus.SUCCESS if success else ArtifactStatus.FAILED,
                path=output_path,
                error=failure,
            ),
        ),
        selected_engine=EngineName.LIBREOFFICE if success else None,
        attempted_engines=(EngineName.LIBREOFFICE,),
        error=failure,
    )


class StubService:
    """Record CLI-created requests while returning configured service results."""

    probes: tuple[EngineProbeResult, ...] = ()
    conversion_results: tuple[ConversionResult, ...] = ()
    requests: list[ConversionRequest] = []

    def probe_engines(
        self,
        names: Sequence[EngineName] = tuple(EngineName),
    ) -> tuple[EngineProbeResult, ...]:
        del names
        return self.probes

    def convert(
        self,
        request: ConversionRequest,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> ConversionResult:
        self.requests.append(request)
        if progress_callback is not None:
            progress_callback(
                ProgressEvent("rendering", ProgressState.RUNNING, "Rendering document")
            )
        return self.conversion_results[0]

    def convert_batch(
        self,
        requests: Iterable[ConversionRequest],
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> tuple[ConversionResult, ...]:
        queued = tuple(requests)
        self.requests.extend(queued)
        if progress_callback is not None:
            progress_callback(
                ProgressEvent(
                    "batch",
                    ProgressState.COMPLETED,
                    "Finished batch item",
                    completed=len(queued),
                    total=len(queued),
                )
            )
        return self.conversion_results


@pytest.fixture(autouse=True)
def _reset_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    StubService.probes = ()
    StubService.conversion_results = ()
    StubService.requests = []
    monkeypatch.setattr(cli_module, "DocumentConversionService", StubService)


@pytest.mark.parametrize(
    "command", ["doctor", "engines", "template", "convert", "compare", "batch", "version"]
)
def test_every_command_has_help(command: str) -> None:
    result = runner.invoke(app, [command, "--help"])

    assert result.exit_code == 0
    assert "--help" in _plain_text(result.stdout)


def test_version_json_contract() -> None:
    result = runner.invoke(app, ["version", "--json"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"command": "version", "version": "0.7.0"}


def test_compare_emits_machine_readable_raster_report(tmp_path: Path) -> None:
    left = tmp_path / "left.pdf"
    right = tmp_path / "right.pdf"
    _write_pdf(left)
    _write_pdf(right)

    result = runner.invoke(app, ["compare", str(left), str(right), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "compare"
    assert payload["report"]["equal"] is True
    assert payload["report"]["pages"][0]["page_number"] == 1


def test_engines_json_contract() -> None:
    StubService.probes = (_probe(EngineName.LIBREOFFICE, available=True),)

    result = runner.invoke(app, ["engines", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "engines"
    assert payload["engines"][0]["engine"] == "libreoffice"
    assert payload["engines"][0]["available"] is True


def test_engines_human_output() -> None:
    StubService.probes = (_probe(EngineName.LIBREOFFICE, available=False),)

    result = runner.invoke(app, ["engines"])

    assert result.exit_code == 0
    assert result.stdout == "libreoffice: unavailable (not installed)\n"


def test_doctor_json_contract_and_healthy_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    StubService.probes = (_probe(EngineName.LIBREOFFICE, available=True),)
    monkeypatch.setattr(cli_module, "detect_environment", lambda: EnvironmentInfo("linux", False))

    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["healthy"] is True
    assert payload["environment"] == {"platform": "linux", "interactive": False}


def test_doctor_returns_engine_exit_when_every_engine_is_unavailable() -> None:
    StubService.probes = (_probe(EngineName.LIBREOFFICE, available=False),)

    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 3
    assert json.loads(result.stdout)["healthy"] is False


def test_convert_builds_request_and_emits_json(tmp_path: Path) -> None:
    source = tmp_path / "繁中 文件.docx"
    output = tmp_path / "輸出 文件.pdf"
    StubService.conversion_results = (_result(success=True, output_path=output),)

    result = runner.invoke(
        app,
        [
            "convert",
            str(source),
            "--output",
            str(output),
            "--engine",
            "libreoffice",
            "--timeout",
            "9",
            "--metadata",
            "layout",
            "--overwrite",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "convert"
    assert payload["success"] is True
    assert payload["result"]["selected_engine"] == "libreoffice"
    request = StubService.requests[0]
    assert request.source_path == source
    assert request.options.output_path == output
    assert request.options.engine is EngineName.LIBREOFFICE
    assert request.options.timeout_seconds == 9
    assert request.options.metadata_detail.value == "layout"
    assert request.options.overwrite is True


def test_convert_without_rendering_engine_emits_clear_human_output(tmp_path: Path) -> None:
    source = tmp_path / "input.docx"
    output = tmp_path / "input.html"
    StubService.conversion_results = (
        ConversionResult(
            success=True,
            source_format=SourceFormat.DOCX,
            artifacts=(
                ArtifactResult(
                    artifact_type=ArtifactType.HTML,
                    status=ArtifactStatus.SUCCESS,
                    path=output,
                ),
            ),
        ),
    )

    result = runner.invoke(app, ["convert", str(source), "--to", "html"])

    assert result.exit_code == 0
    assert result.stdout == f"Converted without a rendering engine: {output}\n"


def test_convert_progress_is_emitted_to_stderr_without_polluting_json(tmp_path: Path) -> None:
    output = tmp_path / "output.json"
    StubService.conversion_results = (_result(success=True, output_path=output),)

    result = runner.invoke(
        app,
        [
            "convert",
            str(tmp_path / "input.docx"),
            "--to",
            "json",
            "--progress",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["success"] is True
    assert "[running] Rendering document" in result.stderr


def test_convert_invalid_extension_returns_input_exit_and_json(tmp_path: Path) -> None:
    result = runner.invoke(app, ["convert", str(tmp_path / "input.txt"), "--json"])

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["command"] == "convert"
    assert payload["success"] is False
    assert payload["error"]["code"] == "INVALID_INPUT"


@pytest.mark.parametrize(
    ("error_code", "exit_code"),
    [
        (ErrorCode.OUTPUT_EXISTS, 2),
        (ErrorCode.ENGINE_UNAVAILABLE, 3),
        (ErrorCode.UNSUPPORTED_ANNOTATION_MODE, 3),
        (ErrorCode.ENGINE_FAILED, 4),
        (ErrorCode.CONVERSION_TIMEOUT, 4),
        (ErrorCode.PDF_NOT_CREATED, 4),
        (ErrorCode.PDF_VALIDATION_FAILED, 5),
    ],
)
def test_convert_maps_stable_failure_exit_codes(
    tmp_path: Path, error_code: ErrorCode, exit_code: int
) -> None:
    StubService.conversion_results = (_result(success=False, error_code=error_code),)

    result = runner.invoke(app, ["convert", str(tmp_path / "input.docx"), "--json"])

    assert result.exit_code == exit_code
    assert json.loads(result.stdout)["result"]["error"]["code"] == error_code.value


def test_batch_preserves_results_and_returns_most_specific_exit(tmp_path: Path) -> None:
    first = tmp_path / "一.docx"
    second = tmp_path / "二.docx"
    output_directory = tmp_path / "PDF"
    StubService.conversion_results = (
        _result(success=True, output_path=output_directory / "一.pdf"),
        _result(success=False, error_code=ErrorCode.PDF_VALIDATION_FAILED),
    )

    result = runner.invoke(
        app,
        [
            "batch",
            str(first),
            str(second),
            "--output-dir",
            str(output_directory),
            "--json",
        ],
    )

    assert result.exit_code == 5
    payload = json.loads(result.stdout)
    assert payload["command"] == "batch"
    assert payload["success"] is False
    assert len(payload["results"]) == 2
    assert tuple(request.options.output_path for request in StubService.requests) == (
        output_directory / "一.pdf",
        output_directory / "二.pdf",
    )


def test_batch_progress_reports_completed_count_on_stderr(tmp_path: Path) -> None:
    StubService.conversion_results = (
        _result(success=True, output_path=tmp_path / "一.pdf"),
        _result(success=True, output_path=tmp_path / "二.pdf"),
    )

    result = runner.invoke(
        app,
        [
            "batch",
            str(tmp_path / "一.docx"),
            str(tmp_path / "二.docx"),
            "--progress",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["success"] is True
    assert "2/2" in result.stderr


def test_convert_json_lines_flag_reaches_conversion_options(tmp_path: Path) -> None:
    output = tmp_path / "input.jsonl"
    StubService.conversion_results = (
        ConversionResult(
            success=True,
            source_format=SourceFormat.HTML,
            artifacts=(
                ArtifactResult(
                    artifact_type=ArtifactType.JSON,
                    status=ArtifactStatus.SUCCESS,
                    path=output,
                ),
            ),
        ),
    )
    StubService.requests = []

    result = runner.invoke(
        app,
        ["convert", str(tmp_path / "input.html"), "--to", "json", "--json-lines"],
    )

    assert result.exit_code == 0
    assert StubService.requests[-1].options.json_lines is True


def test_convert_defaults_to_nested_json_without_the_flag(tmp_path: Path) -> None:
    StubService.conversion_results = (_result(success=True, output_path=tmp_path / "input.json"),)
    StubService.requests = []

    result = runner.invoke(app, ["convert", str(tmp_path / "input.html"), "--to", "json"])

    assert result.exit_code == 0
    assert StubService.requests[-1].options.json_lines is False
