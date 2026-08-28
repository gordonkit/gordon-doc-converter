"""Unit tests for direct, non-mutating ODF content extraction."""

# ruff: noqa: E501 -- ODF fixture lines intentionally mirror package parts.

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from gordon_doc_converter.content.models import BlockKind, InlineKind
from gordon_doc_converter.content.odt import extract_odt_content
from gordon_doc_converter.exceptions import InvalidInputError
from gordon_doc_converter.models import (
    AnnotationKind,
    CommentMode,
    MetadataDetail,
    RevisionMode,
)

_AUTOMATIC_STYLES = """<office:automatic-styles>
 <text:list-style style:name="L1">
  <text:list-level-style-number text:level="1" style:num-format="一" style:num-prefix="第" style:num-suffix="項"/>
  <text:list-level-style-number text:level="2" style:num-format="1" text:display-levels="2" style:num-suffix="."/>
 </text:list-style>
 <text:list-style style:name="LB">
  <text:list-level-style-bullet text:level="1" text:bullet-char="•"/>
 </text:list-style>
</office:automatic-styles>"""
_BODY = """
 <text:tracked-changes>
  <text:changed-region text:id="ct1"><text:deletion>
   <office:change-info><dc:creator>甲</dc:creator><dc:date>2026-01-01T00:00:00</dc:date><text:p>刪除理由</text:p></office:change-info>
   <text:p>舊字</text:p>
  </text:deletion></text:changed-region>
  <text:changed-region text:id="ct2"><text:insertion>
   <office:change-info><dc:creator>乙</dc:creator><dc:date>2026-01-02T00:00:00</dc:date></office:change-info>
  </text:insertion></text:changed-region>
 </text:tracked-changes>
 <text:h text:outline-level="1">總則</text:h>
 <text:p>保留<text:change text:change-id="ct1"/><text:change-start text:change-id="ct2"/>新字<text:change-end text:change-id="ct2"/>。</text:p>
 <text:h text:outline-level="2">範圍</text:h>
 <text:p>參見<text:a xlink:href="https://example.test/a">連結</text:a>與圖<draw:frame><svg:desc>標誌</svg:desc><draw:image xlink:href="Pictures/logo.png"/></draw:frame>。</text:p>
 <text:p>註解<office:annotation office:name="cm1"><dc:creator>作者</dc:creator><dc:date>2026-02-03</dc:date><text:p>註解內容</text:p></office:annotation></text:p>
 <text:list text:style-name="L1">
  <text:list-item><text:p>第一項內容</text:p>
   <text:list><text:list-item><text:p>子項甲</text:p></text:list-item>
    <text:list-item><text:p>子項乙</text:p></text:list-item></text:list>
  </text:list-item>
  <text:list-item><text:p>第二項內容</text:p><text:p>同項續行</text:p></text:list-item>
 </text:list>
 <text:list text:style-name="LB"><text:list-item><text:p>符號項</text:p></text:list-item></text:list>
 <table:table><table:table-row>
   <table:table-cell><text:p>欄一</text:p></table:table-cell>
   <table:table-cell><text:p>欄二</text:p></table:table-cell>
  </table:table-row><table:table-row>
   <table:table-cell><text:p>資料</text:p></table:table-cell>
   <table:table-cell><text:p>值</text:p></table:table-cell>
  </table:table-row></table:table>
 <text:p>製表<text:tab/>完成<text:line-break/>換行<text:s text:c="2"/>結束</text:p>
"""
_STYLES = """<office:styles>
 <style:style style:name="Heading_20_1" style:display-name="Heading 1" style:family="paragraph" style:default-outline-level="1"/>
 <text:outline-style style:name="Outline">
  <text:outline-level-style text:level="1" style:num-format="壹" style:num-suffix="、"/>
  <text:outline-level-style text:level="2" style:num-format="1" style:num-suffix="."/>
 </text:outline-style>
</office:styles>
<office:master-styles><style:master-page style:name="Standard">
 <style:header><text:p>頁首</text:p></style:header>
</style:master-page></office:master-styles>"""
_META = """<office:meta>
<dc:title>公開報告</dc:title><dc:subject>測試</dc:subject><meta:initial-creator>GordonKit</meta:initial-creator>
<meta:keyword>文件</meta:keyword><meta:keyword>轉換</meta:keyword>
<meta:creation-date>2026-08-01T00:00:00</meta:creation-date><dc:date>2026-08-02T00:00:00</dc:date>
</office:meta>"""
_PNG = b"public-image-data"


@pytest.fixture
def report(tmp_path: Path, write_odt: Callable[..., Path]) -> Path:
    """Build one ODT covering headings, lists, tables, revisions, and annotations."""
    return write_odt(
        tmp_path / "報告.odt",
        _BODY,
        styles_xml=_AUTOMATIC_STYLES,
        document_styles=_STYLES,
        document_meta=_META,
        parts={"Pictures/logo.png": _PNG},
    )


