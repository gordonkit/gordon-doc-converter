"""Deterministic Markdown serialization from normalized semantic content."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from gordon_doc_converter.content.models import (
    BlockKind,
    ContentBlock,
    InlineKind,
    InlineSpan,
    InlineStyle,
    NormalizedContent,
)

# A decimal counter, but never a decimal fraction such as "1.5".
_ORDERED_MARKER = re.compile(r"^([0-9]{1,3})[.)](?!\d)\s*")
_BACKTICK_RUN = re.compile(r"`+")
_DELIMITERS = {InlineStyle.STRONG: "**", InlineStyle.EMPHASIS: "*"}
# Emphasis is applied inside strong so the strong delimiters stay outermost.
_EMPHASIS_ORDER = (InlineStyle.EMPHASIS, InlineStyle.STRONG)


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


def _code_span(value: str) -> str:
    """Wrap literal text in a code span whose fence never collides with it."""
    body = " ".join(value.split())
    if not body:
        return ""
    longest = max((len(run.group()) for run in _BACKTICK_RUN.finditer(body)), default=0)
    fence = "`" * (longest + 1)
    padding = " " if body.startswith("`") or body.endswith("`") else ""
    return f"{fence}{padding}{body}{padding}{fence}"


def _wrap(value: str, delimiter: str) -> str:
    """Apply an emphasis delimiter, keeping surrounding whitespace outside it."""
    body = value.strip()
    if not body:
        return value
    leading = value[: len(value) - len(value.lstrip())]
    trailing = value[len(value.rstrip()) :]
    return f"{leading}{delimiter}{body}{delimiter}{trailing}"


def _styled(value: str, styles: frozenset[InlineStyle]) -> str:
    """Render inline text with its character formatting, code span innermost."""
    if not value:
        return ""
    rendered = _code_span(value) if InlineStyle.CODE in styles else _escape_text(value)
    for style in _EMPHASIS_ORDER:
        if style in styles:
            rendered = _wrap(rendered, _DELIMITERS[style])
    return rendered


def _render_span(span: InlineSpan, asset_directory: str) -> str:
    text = _styled(span.text, span.styles)
    if span.kind is InlineKind.INSERTION:
        return f"<ins>{text}</ins>"
    if span.kind is InlineKind.DELETION:
        return f"<del>{text}</del>"
    if span.kind is InlineKind.LINK:
        link_text = text.strip()
        if not link_text:
            return ""
        target = _safe_target(span.target)
        return f"[{link_text}]({target})" if target is not None else link_text
    if span.kind is InlineKind.IMAGE:
        alt = _escape_text(span.text)
        if span.asset_id is not None:
            return f"![{alt or 'image'}]({asset_directory}/{span.asset_id})"
        target = _safe_target(span.target)
        if target is not None:
            return f"![{alt or 'image'}]({target})"
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


def _render_code_block(block: ContentBlock) -> list[str]:
    """Render one code block as a fence long enough to contain its body."""
    body = "".join(span.text for span in block.inlines)
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    if not body.strip():
        return []
    longest = max((len(run.group()) for run in _BACKTICK_RUN.finditer(body)), default=0)
    fence = "`" * max(3, longest + 1)
    info = (block.language or "").strip().split(" ", 1)[0]
    return [f"{fence}{info}", *body.rstrip("\n").split("\n"), fence]


def _quoted(lines: list[str], quote_level: int | None) -> list[str]:
    """Prefix one block's rendered lines with its blockquote markers."""
    if not quote_level or quote_level < 1:
        return lines
    prefix = "> " * quote_level
    return [f"{prefix}{line}".rstrip() for line in lines]


def _separator(block: ContentBlock, following: ContentBlock | None) -> str:
    """Return the blank line between blocks, kept inside a continuing quote."""
    level = block.quote_level or 0
    if level < 1 or following is None:
        return ""
    shared = min(level, following.quote_level or 0)
    return ">" * shared


def render_markdown(content: NormalizedContent, *, asset_directory: str) -> str:
    """Serialize normalized blocks into deterministic UTF-8-ready Markdown text."""
    lines: list[str] = []
    list_levels: list[int] = []
    list_indents: list[str] = []
    marker_widths: list[int] = []

    def close_lists() -> None:
        list_levels.clear()
        list_indents.clear()
        marker_widths.clear()

    for index, block in enumerate(content.blocks):
        produced: list[str] = []
        list_continuation = block.kind is BlockKind.PARAGRAPH and block.list_level is not None
        if block.kind is not BlockKind.LIST_ITEM and not list_continuation:
            close_lists()
        if block.kind is BlockKind.THEMATIC_BREAK:
            produced.append("---")
        elif block.kind is BlockKind.CODE_BLOCK:
            produced.extend(_render_code_block(block))
            if not produced:
                continue
        elif block.kind is BlockKind.TABLE:
            produced.extend(_render_table(block, asset_directory))
        else:
            text = _render_inlines(block.inlines, asset_directory)
            if not text.strip():
                continue
            if block.kind is BlockKind.HEADING:
                level = min(max(block.level or 1, 1), 6)
                heading = " ".join(text.split()).rstrip(".,;:!。，；：！？ ")
                produced.append(f"{'#' * level} {heading}")
            elif block.kind is BlockKind.LIST_ITEM:
                level = block.list_level or 0
                while list_levels and level < list_levels[-1]:
                    list_levels.pop()
                    list_indents.pop()
                    marker_widths.pop()
                if not list_levels or level > list_levels[-1]:
                    parent_indent = list_indents[-1] if list_indents else ""
                    parent_width = marker_widths[-1] if marker_widths else 0
                    list_levels.append(level)
                    list_indents.append(parent_indent + " " * parent_width)
                    marker_widths.append(0)
                # An item already numbered by the source becomes an ordered item.
                ordered = _ORDERED_MARKER.match(text)
                if ordered is not None:
                    marker = f"{ordered.group(1)}. "
                    body = text[ordered.end() :]
                else:
                    marker = "- "
                    body = re.sub(r"^([0-9A-Za-z]+)\.(?!\d)", r"\1\\.", text)
                marker_widths[-1] = len(marker)
                produced.append(f"{list_indents[-1]}{marker}{body}")
            else:
                indent = ""
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
                    indent = list_indents[depth] + " " * marker_widths[depth]
                produced.extend(f"{indent}{line.rstrip()}" for line in text.splitlines())
        lines.extend(_quoted(produced, block.quote_level))
        following = content.blocks[index + 1] if index + 1 < len(content.blocks) else None
        next_is_list = following is not None and following.kind is BlockKind.LIST_ITEM
        if block.kind is not BlockKind.LIST_ITEM or not next_is_list:
            lines.append(_separator(block, following))
    while lines and lines[-1] == "":
        lines.pop()
    normalized: list[str] = []
    for line in lines:
        stripped = line.rstrip()
        if stripped or not normalized or normalized[-1] != "":
            normalized.append(stripped)
    return "\n".join(normalized) + ("\n" if normalized else "")
