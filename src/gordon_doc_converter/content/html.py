"""Safe deterministic semantic HTML serialization."""

from __future__ import annotations

from html import escape
from urllib.parse import urlsplit

from gordon_doc_converter.content.models import (
    BlockKind,
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
    if span.kind is InlineKind.IMAGE and span.asset_id is not None:
        source = escape(f"{asset_directory}/{span.asset_id}", quote=True)
        return f'<img src="{source}" alt="{escape(span.text, quote=True)}">'
    if span.kind is InlineKind.COMMENT_REFERENCE and span.annotation_id is not None:
        identifier = escape(span.annotation_id, quote=True)
        return f'<sup><a href="#annotation-{identifier}">[{identifier}]</a></sup>'
    return text


def _render_inlines(inlines: tuple[InlineSpan, ...], asset_directory: str) -> str:
    return "".join(_render_span(span, asset_directory) for span in inlines)


def render_html(content: NormalizedContent, *, asset_directory: str) -> str:
    """Serialize normalized blocks to semantic HTML without active content."""
    body: list[str] = []
    list_open = False
    for block in content.blocks:
        if block.kind is not BlockKind.LIST_ITEM and list_open:
            body.append("</ul>")
            list_open = False
        if block.kind is BlockKind.HEADING:
            level = min(max(block.level or 1, 1), 6)
            body.append(f"<h{level}>{_render_inlines(block.inlines, asset_directory)}</h{level}>")
        elif block.kind is BlockKind.LIST_ITEM:
            if not list_open:
                body.append("<ul>")
                list_open = True
            body.append(f"<li>{_render_inlines(block.inlines, asset_directory)}</li>")
        elif block.kind is BlockKind.TABLE:
            body.append("<table>")
            for row_index, row in enumerate(block.rows):
                body.append("<tr>")
                cell_tag = "th" if row_index == 0 else "td"
                body.extend(
                    f"<{cell_tag}>{_render_inlines(cell, asset_directory)}</{cell_tag}>"
                    for cell in row
                )
                body.append("</tr>")
            body.append("</table>")
        else:
            body.append(f"<p>{_render_inlines(block.inlines, asset_directory)}</p>")
    if list_open:
        body.append("</ul>")
    return '<!doctype html>\n<html lang="en">\n<body>\n' + "\n".join(body) + "\n</body>\n</html>\n"
