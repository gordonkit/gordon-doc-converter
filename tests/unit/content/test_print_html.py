"""Tests for the print-ready HTML intermediate rendered from normalized content."""

from __future__ import annotations

from pathlib import Path

from gordon_doc_converter.content.models import (
    BlockKind,
    ContentAsset,
    ContentBlock,
    DocumentMetadata,
    InlineKind,
    InlineSpan,
    NormalizedContent,
)
from gordon_doc_converter.content.print_html import (
    ASSET_DIRECTORY_NAME,
    DOCUMENT_FILENAME,
    render_print_html,
    write_print_document,
)
from gordon_doc_converter.models import PageOrientation, SourceFormat


def _content(*, assets: tuple[ContentAsset, ...] = ()) -> NormalizedContent:
    blocks: tuple[ContentBlock, ...] = (
        ContentBlock(
            BlockKind.HEADING,
            inlines=(InlineSpan(InlineKind.TEXT, "臺灣報告"),),
            level=1,
        ),
        ContentBlock(BlockKind.PARAGRAPH, inlines=(InlineSpan(InlineKind.TEXT, "內文"),)),
    )
    if assets:
        blocks += (
            ContentBlock(
                BlockKind.PARAGRAPH,
                inlines=(InlineSpan(InlineKind.IMAGE, "圖", asset_id=assets[0].asset_id),),
            ),
        )
    return NormalizedContent(
        source_format=SourceFormat.MARKDOWN,
        blocks=blocks,
        assets=assets,
        metadata=DocumentMetadata(title="臺灣報告", creator="作者", subject="摘要"),
    )


def test_print_html_carries_a4_css_cjk_fonts_and_the_document_language() -> None:
    html = render_print_html(_content(), orientation=PageOrientation.LANDSCAPE)

    assert html.startswith("<!doctype html>")
    assert '<html lang="zh-TW">' in html
    assert '<meta charset="utf-8">' in html
    assert "<title>臺灣報告</title>" in html
    assert '<meta name="author" content="作者">' in html
    assert "size: A4 landscape" in html
    assert "Noto Sans CJK TC" in html
    assert "<h1>臺灣報告</h1>" in html


def test_print_html_defaults_to_portrait_and_a_placeholder_title() -> None:
    content = NormalizedContent(
        source_format=SourceFormat.MARKDOWN,
        blocks=(ContentBlock(BlockKind.PARAGRAPH, inlines=(InlineSpan(InlineKind.TEXT, "hi"),)),),
    )

    html = render_print_html(content)

    assert "size: A4 portrait" in html
    assert "<title>Document</title>" in html
    assert '<html lang="en">' in html


def test_write_print_document_stages_assets_beside_the_document(tmp_path: Path) -> None:
    asset = ContentAsset("image-0001.png", "image-0001.png", "image/png", b"binary")

    document = write_print_document(_content(assets=(asset,)), tmp_path / "intermediate")

    assert document.name == DOCUMENT_FILENAME
    staged = document.parent / ASSET_DIRECTORY_NAME / asset.filename
    assert staged.read_bytes() == b"binary"
    assert f'src="{ASSET_DIRECTORY_NAME}/{asset.filename}"' in document.read_text(encoding="utf-8")
