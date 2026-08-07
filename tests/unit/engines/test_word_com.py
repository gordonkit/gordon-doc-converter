"""Unit tests for the bounded Microsoft Word COM adapter."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest
from pypdf import PdfWriter

import gordon_doc_converter.engines.word_com as word_module
from gordon_doc_converter.engines.word_com import WordComEngine
from gordon_doc_converter.exceptions import (
    ConversionTimeoutError,
    EngineFailedError,
    EngineUnavailableError,
    OutputExistsError,
    PdfNotCreatedError,
    UnsupportedAnnotationModeError,
)
from gordon_doc_converter.models import CommentMode, EngineName, RevisionMode
from gordon_doc_converter.process.runner import ProcessResult, ProcessTimeoutError


def _write_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as stream:
        writer.write(stream)


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "臺灣 Word 文件.docx"
    source.write_bytes(b"generated public fixture")
    return source


def test_probe_is_unavailable_without_starting_worker_off_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(word_module.sys, "platform", "linux")

    result = WordComEngine().probe()

    assert result.available is False
    assert result.reason == "Microsoft Word COM is available only on Windows"


def test_probe_uses_real_worker_result_and_reports_capabilities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(word_module.sys, "platform", "win32")
    calls: list[tuple[tuple[str, ...], float]] = []

    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        calls.append((tuple(arguments), timeout_seconds))
        return ProcessResult(0, '{"status":"ok","version":"16.0"}', "")

    monkeypatch.setattr(word_module, "run_process", fake_run)
    python = tmp_path / "python.exe"

    result = WordComEngine(python, probe_timeout_seconds=4).probe()

    assert result.available is True
    assert result.version == "16.0"
    assert result.revision_modes == (
        RevisionMode.FINAL,
        RevisionMode.ORIGINAL,
        RevisionMode.MARKUP,
    )
    assert result.comment_modes == (CommentMode.OMIT, CommentMode.MARKUP)
    assert calls == [
        (
            (
                str(python.resolve()),
                "-m",
                "gordon_doc_converter.engines._word_worker",
                "--probe",
            ),
            4,
        )
    ]


@pytest.mark.parametrize(
    ("outcome", "reason"),
    [
        (ProcessResult(2, '{"status":"unavailable"}', ""), "activation failed"),
        (ProcessResult(3, '{"status":"cleanup-failed"}', ""), "activation failed"),
        (ProcessResult(0, "not-json", ""), "activation failed"),
        (ProcessTimeoutError(), "activation timed out"),
    ],
)
def test_probe_maps_worker_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: object,
    reason: str,
) -> None:
    monkeypatch.setattr(word_module.sys, "platform", "win32")

    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        del arguments, timeout_seconds
        if isinstance(outcome, BaseException):
            raise outcome
        assert isinstance(outcome, ProcessResult)
        return outcome

    monkeypatch.setattr(word_module, "run_process", fake_run)

    result = WordComEngine(tmp_path / "python.exe").probe()

    assert result.available is False
    assert result.reason is not None
    assert reason in result.reason


def test_conversion_passes_request_out_of_process_and_publishes_valid_pdf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(word_module.sys, "platform", "win32")
    source = _source(tmp_path)
    output = tmp_path / "nested output" / "Word 結果.pdf"
    workspace: Path | None = None
    commands: list[tuple[str, ...]] = []

    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        nonlocal workspace
        assert timeout_seconds == 8
        commands.append(tuple(arguments))
        request_path = Path(arguments[-1])
        workspace = request_path.parent
        payload = json.loads(request_path.read_text(encoding="utf-8"))
        assert payload["source"] == str(source.resolve())
        assert payload["revision_mode"] == "original"
        assert payload["comment_mode"] == "markup"
        _write_pdf(Path(payload["output"]))
        return ProcessResult(0, '{"status":"ok"}', "")

    monkeypatch.setattr(word_module, "run_process", fake_run)

    result = WordComEngine(tmp_path / "python.exe").convert(
        source,
        output,
        timeout_seconds=8,
        revision_mode=RevisionMode.ORIGINAL,
        comment_mode=CommentMode.MARKUP,
    )

    assert result.engine is EngineName.WORD_COM
    assert result.output_path == output
    assert output.is_file()
    assert len(commands) == 1
    command = commands[0]
    assert str(source) not in command
    assert workspace is not None
    assert not workspace.exists()


@pytest.mark.parametrize(
    ("result", "error_type"),
    [
        (ProcessResult(2, '{"status":"unavailable"}', ""), EngineUnavailableError),
        (ProcessResult(3, '{"status":"failed"}', "private"), EngineFailedError),
        (ProcessResult(0, "not-json", "private"), EngineFailedError),
    ],
)
def test_conversion_maps_worker_failures_without_exposing_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    result: ProcessResult,
    error_type: type[Exception],
) -> None:
    monkeypatch.setattr(word_module.sys, "platform", "win32")
    source = _source(tmp_path)
    monkeypatch.setattr(word_module, "run_process", lambda arguments, timeout: result)

    with pytest.raises(error_type) as raised:
        WordComEngine(tmp_path / "python.exe").convert(
            source,
            tmp_path / "output.pdf",
            timeout_seconds=5,
            revision_mode=RevisionMode.FINAL,
            comment_mode=CommentMode.OMIT,
        )

    assert "private" not in str(raised.value)


def test_conversion_timeout_maps_error_and_cleans_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(word_module.sys, "platform", "win32")
    source = _source(tmp_path)
    workspace: Path | None = None

    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        nonlocal workspace
        del timeout_seconds
        workspace = Path(arguments[-1]).parent
        raise ProcessTimeoutError

    monkeypatch.setattr(word_module, "run_process", fake_run)

    with pytest.raises(ConversionTimeoutError):
        WordComEngine(tmp_path / "python.exe").convert(
            source,
            tmp_path / "output.pdf",
            timeout_seconds=5,
            revision_mode=RevisionMode.FINAL,
            comment_mode=CommentMode.OMIT,
        )

    assert workspace is not None
    assert not workspace.exists()


def test_conversion_requires_actual_pdf_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(word_module.sys, "platform", "win32")
    source = _source(tmp_path)
    monkeypatch.setattr(
        word_module,
        "run_process",
        lambda arguments, timeout: ProcessResult(0, '{"status":"ok"}', ""),
    )

    with pytest.raises(PdfNotCreatedError):
        WordComEngine(tmp_path / "python.exe").convert(
            source,
            tmp_path / "output.pdf",
            timeout_seconds=5,
            revision_mode=RevisionMode.FINAL,
            comment_mode=CommentMode.OMIT,
        )


def test_conversion_rejects_comment_appendix_before_worker_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(word_module.sys, "platform", "win32")
    source = _source(tmp_path)

    with pytest.raises(UnsupportedAnnotationModeError):
        WordComEngine(tmp_path / "python.exe").convert(
            source,
            tmp_path / "output.pdf",
            timeout_seconds=5,
            revision_mode=RevisionMode.FINAL,
            comment_mode=CommentMode.APPENDIX,
        )


def test_conversion_preserves_existing_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(word_module.sys, "platform", "win32")
    source = _source(tmp_path)
    output = tmp_path / "output.pdf"
    output.write_bytes(b"preserve")

    with pytest.raises(OutputExistsError):
        WordComEngine(tmp_path / "python.exe").convert(
            source,
            output,
            timeout_seconds=5,
            revision_mode=RevisionMode.FINAL,
            comment_mode=CommentMode.OMIT,
        )

    assert output.read_bytes() == b"preserve"
