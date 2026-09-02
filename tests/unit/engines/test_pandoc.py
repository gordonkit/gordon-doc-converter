"""Unit tests for the Pandoc markup rendering adapter."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

import gordon_doc_converter.engines.pandoc as pandoc_module
from gordon_doc_converter.engines.pandoc import PandocConverter
from gordon_doc_converter.exceptions import (
    ConversionTimeoutError,
    EngineFailedError,
    EngineUnavailableError,
)
from gordon_doc_converter.models import ConversionOptions, SourceFormat
from gordon_doc_converter.process.runner import ProcessResult, ProcessTimeoutError

_DOCUMENT = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    "<w:body/></w:document>"
)
_STYLES = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    "<w:docDefaults><w:rPrDefault><w:rPr>"
    '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="24"/>'
    "</w:rPr></w:rPrDefault></w:docDefaults>"
    '<w:style w:styleId="Heading1"><w:rPr><w:rFonts w:ascii="Cambria"/></w:rPr></w:style>'
    '<w:style w:styleId="BodyText"><w:rPr><w:b/></w:rPr></w:style>'
    "</w:styles>"
)


def _write_docx(path: Path) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("word/styles.xml", _STYLES)
        archive.writestr("word/document.xml", _DOCUMENT)


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "文件" / "報告.md"
    source.parent.mkdir(parents=True)
    source.write_text("# 標題\n", encoding="utf-8")
    return source


def _converter(tmp_path: Path) -> PandocConverter:
    return PandocConverter(str(tmp_path / "pandoc"))


def test_missing_pandoc_is_reported_as_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)
    converter = PandocConverter()

    with pytest.raises(EngineUnavailableError):
        converter.convert(
            _source(tmp_path),
            tmp_path / "out.docx",
            source_format=SourceFormat.MARKDOWN,
            options=ConversionOptions(),
        )


def test_markdown_is_read_as_gfm_with_the_source_resource_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source(tmp_path)
    output = tmp_path / "out.docx"
    calls: list[tuple[str, ...]] = []

    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        del timeout_seconds
        items = tuple(arguments)
        calls.append(items)
        _write_docx(Path(items[items.index("--output") + 1]))
        return ProcessResult(0, "", "")

    monkeypatch.setattr(pandoc_module, "run_process", fake_run)

    _converter(tmp_path).convert(
        source,
        output,
        source_format=SourceFormat.MARKDOWN,
        options=ConversionOptions(),
    )

    arguments = calls[-1]
    assert arguments[arguments.index("--from") + 1] == "gfm"
    assert arguments[arguments.index("--resource-path") + 1] == str(source.parent)
    # PDF rendering left this adapter, so no engine wiring should remain.
    assert not any(item.startswith("--pdf-engine") for item in arguments)


def test_docx_conversion_uses_a_restyled_reference_document(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "out.docx"
    references: list[Path] = []

    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        del timeout_seconds
        items = tuple(arguments)
        target = Path(items[items.index("--output") + 1])
        _write_docx(target)
        if "--reference-doc" in items:
            references.append(Path(items[items.index("--reference-doc") + 1]))
        return ProcessResult(0, "", "")

    monkeypatch.setattr(pandoc_module, "run_process", fake_run)

    restyled: list[bytes] = []
    original = pandoc_module._restyle_reference_docx

    def capture(path: Path) -> None:
        original(path)
        with ZipFile(path) as archive:
            restyled.append(archive.read("word/styles.xml"))

    monkeypatch.setattr(pandoc_module, "_restyle_reference_docx", capture)

    _converter(tmp_path).convert(
        _source(tmp_path),
        output,
        source_format=SourceFormat.MARKDOWN,
        options=ConversionOptions(),
    )

    assert len(references) == 1
    styles = restyled[0].decode("utf-8")
    assert 'w:eastAsia="Microsoft JhengHei"' in styles
    assert "Cambria" not in styles
    assert 'w:val="21"' in styles
    with ZipFile(output) as archive:
        document = archive.read("word/document.xml").decode("utf-8")
    assert 'w:w="11906"' in document


def test_docx_conversion_continues_when_the_reference_build_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "out.docx"
    seen: list[tuple[str, ...]] = []

    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        del timeout_seconds
        items = tuple(arguments)
        seen.append(items)
        target = Path(items[items.index("--output") + 1])
        if target.name == "reference.docx":
            return ProcessResult(3, "", "reference build failed")
        _write_docx(target)
        return ProcessResult(0, "", "")

    monkeypatch.setattr(pandoc_module, "run_process", fake_run)

    _converter(tmp_path).convert(
        _source(tmp_path),
        output,
        source_format=SourceFormat.MARKDOWN,
        options=ConversionOptions(),
    )

    assert output.is_file()
    assert not any("--reference-doc" in items for items in seen)


def test_failed_pandoc_run_reports_the_last_stderr_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        del arguments, timeout_seconds
        return ProcessResult(1, "", "context\nunexpected end of input")

    monkeypatch.setattr(pandoc_module, "run_process", fake_run)

    with pytest.raises(EngineFailedError, match="unexpected end of input"):
        _converter(tmp_path).convert(
            _source(tmp_path),
            tmp_path / "out.docx",
            source_format=SourceFormat.HTML,
            options=ConversionOptions(),
        )


def test_timed_out_pandoc_run_is_reported_as_a_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        del arguments, timeout_seconds
        raise ProcessTimeoutError

    monkeypatch.setattr(pandoc_module, "run_process", fake_run)

    with pytest.raises(ConversionTimeoutError):
        _converter(tmp_path).convert(
            _source(tmp_path),
            tmp_path / "out.docx",
            source_format=SourceFormat.HTML,
            options=ConversionOptions(),
        )
