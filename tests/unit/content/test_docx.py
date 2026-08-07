"""Unit tests for direct, non-mutating OOXML content extraction."""

# ruff: noqa: E501 -- OOXML fixture lines intentionally mirror package parts.

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from gordon_doc_converter.content.docx import extract_docx_content
from gordon_doc_converter.content.models import BlockKind, InlineKind
from gordon_doc_converter.models import CommentMode, RevisionMode

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


def _write_docx(path: Path) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _ROOT_RELS)
        archive.writestr("word/document.xml", _DOCUMENT)
        archive.writestr("word/_rels/document.xml.rels", _DOCUMENT_RELS)
        archive.writestr("word/comments.xml", _COMMENTS)
        archive.writestr("word/media/image.png", b"public-image-data")
        archive.writestr("word/header1.xml", b"<header/>")


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
    assert content.blocks[1].text == "保留新字"
    assert content.blocks[2].inlines[0].kind is InlineKind.LINK
    assert content.blocks[2].inlines[0].target == "https://example.test/a"
    assert content.blocks[2].inlines[1].kind is InlineKind.IMAGE
    assert content.assets[0].filename == "asset-0001.png"
    assert content.assets[0].data == b"public-image-data"
    assert len(content.blocks[-1].rows) == 2
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
