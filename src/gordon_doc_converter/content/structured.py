"""Versioned hierarchical JSON and YAML serialization for semantic content."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Any

import yaml

from gordon_doc_converter.content.models import (
    ContentBlock,
    InlineSpan,
    LayoutAvailability,
    NormalizedContent,
    SourceAnchor,
)

SCHEMA_VERSION = "1.3"


class _ReadableSafeDumper(yaml.SafeDumper):
    """Safe YAML dumper that renders multiline text as readable literal blocks."""


def _represent_string(dumper: yaml.SafeDumper, value: str) -> yaml.nodes.ScalarNode:
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_ReadableSafeDumper.add_representer(str, _represent_string)


def _inline_payload(span: InlineSpan) -> dict[str, object]:
    payload: dict[str, object] = {"kind": span.kind.value, "text": span.text}
    if span.target is not None:
        payload["target"] = span.target
    if span.asset_id is not None:
        payload["asset_id"] = span.asset_id
    if span.annotation_id is not None:
        payload["annotation_id"] = span.annotation_id
    return payload


def _coalesce_spans(spans: tuple[InlineSpan, ...]) -> tuple[InlineSpan, ...]:
    coalesced: list[InlineSpan] = []
    for span in spans:
        if not span.text and span.asset_id is None and span.annotation_id is None:
            continue
        if coalesced:
            previous = coalesced[-1]
            if (
                previous.kind is span.kind
                and previous.target == span.target
                and previous.asset_id == span.asset_id
                and previous.annotation_id == span.annotation_id
            ):
                coalesced[-1] = InlineSpan(
                    previous.kind,
                    previous.text + span.text,
                    previous.target,
                    previous.asset_id,
                    previous.annotation_id,
                )
                continue
        coalesced.append(span)
    return tuple(coalesced)


def _content_payload(spans: tuple[InlineSpan, ...]) -> dict[str, object]:
    normalized = _coalesce_spans(spans)
    payload: dict[str, object] = {"text": "".join(span.text for span in normalized)}
    if normalized and (len(normalized) != 1 or normalized[0].kind.value != "text"):
        payload["inlines"] = [_inline_payload(span) for span in normalized]
    return payload


def _source_anchor_payload(anchor: SourceAnchor, text: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "locator": anchor.locator,
        "content_sha256": sha256(text.encode("utf-8")).hexdigest(),
    }
    if anchor.part is not None:
        payload["part"] = anchor.part
    if anchor.element_path is not None:
        payload["element_path"] = anchor.element_path
    if anchor.native_id is not None:
        payload["native_id"] = anchor.native_id
    if anchor.page_number is not None:
        payload["page_number"] = anchor.page_number
    return payload


def _table_text(block: ContentBlock) -> str:
    return "\n".join(
        "\t".join("".join(span.text for span in cell) for cell in row) for row in block.rows
    )


def _cell_payload(
    cell: tuple[InlineSpan, ...],
    block_anchor: SourceAnchor | None,
    row_number: int,
    cell_number: int,
) -> dict[str, object]:
    payload = _content_payload(cell)
    if (
        block_anchor is not None
        and block_anchor.locator == "ooxml-element"
        and block_anchor.element_path is not None
    ):
        cell_anchor = SourceAnchor(
            "ooxml-table-cell",
            part=block_anchor.part,
            element_path=(f"{block_anchor.element_path}/w:tr[{row_number}]/w:tc[{cell_number}]"),
        )
        text = payload["text"]
        assert isinstance(text, str)
        payload["source_anchor"] = _source_anchor_payload(cell_anchor, text)
    return payload


def _block_payload(block: ContentBlock, source_order: int) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": f"block-{source_order + 1:06d}",
        "source_order": source_order,
        "kind": block.kind.value,
    }
    if block.page_number is not None:
        payload["physical_page_number"] = block.page_number
    if block.display_page_label is not None:
        payload["display_page_label"] = block.display_page_label
    payload.update(_content_payload(block.inlines))
    if block.source_anchor is not None:
        anchor_text = _table_text(block) if block.rows else block.text
        payload["source_anchor"] = _source_anchor_payload(block.source_anchor, anchor_text)
    if block.list_level is not None:
        payload["list_level"] = block.list_level
    if block.rows:
        payload["rows"] = [
            [
                _cell_payload(cell, block.source_anchor, row_number, cell_number)
                for cell_number, cell in enumerate(row, start=1)
            ]
            for row_number, row in enumerate(block.rows, start=1)
        ]
    return payload


def build_structured_payload(content: NormalizedContent) -> dict[str, object]:
    """Build one source-neutral hierarchy shared by JSON and YAML writers."""
    root_blocks: list[dict[str, object]] = []
    sections: list[dict[str, object]] = []
    section_stack: list[dict[str, object]] = []

    for source_order, block in enumerate(content.blocks):
        if block.level is None:
            target = section_stack[-1]["blocks"] if section_stack else root_blocks
            assert isinstance(target, list)
            target.append(_block_payload(block, source_order))
            continue

        section: dict[str, object] = {
            "id": f"section-{source_order + 1:06d}",
            "source_order": source_order,
            "level": block.level,
            "title": block.text,
            "blocks": [],
            "children": [],
        }
        if block.page_number is not None:
            section["physical_page_number"] = block.page_number
        if block.display_page_label is not None:
            section["display_page_label"] = block.display_page_label
        if block.source_anchor is not None:
            section["source_anchor"] = _source_anchor_payload(block.source_anchor, block.text)
        while section_stack:
            parent_level = section_stack[-1]["level"]
            assert isinstance(parent_level, int)
            if parent_level < block.level:
                break
            section_stack.pop()
        target_sections = section_stack[-1]["children"] if section_stack else sections
        assert isinstance(target_sections, list)
        target_sections.append(section)
        section_stack.append(section)

    metadata: dict[str, object] | None = None
    if content.metadata is not None:
        metadata = {
            key: value
            for key, value in {
                "title": content.metadata.title,
                "subject": content.metadata.subject,
                "creator": content.metadata.creator,
                "keywords": content.metadata.keywords,
                "created": content.metadata.created,
                "modified": content.metadata.modified,
            }.items()
            if value is not None
        }

    source: dict[str, object] = {"format": content.source_format.value}
    if content.source_sha256 is not None:
        source["sha256"] = content.source_sha256
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "source": source,
        "root_blocks": root_blocks,
        "sections": sections,
        "assets": [],
        "annotations": [annotation.to_dict() for annotation in content.annotations],
        "warnings": [warning.to_dict() for warning in content.warnings],
    }
    if metadata:
        payload["metadata"] = metadata
    if content.layout.availability is not LayoutAvailability.NOT_REQUESTED:
        layout: dict[str, object] = {"availability": content.layout.availability.value}
        if content.layout.provider is not None:
            layout["provider"] = content.layout.provider
        if content.layout.confidence is not None:
            layout["confidence"] = content.layout.confidence
        if content.layout.availability is LayoutAvailability.AVAILABLE:
            layout["physical_page_number_base"] = 1
        payload["layout"] = layout
    assets = payload["assets"]
    assert isinstance(assets, list)
    for asset in content.assets:
        asset_payload: dict[str, object] = {
            "asset_id": asset.asset_id,
            "filename": asset.filename,
            "media_type": asset.media_type,
            "size_bytes": len(asset.data),
        }
        if asset.page_number is not None:
            asset_payload["physical_page_number"] = asset.page_number
        assets.append(asset_payload)
    return payload


def render_json(content: NormalizedContent) -> str:
    """Serialize hierarchical content as deterministic UTF-8-ready JSON."""
    return (
        json.dumps(
            build_structured_payload(content),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def render_yaml(content: NormalizedContent) -> str:
    """Serialize hierarchical content as safe deterministic YAML."""
    payload: Any = build_structured_payload(content)
    return yaml.dump(
        payload,
        Dumper=_ReadableSafeDumper,
        allow_unicode=True,
        sort_keys=False,
    )
