"""Unit tests for normalized semantic extraction from HTML sources."""

from __future__ import annotations

from pathlib import Path

import pytest

from gordon_doc_converter.content.html_source import extract_html_content
from gordon_doc_converter.content.markdown import render_markdown
from gordon_doc_converter.content.models import BlockKind, InlineKind, LayoutAvailability
from gordon_doc_converter.exceptions import InvalidInputError
from gordon_doc_converter.models import MetadataDetail, SourceFormat

_PIXEL_DATA_URI = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
    "AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _html(path: Path, body: str) -> Path:
    source = path / "source.html"
    source.write_text(body, encoding="utf-8", newline="\n")
    return source


def test_headings_paragraphs_and_links_become_normalized_blocks(tmp_path: Path) -> None:
    source = _html(
        tmp_path,
        '<h1>標題</h1><h3>小節</h3><p>請見 <a href="https://example.com/a">連結</a>。</p>',
    )

    content = extract_html_content(source)

    assert content.source_format is SourceFormat.HTML
    assert [(block.kind, block.level) for block in content.blocks] == [
        (BlockKind.HEADING, 1),
        (BlockKind.HEADING, 3),
        (BlockKind.PARAGRAPH, None),
    ]
    link = content.blocks[2].inlines[1]
    assert link.kind is InlineKind.LINK
    assert link.target == "https://example.com/a"


def test_nested_and_ordered_lists_keep_level_and_numbering(tmp_path: Path) -> None:
    source = _html(
        tmp_path,
        "<ul><li>外層<ul><li>內層</li></ul></li><li>第二項</ul>"
        '<ol start="3"><li>丙</li><li>丁</li></ol>',
    )

    content = extract_html_content(source)

    assert [(block.list_level, block.text) for block in content.blocks] == [
        (0, "外層"),
        (1, "內層"),
        (0, "第二項"),
        (0, "3. 丙"),
        (0, "4. 丁"),
    ]


def test_tables_recover_omitted_end_tags_and_report_merged_cells(tmp_path: Path) -> None:
    source = _html(
        tmp_path,
        "<table><tr><th>區域</th><th>營收</th><tr><td>亞太</td><td colspan='2'>1200</td></table>",
    )

    content = extract_html_content(source)

    table = content.blocks[0]
    assert table.kind is BlockKind.TABLE
    assert [[cell[0].text for cell in row] for row in table.rows] == [
        ["區域", "營收"],
        ["亞太", "1200"],
    ]
    assert "INCOMPLETE_TABLE_STRUCTURE" in {warning.code for warning in content.warnings}


def test_script_and_style_content_is_omitted_with_one_warning(tmp_path: Path) -> None:
    source = _html(
        tmp_path,
        "<style>p { color: red }</style><script>var secret = '<p>洩漏</p>';</script><p>保留</p>",
    )

    content = extract_html_content(source)

    assert [block.text for block in content.blocks] == ["保留"]
    assert [warning.code for warning in content.warnings] == ["HTML_NON_CONTENT_ELEMENT_OMITTED"]


def test_data_uri_images_become_assets_and_urls_stay_linked(tmp_path: Path) -> None:
    source = _html(
        tmp_path,
        f'<p><img src="{_PIXEL_DATA_URI}" alt="像素"></p>'
        '<p><img src="https://cdn.example.com/chart.png" alt="圖表"></p>',
    )

    content = extract_html_content(source)

    assert [(asset.filename, asset.media_type) for asset in content.assets] == [
        ("image-0001.png", "image/png")
    ]
    embedded, linked = content.blocks[0].inlines[0], content.blocks[1].inlines[0]
    assert embedded.kind is InlineKind.IMAGE
    assert embedded.asset_id == "image-0001.png"
    assert linked.target == "https://cdn.example.com/chart.png"
    assert "HTML_EXTERNAL_ASSET_REFERENCED" in {warning.code for warning in content.warnings}
    markdown = render_markdown(content, asset_directory="source.assets")
    assert "![像素](source.assets/image-0001.png)" in markdown
    assert "![圖表](https://cdn.example.com/chart.png)" in markdown


def test_unsafe_link_and_image_targets_are_dropped(tmp_path: Path) -> None:
    source = _html(
        tmp_path,
        '<p><a href="javascript:alert(1)">點我</a></p>'
        '<p><img src="data:text/html,<script>x</script>" alt="假圖"></p>',
    )

    content = extract_html_content(source)

    assert content.blocks[0].inlines[0].kind is InlineKind.TEXT
    assert content.blocks[0].inlines[0].target is None
    assert content.blocks[1].inlines[0].target is None
    assert content.assets == ()
    assert "HTML_ASSET_DECODE_FAILED" in {warning.code for warning in content.warnings}