def test_extraction_normalizes_headings_links_images_and_tables(report: Path) -> None:
    content = extract_odt_content(report)

    headings = [block for block in content.blocks if block.kind is BlockKind.HEADING]
    assert [block.level for block in headings] == [1, 2]
    assert headings[0].text == "壹、 總則"
    assert headings[1].text == "1. 範圍"
    link = next(
        span for block in content.blocks for span in block.inlines if span.kind is InlineKind.LINK
    )
    assert (link.text, link.target) == ("連結", "https://example.test/a")
    image = next(
        span for block in content.blocks for span in block.inlines if span.kind is InlineKind.IMAGE
    )
    assert image.text == "標誌"
    assert content.assets[0].media_type == "image/png"
    assert content.assets[0].data == _PNG
    table = next(block for block in content.blocks if block.kind is BlockKind.TABLE)
    assert [[cell[0].text for cell in row] for row in table.rows] == [
        ["欄一", "欄二"],
        ["資料", "值"],
    ]
    assert content.source_sha256 is not None


def test_list_markers_follow_nesting_display_levels_and_bullet_styles(report: Path) -> None:
    content = extract_odt_content(report)

    items = [block for block in content.blocks if block.kind is BlockKind.LIST_ITEM]
    assert [(block.list_level, block.text) for block in items] == [
        (0, "第一項 第一項內容"),
        (1, "一.1. 子項甲"),
        (1, "一.2. 子項乙"),
        (0, "第二項 第二項內容"),
        (0, "符號項"),
    ]
    continuation = next(
        block
        for block in content.blocks
        if block.kind is BlockKind.PARAGRAPH and block.text == "同項續行"
    )
    assert continuation.list_level == 0


def test_inline_whitespace_elements_become_literal_characters(report: Path) -> None:
    content = extract_odt_content(report)

    assert content.blocks[-1].text == "製表\t完成\n換行  結束"


def test_final_revisions_keep_insertions_and_drop_deletions(report: Path) -> None:
    content = extract_odt_content(report)

    paragraph = next(block for block in content.blocks if block.text.startswith("保留"))
    assert paragraph.text == "保留新字。"
    assert content.annotations == ()


def test_original_revisions_restore_deletions_and_drop_insertions(report: Path) -> None:
    content = extract_odt_content(report, revision_mode=RevisionMode.ORIGINAL)

    paragraph = next(block for block in content.blocks if block.text.startswith("保留"))
    assert paragraph.text == "保留舊字。"


def test_markup_revisions_mark_both_sides_and_record_annotations(report: Path) -> None:
    content = extract_odt_content(
        report,
        revision_mode=RevisionMode.MARKUP,
        comment_mode=CommentMode.MARKUP,
        include_annotation_metadata=True,
    )

    paragraph = next(block for block in content.blocks if block.text.startswith("保留"))
    assert [(span.kind, span.text) for span in paragraph.inlines] == [
        (InlineKind.TEXT, "保留"),
        (InlineKind.DELETION, "舊字"),
        (InlineKind.INSERTION, "新字"),
        (InlineKind.TEXT, "。"),
    ]
    deletion, insertion, comment = content.annotations
    assert [item.kind for item in content.annotations] == [
        AnnotationKind.DELETION,
        AnnotationKind.INSERTION,
        AnnotationKind.COMMENT,
    ]
    assert (deletion.text, deletion.author) == ("舊字", "甲")
    assert insertion.author == "乙"
    assert (comment.annotation_id, comment.text, comment.author) == ("cm1", "註解內容", "作者")
    assert {warning.code for warning in content.warnings} >= {
        "INEXACT_REVISION_ANCHOR",
        "INEXACT_COMMENT_ANCHOR",
    }


def test_omitted_comments_leave_no_reference_or_annotation(report: Path) -> None:
    content = extract_odt_content(report)

    assert content.annotations == ()
    assert all(
        span.kind is not InlineKind.COMMENT_REFERENCE
        for block in content.blocks
        for span in block.inlines
    )


def test_metadata_and_header_warnings_come_from_the_package_parts(report: Path) -> None:
    content = extract_odt_content(report)

    assert content.metadata is not None
    assert content.metadata.title == "公開報告"
    assert content.metadata.creator == "GordonKit"
    assert content.metadata.keywords == "文件, 轉換"
    assert content.metadata.created == "2026-08-01T00:00:00"
    assert content.metadata.modified == "2026-08-02T00:00:00"
    assert "HEADER_FOOTER_OMITTED" in {warning.code for warning in content.warnings}


def test_metadata_detail_none_omits_document_properties(report: Path) -> None:
    content = extract_odt_content(report, metadata_detail=MetadataDetail.NONE)

    assert content.metadata is None


def test_layout_detail_reports_unavailable_layout_metadata(report: Path) -> None:
    content = extract_odt_content(report, metadata_detail=MetadataDetail.LAYOUT)

    assert content.layout.availability.value == "unavailable"
    assert "LAYOUT_METADATA_UNAVAILABLE" in {warning.code for warning in content.warnings}


