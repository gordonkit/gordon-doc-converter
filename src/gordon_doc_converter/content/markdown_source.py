"""Normalized semantic content extraction from CommonMark and GFM Markdown."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from markdown_it import MarkdownIt
from markdown_it.token import Token

from gordon_doc_converter.content.data_uri import DataUriReason, decode_data_uri_image
from gordon_doc_converter.content.models import (
    BlockKind,
    ContentAsset,
    ContentBlock,
    DocumentMetadata,
    InlineKind,
    InlineSpan,
    InlineStyle,
    LayoutAvailability,
    LayoutMetadata,
    NormalizedContent,
    SourceAnchor,
)
from gordon_doc_converter.exceptions import InvalidInputError
from gordon_doc_converter.models import ConversionWarning, MetadataDetail, SourceFormat
from gordon_doc_converter.security import file_sha256, validate_source_document

# A leading YAML block, terminated by "---" or "...", holds document metadata.
_FRONT_MATTER = re.compile(r"\A---[ \t]*\n(.*?\n)(?:---|\.\.\.)[ \t]*(?:\n|\Z)", re.DOTALL)
_HEADING_TAGS = {f"h{level}": level for level in range(1, 7)}
_STYLE_TOKENS = {
    "strong": InlineStyle.STRONG,
    "em": InlineStyle.EMPHASIS,
}
# Raw inline HTML the writers themselves emit, so our own output round-trips.
_REVISION_HTML = {"<ins>": InlineKind.INSERTION, "<del>": InlineKind.DELETION}
_REVISION_HTML_END = frozenset({"</ins>", "</del>"})
_LINE_BREAK_HTML = frozenset({"<br>", "<br/>", "<br />"})
_MAX_HEADING_LEVEL = 6
# GFM checkboxes, kept as symbols with wide CJK font coverage: U+2610 is missing
# from common print fonts, so an unchecked box uses the white square instead.
_TASK_MARKERS = {"[ ] ": "□", "[x] ": "☑"}


def _safe_target(target: str | None) -> str | None:
    """Keep only link targets whose scheme a rendered document may follow."""
    if not target:
        return None
    value = target.strip()
    if not value:
        return None
    return value if urlsplit(value).scheme.casefold() in {"", "http", "https", "mailto"} else None


def _task_marker(spans: tuple[InlineSpan, ...]) -> tuple[InlineSpan, ...]:
    """Turn a GFM task-list checkbox into the symbol every output can render."""
    if not spans:
        return spans
    first = spans[0]
    if first.kind is not InlineKind.TEXT:
        return spans
    marker = _TASK_MARKERS.get(first.text[:4].casefold())
    if marker is None:
        return spans
    remainder = f"{marker} {first.text[4:]}"
    return (replace(first, text=remainder), *spans[1:])


@dataclass(slots=True)
class _List:
    """One open list and its ordered-item counter."""

    ordered: bool
    counter: int


@dataclass(slots=True)
class _Table:
    """One open table with its completed rows and current row."""

    anchor: SourceAnchor | None
    rows: list[tuple[tuple[InlineSpan, ...], ...]] = field(default_factory=list)
    row: list[tuple[InlineSpan, ...]] = field(default_factory=list)
    header: bool = False


class _MarkdownWalker:
    """Turn one markdown-it token stream into normalized blocks and assets."""

    def __init__(self, line_offset: int = 0) -> None:
        self.blocks: list[ContentBlock] = []
        self.assets: list[ContentAsset] = []
        self.warnings: list[ConversionWarning] = []
        self._line_offset = line_offset
        self._quote_depth = 0
        self._lists: list[_List] = []
        self._tables: list[_Table] = []
        self._styles: list[InlineStyle] = []
        self._links: list[str | None] = []
        self._revisions: list[InlineKind] = []
        self._item_pending = False
        self._asset_bytes = 0
        self._warned: set[str] = set()

    # Warnings ---------------------------------------------------------------

    def _warn(self, code: str, message: str) -> None:
        if code in self._warned:
            return
        self._warned.add(code)
        self.warnings.append(ConversionWarning(code, message))

    # Positions --------------------------------------------------------------

    def _anchor(self, token: Token) -> SourceAnchor | None:
        if not token.map:
            return None
        line = token.map[0] + self._line_offset + 1
        return SourceAnchor("markdown-line", element_path=f"line[{line}]")

    def _quote(self) -> int | None:
        return self._quote_depth or None

    def _list_level(self) -> int | None:
        return len(self._lists) - 1 if self._lists else None

    # Emission ---------------------------------------------------------------

    def _emit(self, block: ContentBlock) -> None:
        self.blocks.append(block)

    def _emit_leaf(
        self,
        kind: BlockKind,
        spans: tuple[InlineSpan, ...],
        token: Token,
        **fields: Any,
    ) -> None:
        """Emit one inline-bearing block, opening a list item when one is due."""
        list_level = self._list_level()
        if self._item_pending and list_level is not None:
            self._item_pending = False
            if kind is BlockKind.PARAGRAPH:
                kind = BlockKind.LIST_ITEM
                spans = self._numbered(_task_marker(spans))
        self._emit(
            ContentBlock(
                kind,
                spans,
                list_level=list_level if kind is not BlockKind.HEADING else None,
                quote_level=self._quote(),
                source_anchor=self._anchor(token),
                **fields,
            )
        )

    def _numbered(self, spans: tuple[InlineSpan, ...]) -> tuple[InlineSpan, ...]:
        """Prefix an ordered item with its rendered counter, as HTML sources do."""
        current = self._lists[-1]
        if not current.ordered:
            return spans
        prefix = InlineSpan(InlineKind.TEXT, f"{current.counter}. ")
        current.counter += 1
        return (prefix, *spans)

    # Block walking ----------------------------------------------------------

    def walk(self, tokens: list[Token]) -> None:
        """Consume one block-level token stream in source order."""
        index = 0
        while index < len(tokens):
            token = tokens[index]
            following = tokens[index + 1] if index + 1 < len(tokens) else None
            index += self._block(token, following)

    def _block(self, token: Token, following: Token | None) -> int:
        """Handle one block token, returning how many tokens it consumed."""
        kind = token.type
        inline = following if following is not None and following.type == "inline" else None
        if kind == "heading_open" and inline is not None:
            level = min(_HEADING_TAGS.get(token.tag, 1), _MAX_HEADING_LEVEL)
            self._emit_leaf(BlockKind.HEADING, self._inlines(inline), token, level=level)
            return 3
        if kind == "paragraph_open" and inline is not None:
            spans = self._inlines(inline)
            if spans:
                self._emit_leaf(BlockKind.PARAGRAPH, spans, token)
            return 3
        if kind in {"th_open", "td_open"} and self._tables:
            # A cell always occupies a column, so an empty one still counts.
            self._tables[-1].row.append(self._inlines(inline) if inline is not None else ())
            return 3 if inline is not None else 1
        if kind in {"fence", "code_block"}:
            self._code_block(token)
            return 1
        if kind == "hr":
            self._emit_leaf(BlockKind.THEMATIC_BREAK, (), token)
            return 1
        if kind == "blockquote_open":
            self._quote_depth += 1
            return 1
        if kind == "blockquote_close":
            self._quote_depth = max(self._quote_depth - 1, 0)
            return 1
        if kind in {"bullet_list_open", "ordered_list_open"}:
            self._lists.append(_List(kind == "ordered_list_open", _list_start(token)))
            return 1
        if kind in {"bullet_list_close", "ordered_list_close"}:
            if self._lists:
                self._lists.pop()
            self._item_pending = False
            return 1
        if kind == "list_item_open":
            self._item_pending = True
            return 1
        if kind == "list_item_close":
            self._item_pending = False
            return 1
        if kind == "table_open":
            self._tables.append(_Table(self._anchor(token)))
            return 1
        if kind == "table_close":
            self._close_table()
            return 1
        if kind in {"tr_open", "thead_open", "tbody_open"}:
            return 1
        if kind == "tr_close":
            if self._tables:
                table = self._tables[-1]
                table.rows.append(tuple(table.row))
                table.row = []
            return 1
        if kind in {"thead_close", "tbody_close", "th_close", "td_close"}:
            return 1
        if kind == "html_block":
            self._warn(
                "MARKDOWN_RAW_HTML_OMITTED",
                "Raw HTML blocks are omitted from normalized content.",
            )
            return 1
        if kind == "inline":
            spans = self._inlines(token)
            if spans:
                self._emit_leaf(BlockKind.PARAGRAPH, spans, token)
            return 1
        return 1

    def _code_block(self, token: Token) -> None:
        body = token.content.rstrip("\n")
        if not body.strip():
            return
        language = token.info.strip().split(" ", 1)[0] if token.info else None
        self._emit_leaf(
            BlockKind.CODE_BLOCK,
            (InlineSpan(InlineKind.TEXT, body),),
            token,
            language=language or None,
        )

    def _close_table(self) -> None:
        table = self._tables.pop()
        if table.row:
            table.rows.append(tuple(table.row))
        if not table.rows:
            return
        if len({len(row) for row in table.rows}) > 1:
            self._warn(
                "INCOMPLETE_TABLE_STRUCTURE",
                "A table has merged or uneven cells that cannot be represented exactly.",
            )
        self._emit(
            ContentBlock(
                BlockKind.TABLE,
                rows=tuple(table.rows),
                quote_level=self._quote(),
                source_anchor=table.anchor,
            )
        )

    # Inline walking ---------------------------------------------------------

    def _inline_kind(self) -> InlineKind:
        if self._revisions:
            return self._revisions[-1]
        return InlineKind.LINK if self._links and self._links[-1] else InlineKind.TEXT

    def _span(self, text: str) -> InlineSpan:
        return InlineSpan(
            self._inline_kind(),
            text,
            target=self._links[-1] if self._links else None,
            styles=frozenset(self._styles),
        )

    def _inlines(self, token: Token) -> tuple[InlineSpan, ...]:
        """Flatten one inline token and its children into normalized spans."""
        spans: list[InlineSpan] = []
        for child in token.children or ():
            self._inline(child, spans)
        return tuple(span for span in spans if span.text or span.asset_id is not None)

    def _inline(self, token: Token, spans: list[InlineSpan]) -> None:
        kind = token.type
        if kind == "text":
            if token.content:
                spans.append(self._span(token.content))
        elif kind == "code_inline":
            self._styles.append(InlineStyle.CODE)
            spans.append(self._span(token.content))
            self._styles.pop()
        elif kind in {"strong_open", "em_open"}:
            self._styles.append(_STYLE_TOKENS[token.tag])
        elif kind in {"strong_close", "em_close"}:
            style = _STYLE_TOKENS.get(token.tag)
            if style is not None and style in self._styles:
                self._styles.remove(style)
        elif kind == "s_open":
            self._revisions.append(InlineKind.DELETION)
        elif kind == "s_close":
            if self._revisions:
                self._revisions.pop()
        elif kind == "link_open":
            href = token.attrGet("href")
            self._links.append(_safe_target(str(href) if href is not None else None))
        elif kind == "link_close":
            if self._links:
                self._links.pop()
        elif kind == "image":
            self._image(token, spans)
        elif kind == "softbreak":
            spans.append(self._span(" "))
        elif kind == "hardbreak":
            spans.append(self._span("\n"))
        elif kind == "html_inline":
            self._html_inline(token, spans)
        else:
            for child in token.children or ():
                self._inline(child, spans)

    def _html_inline(self, token: Token, spans: list[InlineSpan]) -> None:
        """Keep the few raw inline tags the writers emit; drop everything else."""
        markup = token.content.strip().casefold()
        revision = _REVISION_HTML.get(markup)
        if revision is not None:
            self._revisions.append(revision)
            return
        if markup in _REVISION_HTML_END:
            if self._revisions:
                self._revisions.pop()
            return
        if markup in _LINE_BREAK_HTML:
            spans.append(self._span("\n"))
            return
        self._warn(
            "MARKDOWN_RAW_HTML_OMITTED",
            "Raw HTML blocks are omitted from normalized content.",
        )

    def _image(self, token: Token, spans: list[InlineSpan]) -> None:
        alt = "".join(child.content for child in token.children or ()) or token.attrGet("alt") or ""
        alt = str(alt).strip()
        source = str(token.attrGet("src") or "").strip()
        asset, reason = decode_data_uri_image(
            source, index=len(self.assets) + 1, consumed_bytes=self._asset_bytes
        )
        if asset is not None:
            self.assets.append(asset)
            self._asset_bytes += len(asset.data)
            spans.append(InlineSpan(InlineKind.IMAGE, alt or "image", asset_id=asset.asset_id))
            return
        if reason is DataUriReason.DECODE_FAILED:
            self._warn(
                "MARKDOWN_ASSET_DECODE_FAILED",
                "An inline data URI could not be decoded as an embedded image.",
            )
        elif reason is DataUriReason.LIMIT_EXCEEDED:
            self._warn(
                "MARKDOWN_ASSET_LIMIT_EXCEEDED",
                "Inline image data exceeded the embedded-asset limit and was not extracted.",
            )
        target = _safe_target(source)
        if target is None and not alt:
            return
        spans.append(InlineSpan(InlineKind.IMAGE, alt or "image", target=target))
        if target is not None:
            self._warn(
                "MARKDOWN_EXTERNAL_ASSET_REFERENCED",
                "Images referenced by path or URL are linked rather than embedded as assets.",
            )


def _list_start(token: Token) -> int:
    try:
        return int(str(token.attrGet("start") or "1"))
    except ValueError:
        return 1


def _normalize_newlines(text: str) -> str:
    """Fold CRLF and lone CR into LF so a document extracts the same everywhere."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _decode(raw: bytes) -> tuple[str, ConversionWarning | None]:
    """Decode Markdown bytes as UTF-8, the only encoding the format declares."""
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        return _normalize_newlines(raw.decode("utf-8")), None
    except UnicodeDecodeError:
        return _normalize_newlines(raw.decode("utf-8", errors="replace")), ConversionWarning(
            "MARKDOWN_ENCODING_REPLACED",
            "Undecodable bytes were replaced while reading the Markdown source.",
        )