def test_tracked_revision_elements_map_to_insertion_and_deletion(tmp_path: Path) -> None:
    source = _html(tmp_path, "<p><ins>新增</ins><del>刪除</del></p>")

    content = extract_html_content(source)

    assert [span.kind for span in content.blocks[0].inlines] == [
        InlineKind.INSERTION,
        InlineKind.DELETION,
    ]


def test_preformatted_text_keeps_line_breaks(tmp_path: Path) -> None:
    source = _html(tmp_path, "<pre>第一行\n  第二行</pre><p>折行<br>之後</p>")

    content = extract_html_content(source)

    assert content.blocks[0].text == "第一行\n  第二行"
    assert content.blocks[1].text == "折行\n之後"


def test_carriage_returns_normalize_so_extraction_is_platform_independent(
    tmp_path: Path,
) -> None:
    windows = tmp_path / "windows.html"
    windows.write_bytes("<pre>第一行\r\n  第二行</pre><p>折行\r\n之後</p>".encode())
    classic_mac = tmp_path / "classic-mac.html"
    classic_mac.write_bytes("<pre>第一行\r  第二行</pre><p>折行\r之後</p>".encode())

    for source in (windows, classic_mac):
        content = extract_html_content(source)

        assert content.blocks[0].text == "第一行\n  第二行"
        assert content.blocks[1].text == "折行 之後"


def test_metadata_comes_from_title_and_allowlisted_meta_elements(tmp_path: Path) -> None:
    source = _html(
        tmp_path,
        "<head><title>季度報告</title>"
        '<meta name="author" content="王小明">'
        '<meta name="description" content="營運回顧">'
        '<meta name="keywords" content="營運">'
        '<meta name="dcterms.modified" content="2026-01-31"></head>'
        "<body><p>內文</p></body>",
    )

    content = extract_html_content(source)

    assert content.metadata is not None
    assert content.metadata.title == "季度報告"
    assert content.metadata.creator == "王小明"
    assert content.metadata.subject == "營運回顧"
    assert content.metadata.keywords == "營運"
    assert content.metadata.modified == "2026-01-31"
    assert [block.text for block in content.blocks] == ["內文"]


def test_metadata_detail_none_omits_metadata_and_layout_reports_unavailable(
    tmp_path: Path,
) -> None:
    source = _html(tmp_path, "<title>標題</title><p>內文</p>")

    assert extract_html_content(source, metadata_detail=MetadataDetail.NONE).metadata is None
    layout = extract_html_content(source, metadata_detail=MetadataDetail.LAYOUT)
    assert layout.layout.availability is LayoutAvailability.UNAVAILABLE
    assert "LAYOUT_METADATA_UNAVAILABLE" in {warning.code for warning in layout.warnings}


def test_declared_charset_is_honored_and_bad_bytes_are_reported(tmp_path: Path) -> None:
    declared = tmp_path / "source.html"
    declared.write_bytes('<meta charset="big5"><p>中文測試</p>'.encode("big5"))
    assert extract_html_content(declared).blocks[0].text == "中文測試"

    broken = tmp_path / "broken.html"
    broken.write_bytes(b"<p>bad \xff\xfe bytes</p>")
    content = extract_html_content(broken)
    assert "HTML_ENCODING_REPLACED" in {warning.code for warning in content.warnings}
    assert content.blocks[0].text.startswith("bad ")


def test_deeply_nested_markup_is_flattened_instead_of_exhausting_memory(
    tmp_path: Path,
) -> None:
    source = _html(tmp_path, "<div>" * 2_000 + "<p>最深層</p>" + "</div>" * 2_000)

    content = extract_html_content(source)

    assert [block.text for block in content.blocks] == ["最深層"]
    assert "HTML_NESTING_DEPTH_EXCEEDED" in {warning.code for warning in content.warnings}


def test_source_anchors_locate_blocks_by_element_path_and_id(tmp_path: Path) -> None:
    source = _html(tmp_path, '<body><p>一</p><p id="second">二</p></body>')

    content = extract_html_content(source)

    anchors = [block.source_anchor for block in content.blocks]
    assert anchors[0] is not None and anchors[1] is not None
    assert anchors[0].locator == "html-element"
    assert anchors[0].element_path == "/body[1]/p[1]"
    assert anchors[1].element_path == "/body[1]/p[2]"
    assert anchors[1].native_id == "second"


def test_missing_source_and_wrong_extension_raise_invalid_input(tmp_path: Path) -> None:
    with pytest.raises(InvalidInputError):
        extract_html_content(tmp_path / "absent.html")
    other = tmp_path / "note.txt"
    other.write_text("<p>text</p>", encoding="utf-8")
    with pytest.raises(InvalidInputError):
        extract_html_content(other)
