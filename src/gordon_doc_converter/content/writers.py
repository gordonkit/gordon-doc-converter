"""Atomic writers for semantic content, shared assets, manifests, and annotations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from gordon_doc_converter.content.html import render_html
from gordon_doc_converter.content.markdown import render_markdown
from gordon_doc_converter.content.models import NormalizedContent
from gordon_doc_converter.models import ArtifactType


@dataclass(frozen=True, slots=True)
class ContentWriteResult:
    """Paths written from one normalized extraction pass."""

    artifacts: tuple[tuple[ArtifactType, Path], ...]
    asset_directory: Path | None
    asset_manifest: Path | None
    annotation_sidecar: Path | None


def _write_text(path: Path, text: str, *, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if overwrite else "x"
    with path.open(mode, encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def write_content_artifacts(
    content: NormalizedContent,
    output_stem: Path,
    artifact_types: tuple[ArtifactType, ...],
    *,
    overwrite: bool = False,
) -> ContentWriteResult:
    """Write Markdown/HTML once-extracted content with one deterministic asset manifest."""
    unsupported = set(artifact_types) - {ArtifactType.MARKDOWN, ArtifactType.HTML}
    if unsupported:
        raise ValueError("content writer supports only Markdown and HTML artifacts")
    asset_directory = output_stem.with_name(f"{output_stem.name}.assets")
    relative_asset_directory = asset_directory.name
    if not overwrite:
        planned = [
            output_stem.with_suffix(".md" if item is ArtifactType.MARKDOWN else ".html")
            for item in artifact_types
        ]
        planned.extend(asset_directory / asset.filename for asset in content.assets)
        if content.assets:
            planned.append(asset_directory / "manifest.json")
        if content.annotations:
            planned.append(output_stem.with_name(f"{output_stem.name}.annotations.json"))
        if any(path.exists() for path in planned):
            raise FileExistsError("one or more content outputs already exist")
    artifacts: list[tuple[ArtifactType, Path]] = []
    for artifact_type in artifact_types:
        if artifact_type is ArtifactType.MARKDOWN:
            path = output_stem.with_suffix(".md")
            _write_text(
                path,
                render_markdown(content, asset_directory=relative_asset_directory),
                overwrite=overwrite,
            )
        else:
            path = output_stem.with_suffix(".html")
            _write_text(
                path,
                render_html(content, asset_directory=relative_asset_directory),
                overwrite=overwrite,
            )
        artifacts.append((artifact_type, path))

    manifest_path: Path | None = None
    if content.assets:
        asset_directory.mkdir(parents=True, exist_ok=True)
        manifest: list[dict[str, object]] = []
        for asset in content.assets:
            asset_path = asset_directory / asset.filename
            mode = "wb" if overwrite else "xb"
            with asset_path.open(mode) as stream:
                stream.write(asset.data)
            manifest.append(
                {
                    "asset_id": asset.asset_id,
                    "filename": asset.filename,
                    "media_type": asset.media_type,
                    "page_number": asset.page_number,
                    "size_bytes": len(asset.data),
                }
            )
        manifest_path = asset_directory / "manifest.json"
        _write_text(
            manifest_path,
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            overwrite=overwrite,
        )

    annotation_path: Path | None = None
    if content.annotations:
        annotation_path = output_stem.with_name(f"{output_stem.name}.annotations.json")
        payload = [annotation.to_dict() for annotation in content.annotations]
        _write_text(
            annotation_path,
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            overwrite=overwrite,
        )
    return ContentWriteResult(
        artifacts=tuple(artifacts),
        asset_directory=asset_directory if content.assets else None,
        asset_manifest=manifest_path,
        annotation_sidecar=annotation_path,
    )