def test_source_anchors_locate_blocks_inside_the_content_part(report: Path) -> None:
    content = extract_odt_content(report)

    anchor = content.blocks[0].source_anchor
    assert anchor is not None
    assert anchor.locator == "odf-element"
    assert anchor.part == "content.xml"
    assert anchor.element_path == "/office:document-content/office:body/text:h[1]"


def test_sections_and_text_boxes_keep_their_blocks_in_reading_order(
    tmp_path: Path, write_odt: Callable[..., Path]
) -> None:
    body = """<text:p><draw:frame><draw:text-box><text:p>目錄</text:p></draw:text-box></draw:frame>壹、基金概況</text:p>
 <text:section text:name="S1"><text:p>章節內容</text:p></text:section>"""

    content = extract_odt_content(write_odt(tmp_path / "區段.odt", body))

    assert [block.text for block in content.blocks] == ["目錄", "壹、基金概況", "章節內容"]


def test_uneven_and_merged_table_cells_raise_a_structure_warning(
    tmp_path: Path, write_odt: Callable[..., Path]
) -> None:
    body = """<table:table><table:table-row>
  <table:table-cell table:number-columns-repeated="2"><text:p>合併</text:p></table:table-cell>
 </table:table-row><table:table-row>
  <table:table-cell table:number-rows-spanned="2"><text:p>跨列</text:p></table:table-cell>
  <table:covered-table-cell/>
 </table:table-row></table:table>"""

    content = extract_odt_content(write_odt(tmp_path / "表格.odt", body))

    table = content.blocks[0]
    assert [len(row) for row in table.rows] == [2, 2]
    assert table.rows[0][1][0].text == "合併"
    assert "INCOMPLETE_TABLE_STRUCTURE" in {warning.code for warning in content.warnings}


def test_footnote_bodies_leave_the_reading_order_with_a_warning(
    tmp_path: Path, write_odt: Callable[..., Path]
) -> None:
    body = """<text:p>正文<text:note text:note-class="footnote"><text:note-citation>1</text:note-citation><text:note-body><text:p>註腳內容</text:p></text:note-body></text:note>結尾</text:p>"""

    content = extract_odt_content(write_odt(tmp_path / "註腳.odt", body))

    assert content.blocks[0].text == "正文1結尾"
    assert "NOTE_BODY_OMITTED" in {warning.code for warning in content.warnings}


def test_images_outside_the_package_warn_instead_of_embedding(
    tmp_path: Path, write_odt: Callable[..., Path]
) -> None:
    body = """<text:p><draw:frame><draw:image xlink:href="https://example.test/logo.png"/></draw:frame></text:p>"""

    content = extract_odt_content(write_odt(tmp_path / "外連.odt", body))

    assert content.assets == ()
    assert "ODT_IMAGE_UNAVAILABLE" in {warning.code for warning in content.warnings}


def test_paragraph_styles_named_like_headings_become_headings(
    tmp_path: Path, write_odt: Callable[..., Path]
) -> None:
    styles = """<office:automatic-styles>
 <style:style style:name="P1" style:family="paragraph" style:parent-style-name="Heading_20_2"/>
 <style:style style:name="Heading_20_2" style:display-name="Heading 2" style:family="paragraph" style:default-outline-level="2"/>
</office:automatic-styles>"""
    body = """<text:p text:style-name="P1">衍生標題</text:p>
 <text:p text:style-name="Standard">一般段落</text:p>"""

    content = extract_odt_content(write_odt(tmp_path / "樣式.odt", body, styles_xml=styles))

    assert [(block.kind, block.level) for block in content.blocks] == [
        (BlockKind.HEADING, 2),
        (BlockKind.PARAGRAPH, None),
    ]


def test_continued_lists_keep_counting_across_separate_list_elements(
    tmp_path: Path, write_odt: Callable[..., Path]
) -> None:
    styles = """<office:automatic-styles><text:list-style style:name="LN">
 <text:list-level-style-number text:level="1" style:num-format="1" style:num-suffix="."/>
</text:list-style></office:automatic-styles>"""
    body = """<text:list text:style-name="LN"><text:list-item><text:p>甲</text:p></text:list-item></text:list>
 <text:list text:style-name="LN" text:continue-numbering="true"><text:list-item><text:p>乙</text:p></text:list-item></text:list>
 <text:list text:style-name="LN"><text:list-item><text:p>丙</text:p></text:list-item></text:list>"""

    content = extract_odt_content(write_odt(tmp_path / "接續.odt", body, styles_xml=styles))

    assert [block.text for block in content.blocks] == ["1. 甲", "2. 乙", "1. 丙"]


def test_a_package_without_a_text_body_is_rejected(
    tmp_path: Path, write_odt: Callable[..., Path]
) -> None:
    content_xml = (
        "<office:document-content"
        ' xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0">'
        "<office:body/></office:document-content>"
    )

    with pytest.raises(InvalidInputError, match="no text body"):
        extract_odt_content(write_odt(tmp_path / "空白包.odt", content_xml=content_xml))
