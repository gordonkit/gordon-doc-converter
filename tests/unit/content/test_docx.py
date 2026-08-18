"""Unit tests for direct, non-mutating OOXML content extraction."""

# ruff: noqa: E501 -- OOXML fixture lines intentionally mirror package parts.

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from gordon_doc_converter.content.docx import extract_docx_content
from gordon_doc_converter.content.models import BlockKind, InlineKind
from gordon_doc_converter.models import CommentMode, MetadataDetail, RevisionMode

_CONTENT_TYPES = """<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
</Types>"""
_ROOT_RELS = """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="document" Target="word/document.xml"/>
</Relationships>"""
_DOCUMENT_RELS = """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="link1" Type="hyperlink" Target="https://example.test/a" TargetMode="External"/>
<Relationship Id="image1" Type="image" Target="media/image.png"/>
</Relationships>"""
_DOCUMENT = """<w:document
 xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
<w:body>
 <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>標題</w:t></w:r></w:p>
 <w:p><w:r><w:t>保留</w:t></w:r><w:del w:author="甲" w:date="2026-01-01"><w:r><w:delText>舊字</w:delText></w:r></w:del><w:ins w:author="乙"><w:r><w:t>新字</w:t></w:r></w:ins></w:p>
 <w:p><w:pPr><w:numPr><w:numId w:val="1"/></w:numPr></w:pPr><w:hyperlink r:id="link1"><w:r><w:t>連結</w:t></w:r></w:hyperlink><w:r><w:drawing><a:blip r:embed="image1"/></w:drawing></w:r></w:p>
 <w:p><w:r><w:t>註解</w:t></w:r><w:r><w:commentReference w:id="7"/></w:r></w:p>
 <w:tbl><w:tr><w:tc><w:p><w:r><w:t>欄一</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>欄二</w:t></w:r></w:p></w:tc></w:tr><w:tr><w:tc><w:p><w:r><w:t>資料</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
</w:body></w:document>"""
_COMMENTS = """<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:comment w:id="7" w:author="作者" w:date="2026-02-03"><w:p><w:r><w:t>註解內容</w:t></w:r></w:p></w:comment>
</w:comments>"""
_STYLES = """<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:style w:type="paragraph" w:styleId="chapter"><w:name w:val="章名"/><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="8"/></w:numPr></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="section"><w:name w:val="節名"/><w:basedOn w:val="base"/><w:pPr><w:numPr><w:ilvl w:val="1"/><w:numId w:val="8"/></w:numPr></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="detail"><w:name w:val="小節"/><w:pPr><w:numPr><w:ilvl w:val="2"/><w:numId w:val="9"/></w:numPr></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="base"><w:name w:val="基底"/></w:style>
</w:styles>"""
_NUMBERING = """<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:abstractNum w:abstractNumId="4">
<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="ideographLegalTraditional"/><w:lvlText w:val="第%1章"/></w:lvl>
<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="ideographTraditional"/><w:lvlText w:val="%2、"/></w:lvl>
<w:lvl w:ilvl="2"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%3."/></w:lvl>
</w:abstractNum><w:num w:numId="8"><w:abstractNumId w:val="4"/></w:num><w:num w:numId="9"><w:abstractNumId w:val="4"/></w:num>
</w:numbering>"""
_CORE_PROPERTIES = """<cp:coreProperties
 xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/">
<dc:title>公開報告</dc:title><dc:subject>測試</dc:subject><dc:creator>GordonKit</dc:creator>
<cp:keywords>文件,轉換</cp:keywords><dcterms:created>2026-08-01T00:00:00Z</dcterms:created>
<dcterms:modified>2026-08-02T00:00:00Z</dcterms:modified></cp:coreProperties>"""


def _write_docx(path: Path) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _ROOT_RELS)
        archive.writestr("word/document.xml", _DOCUMENT)
        archive.writestr("word/_rels/document.xml.rels", _DOCUMENT_RELS)
        archive.writestr("word/comments.xml", _COMMENTS)
        archive.writestr("word/media/image.png", b"public-image-data")
        archive.writestr("word/header1.xml", b"<header/>")
        archive.writestr("docProps/core.xml", _CORE_PROPERTIES)


