"""Deterministic Markdown serialization from normalized semantic content."""

from __future__ import annotations

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
    escaped = value.replace("\\", "\\\\")
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
        return f"[{text}]({target})" if target is not None else text
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
            _render_inlines(cell, asset_directory).replace("|", "\\|")
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
    for block in content.blocks:
        if block.kind is BlockKind.TABLE:
            lines.extend(_render_table(block, asset_directory))
        else:
            text = _render_inlines(block.inlines, asset_directory)
            if block.kind is BlockKind.HEADING:
                level = min(max(block.level or 1, 1), 6)
                lines.append(f"{'#' * level} {text}")
            elif block.kind is BlockKind.LIST_ITEM:
                lines.append(f"- {text}")
            else:
                lines.append(text)
        lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + ("\n" if lines else "")
