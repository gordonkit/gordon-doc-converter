"""Unit tests for the Pandoc markup rendering adapter."""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
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
from gordon_doc_converter.models import ConversionOptions, PageOrientation, SourceFormat
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

    def capture(path: Path, font_family: str | None) -> None:
        original(path, font_family)
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
    assert "eastAsiaTheme" not in styles
    assert "Cambria" not in styles
    assert 'w:val="21"' in styles
    with ZipFile(output) as archive:
        document = archive.read("word/document.xml").decode("utf-8")
    assert 'w:w="11906"' in document


def test_docx_conversion_uses_the_requested_font_for_all_text_scripts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "out.docx"
    restyled: list[bytes] = []

    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        del timeout_seconds
        items = tuple(arguments)
        target = Path(items[items.index("--output") + 1])
        _write_docx(target)
        return ProcessResult(0, "", "")

    monkeypatch.setattr(pandoc_module, "run_process", fake_run)
    original = pandoc_module._restyle_reference_docx

    def capture(path: Path, font_family: str | None) -> None:
        original(path, font_family)
        with ZipFile(path) as archive:
            restyled.append(archive.read("word/styles.xml"))

    monkeypatch.setattr(pandoc_module, "_restyle_reference_docx", capture)

    _converter(tmp_path).convert(
        _source(tmp_path),
        output,
        source_format=SourceFormat.MARKDOWN,
        options=ConversionOptions(font_family="Noto Sans TC"),
    )

    styles = restyled[0].decode("utf-8")
    assert 'w:ascii="Noto Sans TC"' in styles
    assert 'w:eastAsia="Noto Sans TC"' in styles
    assert "eastAsiaTheme" not in styles


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


_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _body(*paragraphs: str) -> ET.Element:
    return ET.fromstring(
        f'<w:document xmlns:w="{_W_NS}"><w:body>{"".join(paragraphs)}</w:body></w:document>'
    )


def _styled(style: str, text: str = "x") -> str:
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>'


def _styles_of(root: ET.Element) -> list[str | None]:
    return [
        paragraph.find("w:pPr/w:pStyle", pandoc_module._NS).get(f"{{{_W_NS}}}val")  # type: ignore[union-attr]
        for paragraph in root.findall("w:body/w:p", pandoc_module._NS)
    ]


def test_title_paragraph_is_dropped_when_the_body_has_its_own_heading() -> None:
    root = _body(_styled("Title"), _styled("Heading1"), _styled("BodyText"))

    pandoc_module._apply_document_fixes(root)

    assert _styles_of(root) == ["Heading1", "BodyText"]


def test_title_paragraph_is_kept_without_a_heading() -> None:
    root = _body(_styled("Title"), _styled("BodyText"))

    pandoc_module._apply_document_fixes(root)

    assert _styles_of(root) == ["Title", "BodyText"]


def test_page_break_marker_becomes_page_break_before_on_the_next_paragraph() -> None:
    root = _body(_styled("BodyText"), _styled("GordonPageBreak", ""), _styled("Heading2"))

    pandoc_module._apply_document_fixes(root)

    assert _styles_of(root) == ["BodyText", "Heading2"]
    heading = root.findall("w:body/w:p", pandoc_module._NS)[1]
    children = [child.tag.rsplit("}", 1)[1] for child in heading.find("w:pPr", pandoc_module._NS)]  # type: ignore[union-attr]
    assert children == ["pStyle", "pageBreakBefore"]


def test_page_break_marker_before_a_table_becomes_an_explicit_break() -> None:
    root = _body(_styled("GordonPageBreak", ""))
    body = root.find("w:body", pandoc_module._NS)
    assert body is not None
    ET.SubElement(body, f"{{{_W_NS}}}tbl")

    pandoc_module._apply_document_fixes(root)

    breaks = root.findall("w:body/w:p/w:r/w:br", pandoc_module._NS)
    assert [item.get(f"{{{_W_NS}}}type") for item in breaks] == ["page"]


def test_trailing_page_break_marker_is_removed() -> None:
    root = _body(_styled("BodyText"), _styled("GordonPageBreak", ""))

    pandoc_module._apply_document_fixes(root)

    assert _styles_of(root) == ["BodyText"]