def _write_structured_docx(path: Path) -> None:
    document = """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
<w:sdt><w:sdtContent><w:p><w:r><w:t>封面內容</w:t></w:r></w:p></w:sdtContent></w:sdt>
<w:p><w:pPr><w:pStyle w:val="chapter"/></w:pPr><w:r><w:t>總則</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="section"/></w:pPr><w:r><w:t>範圍</w:t></w:r></w:p>
<w:tbl><w:tr><w:tc><w:p><w:pPr><w:pStyle w:val="section"/></w:pPr><w:r><w:t>表格項目</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
<w:p><w:pPr><w:pStyle w:val="section"/><w:numPr><w:numId w:val="0"/></w:numPr></w:pPr><w:r><w:t>沿用樣式的正文</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="section"/><w:numPr><w:numId w:val="0"/></w:numPr><w:ind w:left="1600"/></w:pPr><w:r><w:t>(1)手動第一層</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="section"/><w:numPr><w:numId w:val="0"/></w:numPr><w:ind w:left="1700"/></w:pPr><w:r><w:t>A.手動第二層</w:t></w:r></w:p>
</w:body></w:document>"""
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _ROOT_RELS)
        archive.writestr("word/document.xml", document)
        archive.writestr("word/styles.xml", _STYLES)
        archive.writestr("word/numbering.xml", _NUMBERING)


def _write_textbox_docx(path: Path) -> None:
    document = """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"><w:body>
<w:p><w:r><mc:AlternateContent>
<mc:Choice Requires="wps"><w:txbxContent><w:p><w:r><w:t>目錄</w:t></w:r></w:p></w:txbxContent></mc:Choice>
<mc:Fallback><w:txbxContent><w:p><w:r><w:t>目錄</w:t></w:r></w:p></w:txbxContent></mc:Fallback>
</mc:AlternateContent></w:r><w:r><w:t>壹、基金概況</w:t><w:tab/><w:t>1</w:t></w:r></w:p>
</w:body></w:document>"""
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _ROOT_RELS)
        archive.writestr("word/document.xml", document)


def _write_restart_docx(path: Path) -> None:
    document = """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
<w:p><w:pPr><w:pStyle w:val="section"/></w:pPr><w:r><w:t>第一節</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="detail"/></w:pPr><w:r><w:t>甲</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="detail"/></w:pPr><w:r><w:t>乙</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="section"/></w:pPr><w:r><w:t>第二節</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="detail"/></w:pPr><w:r><w:t>丙</w:t></w:r></w:p>
</w:body></w:document>"""
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _ROOT_RELS)
        archive.writestr("word/document.xml", document)
        archive.writestr("word/styles.xml", _STYLES)
        archive.writestr("word/numbering.xml", _NUMBERING)


def test_extract_docx_preserves_semantic_blocks_links_images_and_source(tmp_path: Path) -> None:
    source = tmp_path / "繁體 中文.docx"
    _write_docx(source)
    before = source.read_bytes()

    content = extract_docx_content(source)

    assert source.read_bytes() == before
    assert [block.kind for block in content.blocks] == [
        BlockKind.HEADING,
        BlockKind.PARAGRAPH,
        BlockKind.LIST_ITEM,
        BlockKind.PARAGRAPH,
        BlockKind.TABLE,
    ]
    assert content.blocks[0].level == 1
    assert content.source_sha256 is not None
    assert len(content.source_sha256) == 64
    assert content.blocks[0].source_anchor is not None
    assert content.blocks[0].source_anchor.locator == "ooxml-element"
    assert content.blocks[0].source_anchor.part == "word/document.xml"
    assert content.blocks[0].source_anchor.element_path == "/w:document/w:body/w:p[1]"
    assert content.blocks[1].text == "保留新字"
    assert content.blocks[2].inlines[0].kind is InlineKind.LINK
    assert content.blocks[2].inlines[0].target == "https://example.test/a"
    assert content.blocks[2].inlines[1].kind is InlineKind.IMAGE
    assert content.assets[0].filename == "asset-0001.png"
    assert content.assets[0].data == b"public-image-data"
    assert len(content.blocks[-1].rows) == 2
    assert content.blocks[-1].source_anchor is not None
    assert content.blocks[-1].source_anchor.element_path == "/w:document/w:body/w:tbl[1]"
    assert "INCOMPLETE_TABLE_STRUCTURE" in {warning.code for warning in content.warnings}
    assert "HEADER_FOOTER_OMITTED" in {warning.code for warning in content.warnings}


