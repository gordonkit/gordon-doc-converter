"""Unit tests for normalized semantic extraction from Markdown sources."""

from __future__ import annotations

from pathlib import Path

import pytest

from gordon_doc_converter.content.markdown import render_markdown
from gordon_doc_converter.content.markdown_source import extract_markdown_content
from gordon_doc_converter.content.models import (
    BlockKind,
    InlineKind,
    InlineStyle,
    LayoutAvailability,
)
from gordon_doc_converter.exceptions import InvalidInputError
from gordon_doc_converter.models import MetadataDetail, SourceFormat

_PIXEL_DATA_URI = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
    "AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _markdown(path: Path, body: str) -> Path:
    source = path / "source.md"
    source.write_text(body, encoding="utf-8", newline="\n")
    return source


def test_headings_and_paragraphs_become_normalized_blocks(tmp_path: Path) -> None:
    source = _markdown(tmp_path, "# 標題\n\n### 小節\n\n內文。\n")

    content = extract_markdown_content(source)

    assert content.source_format is SourceFormat.MARKDOWN
    assert content.source_sha256 is not None
    assert [(block.kind, block.level, block.text) for block in content.blocks] == [
        (BlockKind.HEADING, 1, "標題"),
        (BlockKind.HEADING, 3, "小節"),
        (BlockKind.PARAGRAPH, None, "內文。"),
    ]


def test_inline_formatting_links_and_strikethrough_are_normalized(tmp_path: Path) -> None:
    source = _markdown(
        tmp_path,
        "Plain **bold** *italic* `code` ~~struck~~ [link](https://example.com/a).\n",
    )

    spans = extract_markdown_content(source).blocks[0].inlines
    by_text = {span.text: span for span in spans}

    assert by_text["bold"].styles == frozenset({InlineStyle.STRONG})
    assert by_text["italic"].styles == frozenset({InlineStyle.EMPHASIS})
    assert by_text["code"].styles == frozenset({InlineStyle.CODE})
    assert by_text["struck"].kind is InlineKind.DELETION
    assert by_text["link"].kind is InlineKind.LINK
    assert by_text["link"].target == "https://example.com/a"


def test_nested_emphasis_combines_styles_on_one_span(tmp_path: Path) -> None:
    source = _markdown(tmp_path, "***both*** and **[bold link](https://example.com/a)**\n")

    spans = extract_markdown_content(source).blocks[0].inlines

    assert spans[0].text == "both"
    assert spans[0].styles == frozenset({InlineStyle.STRONG, InlineStyle.EMPHASIS})
    link = next(span for span in spans if span.kind is InlineKind.LINK)
    assert link.styles == frozenset({InlineStyle.STRONG})


def test_unsafe_link_and_image_targets_are_dropped(tmp_path: Path) -> None:
    source = _markdown(
        tmp_path,
        "[危險](javascript:alert%281%29) 與 ![圖](javascript:alert%281%29)\n",
    )

    spans = extract_markdown_content(source).blocks[0].inlines

    assert all(span.target is None for span in spans)


def test_lists_carry_nesting_depth_and_ordered_counters(tmp_path: Path) -> None:
    source = _markdown(
        tmp_path,
        "- one\n- two\n  - nested\n\n3. third\n1. fourth\n",
    )

    content = extract_markdown_content(source)

    assert [(block.kind, block.list_level, block.text) for block in content.blocks] == [
        (BlockKind.LIST_ITEM, 0, "one"),
        (BlockKind.LIST_ITEM, 0, "two"),
        (BlockKind.LIST_ITEM, 1, "nested"),
        (BlockKind.LIST_ITEM, 0, "3. third"),
        (BlockKind.LIST_ITEM, 0, "4. fourth"),
    ]


def test_paragraphs_after_the_first_stay_inside_their_list_item(tmp_path: Path) -> None:
    source = _markdown(tmp_path, "- first\n\n  continuation\n\n- second\n")

    content = extract_markdown_content(source)

    assert [(block.kind, block.list_level, block.text) for block in content.blocks] == [
        (BlockKind.LIST_ITEM, 0, "first"),
        (BlockKind.PARAGRAPH, 0, "continuation"),
        (BlockKind.LIST_ITEM, 0, "second"),
    ]


def test_blockquotes_record_their_nesting_depth(tmp_path: Path) -> None:
    source = _markdown(tmp_path, "> outer\n>\n> > inner\n\nafter\n")

    content = extract_markdown_content(source)

    assert [(block.text, block.quote_level) for block in content.blocks] == [
        ("outer", 1),
        ("inner", 2),
        ("after", None),
    ]


def test_fenced_and_indented_code_blocks_keep_their_body(tmp_path: Path) -> None:
    source = _markdown(
        tmp_path,
        "```python\ndef f():\n    return 1\n```\n\ntext\n\n    indented\n",
    )

    content = extract_markdown_content(source)

    fenced = content.blocks[0]
    assert fenced.kind is BlockKind.CODE_BLOCK
    assert fenced.language == "python"
    assert fenced.text == "def f():\n    return 1"
    indented = content.blocks[2]
    assert indented.kind is BlockKind.CODE_BLOCK
    assert indented.language is None
    assert indented.text == "indented"


def test_thematic_breaks_and_tables_become_their_own_blocks(tmp_path: Path) -> None:
    source = _markdown(
        tmp_path,
        "---\n\n| a | b |\n| - | - |\n| 1 |   |\n",
    )

    content = extract_markdown_content(source)

    assert content.blocks[0].kind is BlockKind.THEMATIC_BREAK
    table = content.blocks[1]
    assert table.kind is BlockKind.TABLE
    # An empty trailing cell still occupies its column.
    assert [[["".join(span.text for span in cell)] for cell in row] for row in table.rows] == [
        [["a"], ["b"]],
        [["1"], [""]],
    ]