def test_reference_styles_use_monospace_code_and_bordered_tables() -> None:
    styles = (
        f'<w:styles xmlns:w="{_W_NS}">'
        '<w:style w:styleId="VerbatimChar"><w:rPr><w:rFonts w:ascii="Consolas"/></w:rPr></w:style>'
        '<w:style w:styleId="SourceCode"><w:pPr><w:wordWrap w:val="off"/></w:pPr></w:style>'
        '<w:style w:styleId="Table"><w:tblPr><w:tblCellMar>'
        '<w:top w:w="0"/><w:bottom w:w="0"/></w:tblCellMar></w:tblPr>'
        '<w:tblStylePr w:type="firstRow"><w:tcPr><w:tcBorders><w:bottom w:val="single"/>'
        "</w:tcBorders></w:tcPr></w:tblStylePr></w:style></w:styles>"
    )
    root = ET.fromstring(styles)
    for style in root:
        style_id = style.get(f"{{{_W_NS}}}styleId")
        if style_id == "VerbatimChar":
            pandoc_module._apply_code_run_style(style)
        elif style_id == "SourceCode":
            pandoc_module._apply_code_block_style(style)
        else:
            pandoc_module._apply_table_style(style)

    ns = pandoc_module._NS
    fonts = root.find("w:style/w:rPr/w:rFonts", ns)
    assert fonts is not None
    assert fonts.get(f"{{{_W_NS}}}ascii") == "Consolas"
    code_shading = root.find("w:style/w:pPr/w:shd", ns)
    assert code_shading is not None
    assert code_shading.get(f"{{{_W_NS}}}fill") == "F3F4F6"
    table_properties = root.find("w:style/w:tblPr", ns)
    assert table_properties is not None
    order = [child.tag.rsplit("}", 1)[1] for child in table_properties]
    assert order == ["tblBorders", "tblCellMar"]
    assert root.find("w:style/w:tblPr/w:tblCellMar/w:top", ns).get(f"{{{_W_NS}}}w") == "40"  # type: ignore[union-attr]
    assert root.find("w:style/w:tblStylePr/w:rPr/w:b", ns) is not None
    cell_children = [
        child.tag.rsplit("}", 1)[1]
        for child in root.find("w:style/w:tblStylePr/w:tcPr", ns)  # type: ignore[union-attr]
    ]
    assert cell_children == ["tcBorders", "shd"]


def test_html_sources_get_the_page_break_filter_but_markdown_does_not(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
        del timeout_seconds
        items = tuple(arguments)
        calls.append(items)
        _write_docx(Path(items[items.index("--output") + 1]))
        return ProcessResult(0, "", "")

    monkeypatch.setattr(pandoc_module, "run_process", fake_run)
    for source_format in (SourceFormat.HTML, SourceFormat.MARKDOWN):
        _converter(tmp_path).convert(
            _source(tmp_path / source_format.value),
            tmp_path / f"{source_format.value}.docx",
            source_format=source_format,
            options=ConversionOptions(),
        )

    html_call = next(items for items in calls if "html" in items)
    markdown_call = next(items for items in calls if "gfm" in items)
    assert "--lua-filter" in html_call
    assert "--lua-filter" not in markdown_call


def _zip_text(path: Path, name: str) -> str:
    with ZipFile(path) as archive:
        return archive.read(name).decode("utf-8")


def _package(path: Path) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "word/document.xml",
            f'<w:document xmlns:w="{_W_NS}"><w:body><w:p/><w:sectPr/></w:body></w:document>',
        )
        archive.writestr("word/_rels/document.xml.rels", "<Relationships></Relationships>")
        archive.writestr("[Content_Types].xml", "<Types></Types>")


def test_header_and_footer_parts_are_added_with_live_page_fields(tmp_path: Path) -> None:
    package = tmp_path / "out.docx"
    _package(package)

    pandoc_module._set_docx_page_layout(
        package,
        PageOrientation.PORTRAIT,
        "Acme <內部>",
        "Page {page} of {pages}",
    )

    document = _zip_text(package, "word/document.xml")
    assert document.index("headerReference") < document.index("footerReference")
    assert "rIdGordonHeader" in document and "rIdGordonFooter" in document
    footer = _zip_text(package, "word/gordon-footer.xml")
    assert " PAGE " in footer and " NUMPAGES " in footer
    assert "Page " in footer and " of " in footer
    assert "Acme &lt;內部&gt;" in _zip_text(package, "word/gordon-header.xml")
    assert "gordon-header.xml" in _zip_text(package, "word/_rels/document.xml.rels")
    assert "gordon-footer.xml" in _zip_text(package, "[Content_Types].xml")


def test_no_header_or_footer_parts_are_added_without_meta_tags(tmp_path: Path) -> None:
    package = tmp_path / "out.docx"
    _package(package)

    pandoc_module._set_docx_page_layout(package, PageOrientation.PORTRAIT)

    with ZipFile(package) as archive:
        assert not [name for name in archive.namelist() if "gordon-" in name]
    assert "headerReference" not in _zip_text(package, "word/document.xml")


def test_running_text_is_read_from_gordon_meta_tags(tmp_path: Path) -> None:
    source = tmp_path / "doc.html"
    source.write_text(
        '<meta name="gordon-header" content="Top"><meta name="gordon-footer" content=" ">'
        '<meta name="author" content="x">',
        encoding="utf-8",
    )

    assert pandoc_module._read_running_text(source) == ("Top", None)


def test_author_and_date_paragraphs_are_dropped_only_for_html_sources() -> None:
    def styles(*, html_source: bool) -> list[str | None]:
        root = _body(_styled("Author"), _styled("Date"), _styled("BodyText"))
        pandoc_module._apply_document_fixes(root, html_source=html_source)
        return _styles_of(root)

    assert styles(html_source=True) == ["BodyText"]
    assert styles(html_source=False) == ["Author", "Date", "BodyText"]
