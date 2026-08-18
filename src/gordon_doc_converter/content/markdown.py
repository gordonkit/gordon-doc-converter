"""Deterministic Markdown serialization from normalized semantic content."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from gordon_doc_converter.content.models import (
    BlockKind,
    ContentBlock,
    InlineKind,
    InlineSpan,
    NormalizedContent,
)


def _safe_target(target: str | None) -> str | None:
    if not target:
        return None
    parsed = urlsplit(target)
    if parsed.scheme.casefold() not in {"", "http", "https", "mailto"}:
        return None
    return target.replace(" ", "%20")


def _escape_text(value: str) -> str:
    escaped = value.expandtabs(4).replace("\\", "\\\\")
    for character in ("*", "_", "`", "[", "]"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


def _render_span(span: InlineSpan, asset_directory: str) -> str:
    text = _escape_text(span.text)
    if span.kind is InlineKind.INSERTION:
        return f"<ins>{text}</ins>"
    if span.kind is InlineKind.DELETION:
        return f"<del>{text}</del>"
    if span.kind is InlineKind.LINK:
        target = _safe_target(span.target)
        link_text = text.strip()
        if not link_text:
            return ""
        return f"[{link_text}]({target})" if target is not None else link_text
    if span.kind is InlineKind.IMAGE and span.asset_id is not None:
        return f"![{text or 'image'}]({asset_directory}/{span.asset_id})"
    if span.kind is InlineKind.COMMENT_REFERENCE and span.annotation_id is not None:
        return f"[^{span.annotation_id}]"
    return text


def _render_inlines(inlines: tuple[InlineSpan, ...], asset_directory: str) -> str:
    return "".join(_render_span(span, asset_directory) for span in inlines)


def _render_table(block: ContentBlock, asset_directory: str) -> list[str]:
    if not block.rows:
        return []
    width = max(len(row) for row in block.rows)
    rows = [
        [
            "<br>".join(
                line.strip()
                for line in _render_inlines(cell, asset_directory)
                .replace("\r\n", "\n")
                .replace("\r", "\n")
                .split("\n")
                if line.strip()
            ).replace("|", "\\|")
            for cell in row + ((),) * (width - len(row))
        ]
        for row in block.rows
    ]
    header = rows[0]
    lines = [f"| {' | '.join(header)} |", f"| {' | '.join(['---'] * width)} |"]
    lines.extend(f"| {' | '.join(row)} |" for row in rows[1:])
    return lines


def render_markdown(content: NormalizedContent, *, asset_directory: str) -> str:
    """Serialize normalized blocks into deterministic UTF-8-ready Markdown text."""
    lines: list[str] = []
    list_levels: list[int] = []
    for index, block in enumerate(content.blocks):
        list_continuation = block.kind is BlockKind.PARAGRAPH and block.list_level is not None
        if block.kind is not BlockKind.LIST_ITEM and not list_continuation:
            list_levels.clear()
        if block.kind is BlockKind.TABLE:
            lines.extend(_render_table(block, asset_directory))
        else:
            text = _render_inlines(block.inlines, asset_directory)
            if not text.strip():
                continue
            if block.kind is BlockKind.HEADING:
                level = min(max(block.level or 1, 1), 6)
                heading = " ".join(text.split()).rstrip(".,;:!。，；：！？ ")
                lines.append(f"{'#' * level} {heading}")
            elif block.kind is BlockKind.LIST_ITEM:
                level = block.list_level or 0
                while list_levels and level < list_levels[-1]:
                    list_levels.pop()
                if not list_levels or level > list_levels[-1]:
                    list_levels.append(level)
                depth = len(list_levels) - 1
                text = re.sub(r"^([0-9A-Za-z]+)\.", r"\1\\.", text)
                lines.append(f"{'  ' * depth}- {text}")
            else:
                depth = 0
                if block.list_level is not None and list_levels:
                    depth = max(
                        next(
                            (
                                position
                                for position, level in enumerate(list_levels)
                                if level == block.list_level
                            ),
                            len(list_levels) - 1,
                        ),
                        0,
                    )
                indent = "  " * (depth + 1) if block.list_level is not None else ""
                lines.append("\n".join(f"{indent}{line.rstrip()}" for line in text.splitlines()))
        next_is_list = (
            index + 1 < len(content.blocks)
            and content.blocks[index + 1].kind is BlockKind.LIST_ITEM
        )
        if block.kind is not BlockKind.LIST_ITEM or not next_is_list:
            lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    normalized: list[str] = []
    for line in lines:
        stripped = line.rstrip()
        if stripped or not normalized or normalized[-1] != "":
            normalized.append(stripped)
    return "\n".join(normalized) + ("\n" if normalized else "")
