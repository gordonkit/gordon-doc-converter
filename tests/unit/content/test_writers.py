"""Tests for deterministic Markdown, safe HTML, assets, and annotation sidecars."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gordon_doc_converter.content.html import render_html
from gordon_doc_converter.content.markdown import render_markdown
from gordon_doc_converter.content.models import (
    BlockKind,
    ContentAsset,
    ContentBlock,
    InlineKind,
    InlineSpan,
    NormalizedContent,
)
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
                (InlineSpan(InlineKind.TEXT, "臺灣 <安全>"),),
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
                BlockKind.TABLE,
                rows=(
                    ((InlineSpan(InlineKind.TEXT, "欄位"),),),
                    ((InlineSpan(InlineKind.TEXT, "值|內容"),),),
                ),
            ),
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
    assert "## 臺灣 <安全>" in first
    assert "<ins>新增</ins><del>刪除</del>危險連結" in first
    assert "javascript:" not in first
    assert "![插圖](文件.assets/asset-0001.png)" in first
    assert "[^comment-0001]" in first
    assert "值\\|內容" in first
    assert first.endswith("\n")


def test_html_escapes_content_and_never_emits_active_source_values() -> None:
    rendered = render_html(_content(), asset_directory="文件.assets")

    assert "<h2>臺灣 &lt;安全&gt;</h2>" in rendered
    assert "<ins>新增</ins><del>刪除</del>危險連結" in rendered
    assert "javascript:" not in rendered
    assert "<script" not in rendered.casefold()
    assert "onerror=" not in rendered.casefold()
    assert 'src="文件.assets/asset-0001.png"' in rendered
    assert "<table>" in rendered


def test_writer_reuses_one_asset_manifest_and_writes_annotation_sidecar(tmp_path: Path) -> None:
    output_stem = tmp_path / "臺灣 文件"

    result = write_content_artifacts(
        _content(),
        output_stem,
        (ArtifactType.MARKDOWN, ArtifactType.HTML),
    )

    assert tuple(path.suffix for _, path in result.artifacts) == (".md", ".html")
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
