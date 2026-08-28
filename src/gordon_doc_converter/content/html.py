"""Safe deterministic semantic HTML serialization."""

from __future__ import annotations

from html import escape
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
    return target


def _render_span(span: InlineSpan, asset_directory: str) -> str:
    text = escape(span.text)
    if span.kind is InlineKind.INSERTION:
        return f"<ins>{text}</ins>"
    if span.kind is InlineKind.DELETION:
        return f"<del>{text}</del>"
    if span.kind is InlineKind.LINK:
        target = _safe_target(span.target)
        return f'<a href="{escape(target, quote=True)}">{text}</a>' if target else text
    if span.kind is InlineKind.IMAGE:
        reference = (
            f"{asset_directory}/{span.asset_id}"
            if span.asset_id is not None
            else _safe_target(span.target)
        )
        if reference is not None:
            source = escape(reference, quote=True)
            return f'<img src="{source}" alt="{escape(span.text, quote=True)}">'
    if span.kind is InlineKind.COMMENT_REFERENCE and span.annotation_id is not None:
        identifier = escape(span.annotation_id, quote=True)
        return f'<sup><a href="#annotation-{identifier}">[{identifier}]</a></sup>'
    return text


def _render_inlines(inlines: tuple[InlineSpan, ...], asset_directory: str) -> str:
    return "".join(_render_span(span, asset_directory) for span in inlines)


def _block_data_attributes(block: ContentBlock) -> str:
    """Return data-* attributes for source traceability."""
    attributes: list[str] = []
    if block.source_anchor is not None:
        attributes.append(f'data-locator="{escape(block.source_anchor.locator, quote=True)}"')
        if block.source_anchor.native_id is not None:
            attributes.append(f'data-id="{escape(block.source_anchor.native_id, quote=True)}"')
    if block.page_number is not None:
        attributes.append(f'data-page="{block.page_number}"')
    return (" " + " ".join(attributes)) if attributes else ""


def _render_table(block: ContentBlock, asset_directory: str) -> list[str]:
    """Render a table with proper thead/tbody separation."""
    if not block.rows:
        return []
    lines: list[str] = []
    attrs = _block_data_attributes(block)
    lines.append(f"<table{attrs}>")
    for row_index, row in enumerate(block.rows):
        if row_index == 0:
            lines.append("<thead>")
            lines.append("<tr>")
            lines.extend(f"<th>{_render_inlines(cell, asset_directory)}</th>" for cell in row)
            lines.append("</tr>")
            lines.append("</thead>")
            lines.append("<tbody>")
        else:
            lines.append("<tr>")
            lines.extend(f"<td>{_render_inlines(cell, asset_directory)}</td>" for cell in row)
            lines.append("</tr>")
    if block.rows:
        lines.append("</tbody>")
    lines.append("</table>")
    return lines


def _render_metadata(content: NormalizedContent) -> list[str]:
    """Render document metadata as a <header> element."""
    if content.metadata is None:
        return []
    metadata = content.metadata
    if not any((metadata.title, metadata.subject, metadata.creator, metadata.keywords)):
        return []
    lines: list[str] = ["<header>"]
    if metadata.title:
        lines.append(f"<h1>{escape(metadata.title)}</h1>")
    meta_parts: list[str] = []
    if metadata.subject:
        meta_parts.append(f"<p><em>{escape(metadata.subject)}</em></p>")
    if metadata.creator:
        meta_parts.append(f"<p>{escape(metadata.creator)}</p>")
    if metadata.keywords:
        meta_parts.append(f"<p>{escape(metadata.keywords)}</p>")
    lines.extend(meta_parts)
    lines.append("</header>")
    return lines


def _has_content(block: ContentBlock) -> bool:
    """Check if a block has renderable content."""
    if block.rows:
        return True
    text = block.text.strip()
    return bool(text)


def _render_list_items(
    blocks: tuple[ContentBlock, ...],
    start_index: int,
    asset_directory: str,
) -> tuple[list[str], int]:
    """Render a contiguous run of list items and continuation paragraphs."""
    lines: list[str] = []
    index = start_index
    base_level = blocks[index].list_level or 0
    current_level = base_level
    lines.append("<ul>")

    while index < len(blocks):
        block = blocks[index]

        if block.kind is BlockKind.LIST_ITEM:
            level = block.list_level or 0
            text = _render_inlines(block.inlines, asset_directory)
            attrs = _block_data_attributes(block)

            if level > current_level:
                while current_level < level:
                    lines.append("<ul>")
                    current_level += 1
            elif level < current_level:
                lines.append("</li>")
                while current_level > level:
                    lines.append("</ul>")
                    current_level -= 1
                lines.append("</li>")
            else:
                if index > start_index:
                    lines.append("</li>")

            lines.append(f"<li{attrs}>{text}")
            index += 1

        elif block.kind is BlockKind.PARAGRAPH and block.list_level is not None:
            text = _render_inlines(block.inlines, asset_directory)
            if text.strip():
                lines.append(f"<p>{text}</p>")
            index += 1

        else:
            break

    lines.append("</li>")
    exit_depth = current_level
    while current_level > base_level:
        lines.append("</ul>")
        current_level -= 1
        if current_level > base_level:
            lines.append("</li>")
    if exit_depth > base_level:
        lines.append("</li>")
    lines.append("</ul>")
    return lines, index


def render_html(content: NormalizedContent, *, asset_directory: str) -> str:
    """Serialize normalized blocks to structured semantic HTML."""
    head_lines: list[str] = []
    if content.metadata and content.metadata.title:
        head_lines.append(f"<title>{escape(content.metadata.title)}</title>")
    head = "\n".join(head_lines)
    head_section = f"<head>\n{head}\n</head>\n" if head_lines else ""

    body: list[str] = []
    body.extend(_render_metadata(content))

    index = 0
    blocks = content.blocks
    while index < len(blocks):
        block = blocks[index]

        if not _has_content(block):
            index += 1
            continue

        if block.kind is BlockKind.HEADING:
            level = min(max(block.level or 1, 1), 6)
            attrs = _block_data_attributes(block)
            body.append(
                f"<h{level}{attrs}>{_render_inlines(block.inlines, asset_directory)}</h{level}>"
            )
            index += 1

        elif block.kind is BlockKind.LIST_ITEM:
            list_lines, index = _render_list_items(blocks, index, asset_directory)
            body.extend(list_lines)

        elif block.kind is BlockKind.TABLE:
            body.extend(_render_table(block, asset_directory))
            index += 1

        elif block.kind is BlockKind.PARAGRAPH and block.list_level is not None:
            index += 1

        else:
            attrs = _block_data_attributes(block)
            body.append(f"<p{attrs}>{_render_inlines(block.inlines, asset_directory)}</p>")
            index += 1

    html = "<!doctype html>\n<html"
    html += ' lang="zh-TW"' if _is_traditional_chinese(content) else ' lang="en"'
    html += ">\n"
    html += head_section
    html += "<body>\n"
    html += "\n".join(body)
    html += "\n</body>\n</html>\n"
    return html


def _is_traditional_chinese(content: NormalizedContent) -> bool:
    """Heuristic: detect Traditional Chinese content from metadata or first text block."""
    if content.metadata and content.metadata.title and _contains_cjk(content.metadata.title):
        return True
    for block in content.blocks[:5]:
        text = block.text
        if _contains_cjk(text):
            return True
    return False


def _contains_cjk(text: str) -> bool:
    """Check if text contains CJK characters."""
    return any("\u4e00" <= char <= "\u9fff" for char in text)