def test_front_matter_becomes_document_metadata(tmp_path: Path) -> None:
    source = _markdown(
        tmp_path,
        "---\ntitle: 報告\nauthor: GordonKit\ntags:\n  - doc\n  - md\n"
        "date: 2026-09-01\n---\n\n內文\n",
    )

    content = extract_markdown_content(source)

    assert content.metadata is not None
    assert content.metadata.title == "報告"
    assert content.metadata.creator == "GordonKit"
    assert content.metadata.keywords == "doc, md"
    assert content.metadata.created == "2026-09-01"
    assert [block.text for block in content.blocks] == ["內文"]


def test_unreadable_front_matter_is_reported_and_skipped(tmp_path: Path) -> None:
    source = _markdown(tmp_path, "---\ntitle: [unclosed\n---\n\n內文\n")

    content = extract_markdown_content(source)

    assert content.metadata == content.metadata.__class__()
    assert [warning.code for warning in content.warnings] == ["MARKDOWN_FRONT_MATTER_UNREADABLE"]
    assert [block.text for block in content.blocks] == ["內文"]


def test_source_anchors_count_lines_past_the_front_matter(tmp_path: Path) -> None:
    source = _markdown(tmp_path, "---\ntitle: T\n---\n\n第一段\n\n第二段\n")

    content = extract_markdown_content(source)

    anchors = [block.source_anchor for block in content.blocks]
    assert anchors[0] is not None and anchors[1] is not None
    assert anchors[0].locator == "markdown-line"
    assert anchors[0].element_path == "line[5]"
    assert anchors[1].element_path == "line[7]"


def test_inline_data_uri_images_become_shared_assets(tmp_path: Path) -> None:
    source = _markdown(tmp_path, f"![圖說]({_PIXEL_DATA_URI})\n")

    content = extract_markdown_content(source)

    assert [asset.filename for asset in content.assets] == ["image-0001.png"]
    span = content.blocks[0].inlines[0]
    assert span.kind is InlineKind.IMAGE
    assert span.text == "圖說"
    assert span.asset_id == "image-0001.png"


def test_referenced_images_stay_linked_with_a_warning(tmp_path: Path) -> None:
    source = _markdown(tmp_path, "![圖](assets/photo.png)\n")

    content = extract_markdown_content(source)

    span = content.blocks[0].inlines[0]
    assert span.kind is InlineKind.IMAGE
    assert span.asset_id is None
    assert span.target == "assets/photo.png"
    assert "MARKDOWN_EXTERNAL_ASSET_REFERENCED" in {warning.code for warning in content.warnings}


def test_raw_html_blocks_are_omitted_but_revision_tags_survive(tmp_path: Path) -> None:
    source = _markdown(
        tmp_path,
        "<div><p>hidden</p></div>\n\n保留 <ins>新增</ins> 與 <del>刪除</del>。\n",
    )

    content = extract_markdown_content(source)

    kinds = {span.kind for block in content.blocks for span in block.inlines}
    assert InlineKind.INSERTION in kinds
    assert InlineKind.DELETION in kinds
    assert "hidden" not in "".join(block.text for block in content.blocks)
    assert "MARKDOWN_RAW_HTML_OMITTED" in {warning.code for warning in content.warnings}


def test_requested_layout_metadata_is_reported_unavailable(tmp_path: Path) -> None:
    source = _markdown(tmp_path, "內文\n")

    content = extract_markdown_content(source, metadata_detail=MetadataDetail.LAYOUT)

    assert content.layout.availability is LayoutAvailability.UNAVAILABLE
    assert "LAYOUT_METADATA_UNAVAILABLE" in {warning.code for warning in content.warnings}


def test_metadata_detail_none_omits_document_properties(tmp_path: Path) -> None:
    source = _markdown(tmp_path, "---\ntitle: 報告\n---\n\n內文\n")

    content = extract_markdown_content(source, metadata_detail=MetadataDetail.NONE)

    assert content.metadata is None


def test_markdown_round_trips_through_the_normalized_model(tmp_path: Path) -> None:
    body = (
        "# 標題\n\n"
        "Plain **bold** and `code`.\n\n"
        "> quoted\n\n"
        "```sh\nls -l\n```\n\n"
        "---\n\n"
        "- one\n- two\n"
    )
    source = _markdown(tmp_path, body)

    rendered = render_markdown(extract_markdown_content(source), asset_directory="a.assets")

    assert rendered == body


def test_missing_source_and_wrong_extension_raise_invalid_input(tmp_path: Path) -> None:
    with pytest.raises(InvalidInputError):
        extract_markdown_content(tmp_path / "absent.md")
    other = tmp_path / "note.txt"
    other.write_text("# heading", encoding="utf-8")
    with pytest.raises(InvalidInputError):
        extract_markdown_content(other)


def test_task_list_checkboxes_become_renderable_symbols(tmp_path: Path) -> None:
    source = _markdown(tmp_path, "- [ ] 待辦\n- [X] 完成\n- 一般項目\n- [ ]無空白\n")

    content = extract_markdown_content(source)

    assert [block.text for block in content.blocks if block.kind is BlockKind.LIST_ITEM] == [
        "□ 待辦",
        "☑ 完成",
        "一般項目",
        "[ ]無空白",
    ]


def test_ordered_task_items_keep_their_counter_before_the_checkbox(tmp_path: Path) -> None:
    source = _markdown(tmp_path, "1. [ ] 第一步\n2. [x] 第二步\n")

    content = extract_markdown_content(source)

    assert [block.text for block in content.blocks if block.kind is BlockKind.LIST_ITEM] == [
        "1. □ 第一步",
        "2. ☑ 第二步",
    ]
