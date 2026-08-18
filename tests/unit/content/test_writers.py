"""Tests for deterministic Markdown, safe HTML, assets, and annotation sidecars."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from gordon_doc_converter.content.html import render_html
from gordon_doc_converter.content.markdown import render_markdown
from gordon_doc_converter.content.models import (
    BlockKind,
    ContentAsset,
    ContentBlock,
    InlineKind,
    InlineSpan,
    NormalizedContent,
    SourceAnchor,
)
from gordon_doc_converter.content.structured import render_json, render_yaml
from gordon_doc_converter.content.writers import write_content_artifacts
from gordon_doc_converter.models import (
    AnnotationKind,
    ArtifactType,
    NormalizedAnnotation,
    SourceFormat,
)


def _content() -> NormalizedContent:
    return NormalizedContent(
        source_format=SourceFormat.DOCX,
        blocks=(
            ContentBlock(
                BlockKind.HEADING,
                (InlineSpan(InlineKind.TEXT, "臺灣 <安全>："),),
                level=2,
            ),
            ContentBlock(
                BlockKind.PARAGRAPH,
                (
                    InlineSpan(InlineKind.TEXT, "原始 "),
                    InlineSpan(InlineKind.INSERTION, "新增"),
                    InlineSpan(InlineKind.DELETION, "刪除"),
                    InlineSpan(
                        InlineKind.LINK,
                        "危險連結",
                        target="javascript:alert(1)",
                    ),
                    InlineSpan(
                        InlineKind.IMAGE,
                        "插圖",
                        asset_id="asset-0001.png",
                    ),
                    InlineSpan(
                        InlineKind.COMMENT_REFERENCE,
                        annotation_id="comment-0001",
                    ),
                ),
            ),
            ContentBlock(
                BlockKind.LIST_ITEM,
                (InlineSpan(InlineKind.TEXT, "(1) 第一層"),),
                list_level=3,
            ),
            ContentBlock(
                BlockKind.PARAGRAPH,
                (InlineSpan(InlineKind.TEXT, "第一層說明"),),
                list_level=3,
            ),
            ContentBlock(
                BlockKind.LIST_ITEM,
                (InlineSpan(InlineKind.TEXT, "A. 第二層"),),
                list_level=4,
            ),
            ContentBlock(
                BlockKind.TABLE,
                rows=(
                    ((InlineSpan(InlineKind.TEXT, "欄位"),),),
                    ((InlineSpan(InlineKind.TEXT, "值|內容\n第二行"),),),
                ),
            ),
            ContentBlock(BlockKind.PARAGRAPH),
        ),
        assets=(
            ContentAsset(
                asset_id="asset-0001.png",
                filename="asset-0001.png",
                media_type="image/png",
                data=b"generated-image",
            ),
        ),
        annotations=(
            NormalizedAnnotation(
                annotation_id="comment-0001",
                kind=AnnotationKind.COMMENT,
                source_order=0,
                text="公開註解",
            ),
        ),
    )


def test_markdown_is_deterministic_and_preserves_supported_semantics() -> None:
    content = _content()

    first = render_markdown(content, asset_directory="文件.assets")
    second = render_markdown(content, asset_directory="文件.assets")

    assert first == second
    assert "## 臺灣 <安全>\n" in first
    assert "## 臺灣 <安全>：" not in first
    assert "<ins>新增</ins><del>刪除</del>危險連結" in first
    assert "javascript:" not in first
    assert "![插圖](文件.assets/asset-0001.png)" in first
    assert "[^comment-0001]" in first
    assert "值\\|內容<br>第二行" in first
    assert "\n\n\n" not in first
    assert "- (1) 第一層\n\n  第一層說明\n\n  - A\\. 第二層" in first
    assert first.endswith("\n")


def test_html_escapes_content_and_never_emits_active_source_values() -> None:
    rendered = render_html(_content(), asset_directory="文件.assets")

    assert "<h2>臺灣 &lt;安全&gt;：</h2>" in rendered
    assert "<ins>新增</ins><del>刪除</del>危險連結" in rendered
    assert "javascript:" not in rendered
    assert "<script" not in rendered.casefold()
    assert "onerror=" not in rendered.casefold()
    assert 'src="文件.assets/asset-0001.png"' in rendered
    assert "<table>" in rendered
    assert (
        "<ul>\n<li>(1) 第一層\n<p>第一層說明</p>\n<ul>\n<li>A. 第二層\n</li>\n</ul>\n</li>\n</ul>"
    ) in rendered


def test_markdown_normalizes_skipped_word_list_levels_and_tabs() -> None:
    content = NormalizedContent(
        source_format=SourceFormat.DOCX,
        blocks=(
            ContentBlock(
                BlockKind.LIST_ITEM,
                (InlineSpan(InlineKind.TEXT, "(1) 第一層"),),
                list_level=1,
            ),
            ContentBlock(
                BlockKind.LIST_ITEM,
                (InlineSpan(InlineKind.TEXT, "2. 跳層\t項目"),),
                list_level=3,
            ),
        ),
    )

    rendered = render_markdown(content, asset_directory="assets")

    assert rendered == "- (1) 第一層\n  - 2\\. 跳層   項目\n"


def test_json_and_yaml_share_one_versioned_heading_hierarchy() -> None:
    content = NormalizedContent(
        source_format=SourceFormat.DOCX,
        blocks=(
            ContentBlock(
                BlockKind.PARAGRAPH,
                (InlineSpan(InlineKind.TEXT, "前言"),),
            ),
            ContentBlock(
                BlockKind.HEADING,
                (InlineSpan(InlineKind.TEXT, "第一章"),),
                level=1,
            ),
            ContentBlock(
                BlockKind.HEADING,
                (InlineSpan(InlineKind.TEXT, "跳級小節"),),
                level=3,
            ),
            ContentBlock(
                BlockKind.PARAGRAPH,
                (InlineSpan(InlineKind.TEXT, "內容"),),
                page_number=2,
            ),
        ),
    )

    json_payload = json.loads(render_json(content))
    yaml_payload = yaml.safe_load(render_yaml(content))

    assert yaml_payload == json_payload
    assert json_payload["schema_version"] == "1.3"
    assert json_payload["root_blocks"][0]["text"] == "前言"
    chapter = json_payload["sections"][0]
    assert chapter["title"] == "第一章"
    assert chapter["children"][0]["title"] == "跳級小節"
    assert chapter["children"][0]["blocks"][0]["physical_page_number"] == 2
    assert render_json(content) == render_json(content)
    assert render_yaml(content) == render_yaml(content)


def test_structured_content_coalesces_word_runs_and_keeps_semantic_inlines() -> None:
    content = NormalizedContent(
        source_format=SourceFormat.DOCX,
        blocks=(
            ContentBlock(
                BlockKind.PARAGRAPH,
                (
                    InlineSpan(InlineKind.TEXT, "連續"),
                    InlineSpan(InlineKind.TEXT, "文字"),
                ),
            ),
            ContentBlock(
                BlockKind.TABLE,
                rows=(
                    (
                        (
                            InlineSpan(InlineKind.TEXT, "野村臺灣"),
                            InlineSpan(InlineKind.TEXT, "策略高息"),
                            InlineSpan(InlineKind.TEXT, "\n公開說明書"),
                        ),
                    ),
                ),
            ),
            ContentBlock(
                BlockKind.PARAGRAPH,
                (
                    InlineSpan(InlineKind.TEXT, "參考"),
                    InlineSpan(InlineKind.LINK, "網站", target="https://example.test"),
                ),
            ),
        ),
    )

    payload = json.loads(render_json(content))

    paragraph = payload["root_blocks"][0]
    assert paragraph["text"] == "連續文字"
    assert "inlines" not in paragraph
    cell = payload["root_blocks"][1]["rows"][0][0]
    assert cell == {"text": "野村臺灣策略高息\n公開說明書"}
    linked = payload["root_blocks"][2]
    assert linked["text"] == "參考網站"
    assert [span["kind"] for span in linked["inlines"]] == ["text", "link"]


def test_yaml_renders_multiline_text_as_a_readable_literal_block() -> None:
    content = NormalizedContent(
        source_format=SourceFormat.DOCX,
        blocks=(
            ContentBlock(
                BlockKind.PARAGRAPH,
                (InlineSpan(InlineKind.TEXT, "第一行\n第二行\n第三行"),),
            ),
        ),
    )

    rendered = render_yaml(content)

    assert "text: |-\n    第一行\n    第二行\n    第三行\n" in rendered
    assert "第一行\n\n" not in rendered
    assert yaml.safe_load(rendered)["root_blocks"][0]["text"] == "第一行\n第二行\n第三行"


def test_structured_payload_omits_unavailable_optional_values() -> None:
    payload = json.loads(
        render_json(
            NormalizedContent(
                source_format=SourceFormat.DOCX,
                blocks=(
                    ContentBlock(
                        BlockKind.PARAGRAPH,
                        (InlineSpan(InlineKind.TEXT, "內容"),),
                    ),
                ),
            )
        )
    )

    def values(item: object) -> list[object]:
        if isinstance(item, dict):
            return list(item.values()) + [
                nested for value in item.values() for nested in values(value)
            ]
        if isinstance(item, list):
            return [nested for value in item for nested in values(value)]
        return []

    block = payload["root_blocks"][0]
    assert "physical_page_number" not in block
    assert "display_page_label" not in block
    assert "layout" not in payload
    assert "metadata" not in payload
    assert None not in values(payload)


def test_structured_anchors_support_docx_elements_cells_and_pdf_pages() -> None:
    docx = NormalizedContent(
        source_format=SourceFormat.DOCX,
        blocks=(
            ContentBlock(
                BlockKind.TABLE,
                rows=(((InlineSpan(InlineKind.TEXT, "儲存格"),),),),
                source_anchor=SourceAnchor(
                    "ooxml-element",
                    part="word/document.xml",
                    element_path="/w:document/w:body/w:tbl[1]",
                ),
            ),
        ),
        source_sha256="a" * 64,
    )
    pdf = NormalizedContent(
        source_format=SourceFormat.PDF,
        blocks=(
            ContentBlock(
                BlockKind.PARAGRAPH,
                (InlineSpan(InlineKind.TEXT, "頁面文字"),),
                page_number=3,
                source_anchor=SourceAnchor("pdf-page", page_number=3),
            ),
        ),
        source_sha256="b" * 64,
    )

    docx_payload = json.loads(render_json(docx))
    pdf_payload = json.loads(render_json(pdf))

    assert docx_payload["source"]["sha256"] == "a" * 64
    table = docx_payload["root_blocks"][0]
    assert table["source_anchor"]["element_path"].endswith("w:tbl[1]")
    assert table["rows"][0][0]["source_anchor"]["element_path"].endswith("w:tbl[1]/w:tr[1]/w:tc[1]")
    assert len(table["rows"][0][0]["source_anchor"]["content_sha256"]) == 64
    assert pdf_payload["source"]["sha256"] == "b" * 64
    assert pdf_payload["root_blocks"][0]["source_anchor"]["page_number"] == 3


def test_writer_reuses_one_asset_manifest_and_writes_annotation_sidecar(tmp_path: Path) -> None:
    output_stem = tmp_path / "臺灣 文件"

    result = write_content_artifacts(
        _content(),
        output_stem,
        (
            ArtifactType.MARKDOWN,
            ArtifactType.HTML,
            ArtifactType.YAML,
            ArtifactType.JSON,
        ),
    )

    assert tuple(path.suffix for _, path in result.artifacts) == (
        ".md",
        ".html",
        ".yaml",
        ".json",
    )
    yaml_document = yaml.safe_load((tmp_path / "臺灣 文件.yaml").read_text(encoding="utf-8"))
    json_document = json.loads((tmp_path / "臺灣 文件.json").read_text(encoding="utf-8"))
    assert yaml_document == json_document
    asset_directory = result.asset_directory
    assert asset_directory is not None
    assert asset_directory == tmp_path / "臺灣 文件.assets"
    assert result.asset_manifest is not None
    manifest = json.loads(result.asset_manifest.read_text(encoding="utf-8"))
    assert manifest == [
        {
            "asset_id": "asset-0001.png",
            "filename": "asset-0001.png",
            "media_type": "image/png",
            "page_number": None,
            "size_bytes": len(b"generated-image"),
        }
    ]
    assert result.annotation_sidecar is not None
    annotations = json.loads(result.annotation_sidecar.read_text(encoding="utf-8"))
    assert annotations[0]["annotation_id"] == "comment-0001"
    assert (asset_directory / "asset-0001.png").read_bytes() == b"generated-image"


def test_writer_does_not_overwrite_existing_artifact_without_permission(tmp_path: Path) -> None:
    output_stem = tmp_path / "document"
    existing = output_stem.with_suffix(".md")
    existing.write_text("preserve", encoding="utf-8")

    with pytest.raises(FileExistsError):
        write_content_artifacts(_content(), output_stem, (ArtifactType.MARKDOWN,))

    assert existing.read_text(encoding="utf-8") == "preserve"
