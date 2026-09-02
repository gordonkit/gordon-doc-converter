"""Unit tests for the direct wkhtmltopdf adapter."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from pathlib import Path

import pytest

import gordon_doc_converter.engines.wkhtmltopdf as wkhtmltopdf_module
from gordon_doc_converter.engines.wkhtmltopdf import WkhtmltopdfConverter
from gordon_doc_converter.exceptions import (
    ConversionTimeoutError,
    EngineFailedError,
    EngineUnavailableError,
)
from gordon_doc_converter.models import ConversionOptions, PageOrientation
from gordon_doc_converter.process.runner import ProcessResult, ProcessTimeoutError


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "中介文件.html"
    source.write_text("<!doctype html><html><body><p>內文</p></body></html>", encoding="utf-8")
    return source


def _converter(tmp_path: Path) -> WkhtmltopdfConverter:
    return WkhtmltopdfConverter(str(tmp_path / "wkhtmltopdf"))


def test_missing_executable_is_reported_as_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)

    with pytest.raises(EngineUnavailableError):
        WkhtmltopdfConverter().convert(
            _source(tmp_path),
            tmp_path / "out.pdf",
            options=ConversionOptions(),
        )


def test_landscape_pages_carry_a4_setup_and_the_stylesheet_margins(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source(tmp_path)
    output = tmp_path / "out.pdf"
    calls: list[tuple[str, ...]] = []

    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        del timeout_seconds
        calls.append(tuple(arguments))
        output.write_bytes(b"%PDF-1.7 generated")
        return ProcessResult(0, "", "")

    monkeypatch.setattr(wkhtmltopdf_module, "run_process", fake_run)

    _converter(tmp_path).convert(
        source,
        output,
        options=ConversionOptions(page_orientation=PageOrientation.LANDSCAPE),
    )

    arguments = calls[0]
    assert arguments[arguments.index("--page-size") + 1] == "A4"
    assert arguments[arguments.index("--orientation") + 1] == "Landscape"
    assert arguments[arguments.index("--margin-top") + 1] == "20mm"
    assert arguments[-2:] == (str(source), str(output))
    # The document is read as-is, keeping the stylesheet it carries.
    assert "--print-media-type" in arguments


def test_an_older_build_retries_without_the_local_file_access_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "out.pdf"
    attempts: list[tuple[str, ...]] = []

    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        del timeout_seconds
        items = tuple(arguments)
        attempts.append(items)
        if "--enable-local-file-access" in items:
            return ProcessResult(1, "", "Unknown long argument --enable-local-file-access")
        output.write_bytes(b"%PDF-1.7 generated")
        return ProcessResult(0, "", "")

    monkeypatch.setattr(wkhtmltopdf_module, "run_process", fake_run)

    _converter(tmp_path).convert(
        _source(tmp_path),
        output,
        options=ConversionOptions(),
    )

    assert len(attempts) == 2
    assert "--enable-local-file-access" not in attempts[1]


def test_failed_run_reports_the_last_stderr_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        del arguments, timeout_seconds
        return ProcessResult(1, "", "loading pages\nExit with code 1 due to network error")

    monkeypatch.setattr(wkhtmltopdf_module, "run_process", fake_run)

    with pytest.raises(EngineFailedError, match="network error"):
        _converter(tmp_path).convert(
            _source(tmp_path),
            tmp_path / "out.pdf",
            options=ConversionOptions(),
        )


def test_a_missing_output_is_reported_even_when_the_run_succeeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        del arguments, timeout_seconds
        return ProcessResult(0, "", "")

    monkeypatch.setattr(wkhtmltopdf_module, "run_process", fake_run)

    with pytest.raises(EngineFailedError, match="did not create"):
        _converter(tmp_path).convert(
            _source(tmp_path),
            tmp_path / "out.pdf",
            options=ConversionOptions(),
        )


def test_timed_out_run_is_reported_as_a_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        del arguments, timeout_seconds
        raise ProcessTimeoutError

    monkeypatch.setattr(wkhtmltopdf_module, "run_process", fake_run)

    with pytest.raises(ConversionTimeoutError):
        _converter(tmp_path).convert(
            _source(tmp_path),
            tmp_path / "out.pdf",
            options=ConversionOptions(),
        )