def test_revision_modes_are_deterministic(tmp_path: Path) -> None:
    source = tmp_path / "revisions.docx"
    _write_docx(source)

    final = extract_docx_content(source, revision_mode=RevisionMode.FINAL)
    original = extract_docx_content(source, revision_mode=RevisionMode.ORIGINAL)
    markup = extract_docx_content(source, revision_mode=RevisionMode.MARKUP)

    assert final.blocks[1].text == "保留新字"
    assert original.blocks[1].text == "保留舊字"
    assert markup.blocks[1].text == "保留舊字新字"
    assert [span.kind for span in markup.blocks[1].inlines] == [
        InlineKind.TEXT,
        InlineKind.DELETION,
        InlineKind.INSERTION,
    ]
    assert [annotation.kind.value for annotation in markup.annotations] == [
        "deletion",
        "insertion",
    ]
    assert "INEXACT_REVISION_ANCHOR" in {warning.code for warning in markup.warnings}


def test_comments_and_metadata_are_opt_in(tmp_path: Path) -> None:
    source = tmp_path / "comments.docx"
    _write_docx(source)

    omitted = extract_docx_content(source)
    retained = extract_docx_content(source, comment_mode=CommentMode.MARKUP)
    with_metadata = extract_docx_content(
        source,
        comment_mode=CommentMode.APPENDIX,
        include_annotation_metadata=True,
    )

    assert omitted.annotations == ()
    assert all(
        span.kind is not InlineKind.COMMENT_REFERENCE
        for block in omitted.blocks
        for span in block.inlines
    )
    assert retained.annotations[0].annotation_id == "comment-7"
    assert retained.annotations[0].text == "註解內容"
    assert retained.annotations[0].author is None
    assert retained.annotations[0].anchor.exact is False
    assert with_metadata.annotations[0].author == "作者"
    assert with_metadata.annotations[0].timestamp == "2026-02-03"
    assert "INEXACT_COMMENT_ANCHOR" in {warning.code for warning in retained.warnings}


def test_document_metadata_detail_and_layout_capability_are_explicit(tmp_path: Path) -> None:
    source = tmp_path / "metadata.docx"
    _write_docx(source)

    omitted = extract_docx_content(source, metadata_detail=MetadataDetail.NONE)
    basic = extract_docx_content(source, metadata_detail=MetadataDetail.BASIC)
    layout = extract_docx_content(source, metadata_detail=MetadataDetail.LAYOUT)

    assert omitted.metadata is None
    assert basic.metadata is not None
    assert basic.metadata.title == "公開報告"
    assert basic.metadata.creator == "GordonKit"
    assert basic.layout.availability.value == "not-requested"
    assert layout.layout.availability.value == "unavailable"
    assert "LAYOUT_METADATA_UNAVAILABLE" in {warning.code for warning in layout.warnings}


def test_content_controls_custom_heading_styles_and_chinese_numbering(tmp_path: Path) -> None:
    source = tmp_path / "structured.docx"
    _write_structured_docx(source)

    content = extract_docx_content(source)

    assert [block.kind for block in content.blocks] == [
        BlockKind.PARAGRAPH,
        BlockKind.HEADING,
        BlockKind.HEADING,
        BlockKind.TABLE,
        BlockKind.PARAGRAPH,
        BlockKind.LIST_ITEM,
        BlockKind.LIST_ITEM,
    ]
    assert [block.level for block in content.blocks] == [None, 1, 2, None, None, None, None]
    assert [block.list_level for block in content.blocks] == [None, None, None, None, None, 0, 1]
    assert [block.text for block in content.blocks] == [
        "封面內容",
        "第壹章 總則",
        "一、 範圍",
        "",
        "沿用樣式的正文",
        "(1)手動第一層",
        "A.手動第二層",
    ]
    assert content.blocks[3].rows[0][0][0].text == "二、 "
    assert content.blocks[3].rows[0][0][1].text == "表格項目"


def test_textbox_compatibility_fallback_is_not_duplicated_or_merged(tmp_path: Path) -> None:
    source = tmp_path / "textbox.docx"
    _write_textbox_docx(source)

    content = extract_docx_content(source)

    assert [block.text for block in content.blocks] == ["目錄", "壹、基金概況\t1"]


def test_parent_restarts_child_numbering_across_num_instances(tmp_path: Path) -> None:
    source = tmp_path / "restart.docx"
    _write_restart_docx(source)

    content = extract_docx_content(source)

    assert [block.text for block in content.blocks] == [
        "一、 第一節",
        "1. 甲",
        "2. 乙",
        "二、 第二節",
        "1. 丙",
    ]
