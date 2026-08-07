"""Unit tests for the isolated LibreOffice engine adapter."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest
from pypdf import PdfWriter

import gordon_doc_converter.engines.libreoffice as libreoffice_module
from gordon_doc_converter.engines.libreoffice import LibreOfficeEngine
from gordon_doc_converter.exceptions import (
    ConversionTimeoutError,
    EngineFailedError,
    EngineUnavailableError,
    OutputExistsError,
    PdfNotCreatedError,
    PdfValidationError,
    UnsupportedAnnotationModeError,
)
from gordon_doc_converter.models import CommentMode, EngineName, RevisionMode


def _write_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as stream:
        writer.write(stream)


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "臺灣 測試文件.docx"
    source.write_bytes(b"generated public fixture")
    return source


def _output_directory(arguments: Sequence[str]) -> Path:
    return Path(arguments[arguments.index("--outdir") + 1])


def test_find_executable_checks_standard_windows_installation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    program_files = tmp_path / "Program Files"
    executable = program_files / "LibreOffice" / "program" / "soffice.com"
    executable.parent.mkdir(parents=True)
    executable.touch()
    monkeypatch.setattr(libreoffice_module.sys, "platform", "win32")
    monkeypatch.setattr(libreoffice_module.shutil, "which", lambda name: None)
    monkeypatch.setenv("PROGRAMFILES", str(program_files))
    monkeypatch.delenv("PROGRAMFILES(X86)", raising=False)

    assert libreoffice_module._find_executable() == executable.resolve()


def test_process_timeout_terminates_tree_and_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeout_type = libreoffice_module.subprocess.TimeoutExpired

    class FakeProcess:
        returncode = 0
        calls = 0

        def communicate(self, timeout: float) -> tuple[str, str]:
            self.calls += 1
            if self.calls == 1:
                raise timeout_type(("soffice",), timeout)
            return ("partial output", "")

    process = FakeProcess()
    terminated: list[object] = []
    monkeypatch.setattr(libreoffice_module.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(
        libreoffice_module,
        "_terminate_process_tree",
        lambda running_process: terminated.append(running_process),
    )

    with pytest.raises(libreoffice_module._ProcessTimedOut) as raised:
        libreoffice_module._run_process(("soffice", "--version"), 1)

    assert isinstance(raised.value.__cause__, timeout_type)
    assert terminated == [process]
    assert process.calls == 2


def test_probe_reports_version_path_and_conservative_capabilities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "soffice"
    calls: list[tuple[tuple[str, ...], float]] = []

    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> object:
        calls.append((tuple(arguments), timeout_seconds))
        return libreoffice_module._ProcessResult(0, "LibreOffice 24.8.1.2\n", "")

    monkeypatch.setattr(libreoffice_module, "_run_process", fake_run)

    result = LibreOfficeEngine(executable, probe_timeout_seconds=3).probe()

    assert result.available is True
    assert result.engine is EngineName.LIBREOFFICE
    assert result.version == "LibreOffice 24.8.1.2"
    assert result.executable == executable.resolve()
    assert result.revision_modes == (RevisionMode.FINAL,)
    assert result.comment_modes == (CommentMode.OMIT,)
    assert calls == [((str(executable.resolve()), "--headless", "--version"), 3)]


def test_probe_reports_missing_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(libreoffice_module, "_find_executable", lambda: None)

    result = LibreOfficeEngine().probe()

    assert result.available is False
    assert result.reason == "LibreOffice executable was not found"
    assert result.executable is None


@pytest.mark.parametrize(
    ("process_result", "expected_reason"),
    [
        (
            libreoffice_module._ProcessResult(7, "", "failure"),
            "LibreOffice version probe exited with code 7",
        ),
        (libreoffice_module._ProcessTimedOut(), "LibreOffice version probe timed out"),
    ],
)
def test_probe_reports_process_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    process_result: object,
    expected_reason: str,
) -> None:
    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> object:
        del arguments, timeout_seconds
        if isinstance(process_result, BaseException):
            raise process_result
        return process_result

    monkeypatch.setattr(libreoffice_module, "_run_process", fake_run)

    result = LibreOfficeEngine(tmp_path / "soffice").probe()

    assert result.available is False
    assert result.reason == expected_reason


def test_conversion_uses_isolated_profile_validates_and_moves_pdf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source(tmp_path)
    output = tmp_path / "nested output" / "自訂名稱.pdf"
    executable = tmp_path / "Libre Office" / "soffice"
    temporary_root: Path | None = None
    captured_calls: list[tuple[str, ...]] = []

    def fake_run(
        arguments: Sequence[str],
        timeout_seconds: float,
    ) -> libreoffice_module._ProcessResult:
        nonlocal temporary_root
        assert timeout_seconds == 9
        captured_calls.append(tuple(arguments))
        output_directory = _output_directory(arguments)
        temporary_root = output_directory.parent
        _write_pdf(output_directory / f"{source.stem}.pdf")
        return libreoffice_module._ProcessResult(0, "converted", "")

    monkeypatch.setattr(libreoffice_module, "_run_process", fake_run)

    result = LibreOfficeEngine(executable).convert(
        source,
        output,
        timeout_seconds=9,
        revision_mode=RevisionMode.FINAL,
        comment_mode=CommentMode.OMIT,
    )

    assert result.engine is EngineName.LIBREOFFICE
    assert result.output_path == output
    assert result.duration_seconds >= 0
    assert output.is_file()
    assert len(captured_calls) == 1
    captured_arguments = captured_calls[0]
    assert captured_arguments[0] == str(executable.resolve())
    assert captured_arguments[-1] == str(source.resolve())
    assert any(
        argument.startswith("-env:UserInstallation=file:") for argument in captured_arguments
    )
    assert temporary_root is not None
    assert not temporary_root.exists()


def test_nonzero_conversion_maps_error_and_cleans_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source(tmp_path)
    temporary_root: Path | None = None

    def fake_run(
        arguments: Sequence[str],
        timeout_seconds: float,
    ) -> libreoffice_module._ProcessResult:
        nonlocal temporary_root
        del timeout_seconds
        temporary_root = _output_directory(arguments).parent
        return libreoffice_module._ProcessResult(5, "", "private diagnostic")

    monkeypatch.setattr(libreoffice_module, "_run_process", fake_run)

    with pytest.raises(EngineFailedError, match="code 5") as raised:
        LibreOfficeEngine(tmp_path / "soffice").convert(
            source,
            tmp_path / "output.pdf",
            timeout_seconds=5,
            revision_mode=RevisionMode.FINAL,
            comment_mode=CommentMode.OMIT,
        )

    assert raised.value.engine == "libreoffice"
    assert "private diagnostic" not in raised.value.message
    assert temporary_root is not None
    assert not temporary_root.exists()


def test_missing_generated_pdf_maps_to_not_created(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source(tmp_path)
    monkeypatch.setattr(
        libreoffice_module,
        "_run_process",
        lambda arguments, timeout_seconds: libreoffice_module._ProcessResult(0, "", ""),
    )

    with pytest.raises(PdfNotCreatedError):
        LibreOfficeEngine(tmp_path / "soffice").convert(
            source,
            tmp_path / "output.pdf",
            timeout_seconds=5,
            revision_mode=RevisionMode.FINAL,
            comment_mode=CommentMode.OMIT,
        )


def test_invalid_generated_pdf_maps_to_validation_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source(tmp_path)

    def fake_run(
        arguments: Sequence[str],
        timeout_seconds: float,
    ) -> libreoffice_module._ProcessResult:
        del timeout_seconds
        (_output_directory(arguments) / f"{source.stem}.pdf").write_bytes(b"invalid")
        return libreoffice_module._ProcessResult(0, "", "")

    monkeypatch.setattr(libreoffice_module, "_run_process", fake_run)

    with pytest.raises(PdfValidationError):
        LibreOfficeEngine(tmp_path / "soffice").convert(
            source,
            tmp_path / "output.pdf",
            timeout_seconds=5,
            revision_mode=RevisionMode.FINAL,
            comment_mode=CommentMode.OMIT,
        )


def test_timeout_maps_error_and_cleans_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source(tmp_path)
    temporary_root: Path | None = None

    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> object:
        nonlocal temporary_root
        del timeout_seconds
        temporary_root = _output_directory(arguments).parent
        raise libreoffice_module._ProcessTimedOut

    monkeypatch.setattr(libreoffice_module, "_run_process", fake_run)

    with pytest.raises(ConversionTimeoutError) as raised:
        LibreOfficeEngine(tmp_path / "soffice").convert(
            source,
            tmp_path / "output.pdf",
            timeout_seconds=5,
            revision_mode=RevisionMode.FINAL,
            comment_mode=CommentMode.OMIT,
        )

    assert isinstance(raised.value.__cause__, libreoffice_module._ProcessTimedOut)
    assert temporary_root is not None
    assert not temporary_root.exists()


def test_conversion_rejects_unsupported_modes_before_starting_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source(tmp_path)

    def unexpected_run(arguments: Sequence[str], timeout_seconds: float) -> object:
        raise AssertionError((arguments, timeout_seconds))

    monkeypatch.setattr(libreoffice_module, "_run_process", unexpected_run)

    with pytest.raises(UnsupportedAnnotationModeError):
        LibreOfficeEngine(tmp_path / "soffice").convert(
            source,
            tmp_path / "output.pdf",
            timeout_seconds=5,
            revision_mode=RevisionMode.MARKUP,
            comment_mode=CommentMode.OMIT,
        )


def test_conversion_rejects_existing_output(tmp_path: Path) -> None:
    source = _source(tmp_path)
    output = tmp_path / "output.pdf"
    output.write_bytes(b"preserve me")

    with pytest.raises(OutputExistsError):
        LibreOfficeEngine(tmp_path / "soffice").convert(
            source,
            output,
            timeout_seconds=5,
            revision_mode=RevisionMode.FINAL,
            comment_mode=CommentMode.OMIT,
        )

    assert output.read_bytes() == b"preserve me"


def test_conversion_reports_unavailable_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source(tmp_path)
    monkeypatch.setattr(libreoffice_module, "_find_executable", lambda: None)

    with pytest.raises(EngineUnavailableError):
        LibreOfficeEngine().convert(
            source,
            tmp_path / "output.pdf",
            timeout_seconds=5,
            revision_mode=RevisionMode.FINAL,
            comment_mode=CommentMode.OMIT,
        )
