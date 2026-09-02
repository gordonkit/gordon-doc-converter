"""Unit tests for the isolated LibreOffice engine adapter."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from pypdf import PdfWriter

import gordon_doc_converter.engines.libreoffice as libreoffice_module
from gordon_doc_converter.engines.libreoffice import LibreOfficeEngine
from gordon_doc_converter.exceptions import (
    ConversionTimeoutError,
    EngineFailedError,
    EngineUnavailableError,
    InvalidInputError,
    OutputExistsError,
    PdfNotCreatedError,
    PdfValidationError,
    UnsupportedAnnotationModeError,
)
from gordon_doc_converter.models import (
    ArtifactType,
    CommentMode,
    EngineName,
    RevisionMode,
    SourceFormat,
)
from gordon_doc_converter.process.runner import ProcessResult, ProcessTimeoutError


def _write_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as stream:
        writer.write(stream)


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "臺灣 測試文件.docx"
    source.write_bytes(b"generated public fixture")
    return source


def _write_odt(path: Path) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        archive.writestr("META-INF/manifest.xml", "<manifest/>")
        archive.writestr("content.xml", "<content/>")


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


def test_probe_reports_version_path_and_conservative_capabilities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executable = tmp_path / "soffice"
    calls: list[tuple[tuple[str, ...], float]] = []

    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> object:
        calls.append((tuple(arguments), timeout_seconds))
        return ProcessResult(0, "LibreOffice 24.8.1.2\n", "")

    monkeypatch.setattr(libreoffice_module, "run_process", fake_run)

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
            ProcessResult(7, "", "failure"),
            "LibreOffice version probe exited with code 7",
        ),
        (ProcessTimeoutError(), "LibreOffice version probe timed out"),
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

    monkeypatch.setattr(libreoffice_module, "run_process", fake_run)

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
    ) -> ProcessResult:
        nonlocal temporary_root
        assert timeout_seconds == 9
        captured_calls.append(tuple(arguments))
        output_directory = _output_directory(arguments)
        temporary_root = output_directory.parent
        _write_pdf(output_directory / f"{source.stem}.pdf")
        return ProcessResult(0, "converted", "")

    monkeypatch.setattr(libreoffice_module, "run_process", fake_run)

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
    ) -> ProcessResult:
        nonlocal temporary_root
        del timeout_seconds
        temporary_root = _output_directory(arguments).parent
        return ProcessResult(5, "", "private diagnostic")

    monkeypatch.setattr(libreoffice_module, "run_process", fake_run)

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
        "run_process",
        lambda arguments, timeout_seconds: ProcessResult(0, "", ""),
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
    ) -> ProcessResult:
        del timeout_seconds
        (_output_directory(arguments) / f"{source.stem}.pdf").write_bytes(b"invalid")
        return ProcessResult(0, "", "")

    monkeypatch.setattr(libreoffice_module, "run_process", fake_run)

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
        raise ProcessTimeoutError

    monkeypatch.setattr(libreoffice_module, "run_process", fake_run)

    with pytest.raises(ConversionTimeoutError) as raised:
        LibreOfficeEngine(tmp_path / "soffice").convert(
            source,
            tmp_path / "output.pdf",
            timeout_seconds=5,
            revision_mode=RevisionMode.FINAL,
            comment_mode=CommentMode.OMIT,
        )

    assert isinstance(raised.value.__cause__, ProcessTimeoutError)
    assert temporary_root is not None
    assert not temporary_root.exists()


def test_conversion_rejects_unsupported_modes_before_starting_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source(tmp_path)

    def unexpected_run(arguments: Sequence[str], timeout_seconds: float) -> object:
        raise AssertionError((arguments, timeout_seconds))

    monkeypatch.setattr(libreoffice_module, "run_process", unexpected_run)

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


def test_convert_file_supports_odt_to_docx_with_target_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "臺灣 文件.odt"
    _write_odt(source)
    output = tmp_path / "nested" / "結果.docx"
    executable = tmp_path / "soffice"

    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        assert timeout_seconds == 7
        output_directory = _output_directory(arguments)
        generated = output_directory / f"{source.stem}.docx"
        with ZipFile(generated, "w", ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("_rels/.rels", "<Relationships/>")
            archive.writestr("word/document.xml", "<document/>")
        return ProcessResult(0, "converted", "")

    monkeypatch.setattr(libreoffice_module, "run_process", fake_run)

    result = LibreOfficeEngine(executable).convert_file(
        source,
        output,
        source_format=SourceFormat.ODT,
        artifact_type=ArtifactType.DOCX,
        timeout_seconds=7,
    )

    assert result.engine is EngineName.LIBREOFFICE
    assert result.output_path == output
    assert output.is_file()


def test_convert_file_imports_html_into_writer_and_saves_a_text_document(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "中介文件.html"
    source.write_text("<!doctype html><html><body><p>內文</p></body></html>", encoding="utf-8")
    output = tmp_path / "結果.odt"
    seen: list[tuple[str, ...]] = []

    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        del timeout_seconds
        seen.append(tuple(arguments))
        generated = _output_directory(arguments) / f"{source.stem}.odt"
        with ZipFile(generated, "w", ZIP_DEFLATED) as archive:
            archive.writestr("mimetype", "application/vnd.oasis.opendocument.text")
            archive.writestr("META-INF/manifest.xml", "<manifest/>")
            archive.writestr("content.xml", "<content/>")
        return ProcessResult(0, "converted", "")

    monkeypatch.setattr(libreoffice_module, "run_process", fake_run)

    result = LibreOfficeEngine(tmp_path / "soffice").convert_file(
        source,
        output,
        source_format=SourceFormat.HTML,
        artifact_type=ArtifactType.ODT,
        timeout_seconds=9,
    )

    assert result.output_path == output
    assert output.is_file()
    arguments = seen[0]
    # Without both filters LibreOffice saves a Writer/Web document with no page setup.
    assert "--infilter=HTML (StarWriter)" in arguments
    assert arguments[arguments.index("--convert-to") + 1] == "odt:writer8"


def test_convert_file_rejects_a_source_format_no_filter_covers(tmp_path: Path) -> None:
    source = tmp_path / "report.pdf"
    source.write_bytes(b"%PDF-1.7")

    with pytest.raises(InvalidInputError, match="DOCX, ODT, or HTML source"):
        LibreOfficeEngine(tmp_path / "soffice").convert_file(
            source,
            tmp_path / "out.odt",
            source_format=SourceFormat.PDF,
            artifact_type=ArtifactType.ODT,
            timeout_seconds=5,
        )