def _split_front_matter(text: str) -> tuple[str, dict[str, Any], int, ConversionWarning | None]:
    """Separate a leading YAML metadata block from the Markdown body."""
    match = _FRONT_MATTER.match(text)
    if match is None:
        return text, {}, 0, None
    body = text[match.end() :]
    offset = text[: match.end()].count("\n")
    try:
        loaded = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return (
            body,
            {},
            offset,
            ConversionWarning(
                "MARKDOWN_FRONT_MATTER_UNREADABLE",
                "A leading YAML metadata block could not be parsed and was ignored.",
            ),
        )
    if not isinstance(loaded, dict):
        return body, {}, offset, None
    return body, {str(key).casefold(): value for key, value in loaded.items()}, offset, None


def _scalar(value: Any) -> str | None:
    """Render one front-matter value as the flat string the model stores."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, list | tuple):
        parts = [_scalar(item) for item in value]
        joined = ", ".join(part for part in parts if part)
        return joined or None
    text = str(value).strip()
    return text or None


def _metadata_from(front_matter: dict[str, Any], detail: MetadataDetail) -> DocumentMetadata | None:
    if detail is MetadataDetail.NONE:
        return None

    def first(*names: str) -> str | None:
        return next(
            (
                scalar
                for name in names
                if name in front_matter and (scalar := _scalar(front_matter[name])) is not None
            ),
            None,
        )

    return DocumentMetadata(
        title=first("title"),
        subject=first("subject", "description", "summary"),
        creator=first("author", "authors", "creator"),
        keywords=first("keywords", "tags", "categories"),
        created=first("date", "created", "published"),
        modified=first("modified", "updated", "last-modified"),
    )


def _parser() -> MarkdownIt:
    """Build the CommonMark parser with the GFM constructs writers rely on."""
    return MarkdownIt("commonmark").enable(["table", "strikethrough"])


def extract_markdown_content(
    source_path: Path,
    *,
    metadata_detail: MetadataDetail = MetadataDetail.BASIC,
) -> NormalizedContent:
    """Extract normalized blocks, inline data-URI images, and metadata from Markdown."""
    validate_source_document(source_path, SourceFormat.MARKDOWN)
    try:
        text, encoding_warning = _decode(source_path.read_bytes())
        body, front_matter, line_offset, front_matter_warning = _split_front_matter(text)
        walker = _MarkdownWalker(line_offset)
        walker.walk(_parser().parse(body))
    except InvalidInputError:
        raise
    except (OSError, ValueError) as exc:
        raise InvalidInputError("Markdown content could not be extracted") from exc

    warnings = list(walker.warnings)
    for leading in (front_matter_warning, encoding_warning):
        if leading is not None:
            warnings.insert(0, leading)
    layout = LayoutMetadata()
    if metadata_detail is MetadataDetail.LAYOUT:
        layout = LayoutMetadata(LayoutAvailability.UNAVAILABLE)
        warnings.append(
            ConversionWarning(
                "LAYOUT_METADATA_UNAVAILABLE",
                "Markdown layout metadata requires a configured layout provider.",
            )
        )
    return NormalizedContent(
        source_format=SourceFormat.MARKDOWN,
        blocks=tuple(walker.blocks),
        assets=tuple(walker.assets),
        warnings=tuple(warnings),
        metadata=_metadata_from(front_matter, metadata_detail),
        layout=layout,
        source_sha256=file_sha256(source_path),
    )
