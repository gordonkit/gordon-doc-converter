"""Normalized semantic content extraction from untrusted HTML documents."""

from __future__ import annotations

import re
from base64 import b64decode
from binascii import Error as BinasciiError
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote_to_bytes, urlsplit

from gordon_doc_converter.content.models import (
    BlockKind,
    ContentAsset,
    ContentBlock,
    DocumentMetadata,
    InlineKind,
    InlineSpan,
    LayoutAvailability,
    LayoutMetadata,
    NormalizedContent,
    SourceAnchor,
)
from gordon_doc_converter.exceptions import InvalidInputError
from gordon_doc_converter.models import ConversionWarning, MetadataDetail, SourceFormat
from gordon_doc_converter.security import file_sha256, validate_source_document

_HEADING_TAGS = {f"h{level}": level for level in range(1, 7)}
_LEAF_TAGS = frozenset(
    {
        *_HEADING_TAGS,
        "address",
        "caption",
        "dd",
        "dt",
        "figcaption",
        "li",
        "p",
        "pre",
        "summary",
        "td",
        "th",
    }
)
_CONTAINER_TAGS = frozenset(
    {
        "article",
        "aside",
        "blockquote",
        "body",
        "details",
        "div",
        "dl",
        "fieldset",
        "figure",
        "footer",
        "form",
        "header",
        "hgroup",
        "html",
        "main",
        "nav",
        "ol",
        "section",
        "table",
        "tbody",
        "tfoot",
        "thead",
        "tr",
        "ul",
    }
)
_DROPPED_TAGS = frozenset(
    {"embed", "iframe", "noscript", "object", "script", "style", "svg", "template"}
)
_VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
_LIST_TAGS = frozenset({"ol", "ul"})
_TABLE_CELL_TAGS = frozenset({"td", "th"})
_PARAGRAPH_TAG = frozenset({"p"})
# An omitted end tag is never recovered across one of these enclosing elements.
_IMPLICIT_CLOSE_BOUNDARIES = frozenset({"body", "dl", "ol", "table", "ul"})
# Openers that implicitly end an unclosed sibling, keyed by the tags they close.
_IMPLICIT_END_TAGS = {
    "dd": frozenset({"dd", "dt"}),
    "dt": frozenset({"dd", "dt"}),
    "li": frozenset({"li"}),
    "td": _TABLE_CELL_TAGS,
    "th": _TABLE_CELL_TAGS,
    "tr": frozenset({"tr"}),
}
_IMAGE_EXTENSIONS = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/tiff": ".tiff",
    "image/webp": ".webp",
}
_MAX_EMBEDDED_ASSET_BYTES = 32 * 1024 * 1024
_MAX_ELEMENT_DEPTH = 256
_WHITESPACE = re.compile(r"[ \t\n\r\f\v]+")
_CHARSET = re.compile(rb"""charset\s*=\s*["']?\s*([A-Za-z0-9_.:+-]+)""", re.IGNORECASE)


def _collapse(text: str) -> str:
    return _WHITESPACE.sub(" ", text)


def _strip_spans(spans: list[InlineSpan]) -> tuple[InlineSpan, ...]:
    """Drop empty spans and trim the leading and trailing whitespace of a block."""
    kept = [
        span
        for span in spans
        if span.text or span.asset_id is not None or span.annotation_id is not None
    ]
    while kept and kept[0].kind is InlineKind.TEXT and not kept[0].text.strip():
        kept.pop(0)
    while kept and kept[-1].kind is InlineKind.TEXT and not kept[-1].text.strip():
        kept.pop()
    if kept:
        kept[0] = _replace_text(kept[0], kept[0].text.lstrip())
        kept[-1] = _replace_text(kept[-1], kept[-1].text.rstrip())
    return tuple(span for span in kept if span.text or span.asset_id is not None)


def _replace_text(span: InlineSpan, text: str) -> InlineSpan:
    return InlineSpan(span.kind, text, span.target, span.asset_id, span.annotation_id)


@dataclass(slots=True)
class _Leaf:
    """One block-level element accumulating inline spans."""

    kind: BlockKind
    spans: list[InlineSpan] = field(default_factory=list)
    level: int | None = None
    list_level: int | None = None
    anchor: SourceAnchor | None = None
    preformatted: bool = False


@dataclass(slots=True)
class _List:
    """One open list element and its ordered-item counter."""

    ordered: bool
    counter: int


@dataclass(slots=True)
class _Table:
    """One open table element with its completed rows and current cell."""

    anchor: SourceAnchor | None
    rows: list[tuple[tuple[InlineSpan, ...], ...]] = field(default_factory=list)
    row: list[tuple[InlineSpan, ...]] | None = None
    cell: list[InlineSpan] | None = None
    irregular: bool = False


@dataclass(slots=True)
class _Element:
    """One open element used for source paths and implicit end-tag recovery."""

    tag: str
    path: str
    counts: dict[str, int] = field(default_factory=dict)
    opened_leaf: bool = False
    opened_list: bool = False
    opened_table: bool = False
    opened_cell: bool = False
    opened_row: bool = False


class _HtmlContentParser(HTMLParser):
    """Collect normalized blocks, assets, and metadata from one HTML document."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[ContentBlock] = []
        self.assets: list[ContentAsset] = []
        self.warnings: list[ConversionWarning] = []
        self.title: str | None = None
        self.meta: dict[str, str] = {}
        self._elements: list[_Element] = []
        self._root_counts: dict[str, int] = {}
        self._leaf: _Leaf | None = None
        self._lists: list[_List] = []
        self._tables: list[_Table] = []
        self._links: list[str | None] = []
        self._revisions: list[InlineKind] = []
        self._dropped_depth = 0
        self._head_depth = 0
        self._in_title = False
        self._asset_bytes = 0
        self._warned: set[str] = set()

    # Warnings ---------------------------------------------------------------

    def _warn(self, code: str, message: str) -> None:
        if code in self._warned:
            return
        self._warned.add(code)
        self.warnings.append(ConversionWarning(code, message))

    # Element paths ----------------------------------------------------------

    def _element_path(self, tag: str) -> str:
        counts = self._elements[-1].counts if self._elements else self._root_counts
        counts[tag] = counts.get(tag, 0) + 1
        parent = self._elements[-1].path if self._elements else ""
        return f"{parent}/{tag}[{counts[tag]}]"

    def _anchor(self, path: str, attributes: dict[str, str]) -> SourceAnchor:
        return SourceAnchor("html-element", element_path=path, native_id=attributes.get("id"))

    # Emission ---------------------------------------------------------------

    def _cell(self) -> list[InlineSpan] | None:
        return self._tables[-1].cell if self._tables else None

    def _emit(self, block: ContentBlock) -> None:
        cell = self._cell()
        if cell is None:
            self.blocks.append(block)
            return
        if block.kind is BlockKind.TABLE:
            spans = _table_spans(block)
            self._warn(
                "INCOMPLETE_TABLE_STRUCTURE",
                "A table has merged or uneven cells that cannot be represented exactly.",
            )
        else:
            spans = list(block.inlines)
        if not spans:
            return
        if cell:
            cell.append(InlineSpan(InlineKind.TEXT, "\n"))
        cell.extend(spans)

    def _flush_leaf(self) -> None:
        leaf = self._leaf
        self._leaf = None
        if leaf is None:
            return
        spans = _strip_spans(leaf.spans)
        if not spans:
            return
        self._emit(
            ContentBlock(
                leaf.kind,
                spans,
                level=leaf.level,
                list_level=leaf.list_level,
                source_anchor=leaf.anchor,
            )
        )

    def _open_leaf(self, leaf: _Leaf) -> None:
        self._flush_leaf()
        self._leaf = leaf

    def _append(self, span: InlineSpan) -> None:
        if self._leaf is None:
            self._leaf = _Leaf(BlockKind.PARAGRAPH)
        self._leaf.spans.append(span)

    # Implicit end tags ------------------------------------------------------

    def _index_of(self, tags: frozenset[str] | set[str]) -> int | None:
        for index in range(len(self._elements) - 1, -1, -1):
            if self._elements[index].tag in tags:
                return index
            if self._elements[index].tag in _IMPLICIT_CLOSE_BOUNDARIES:
                return None
        return None

    def _close_through(self, index: int) -> None:
        while len(self._elements) > index:
            self._close_element(self._elements[-1])

    def _close_nearest(self, tags: frozenset[str]) -> None:
        index = self._index_of(tags)
        if index is not None:
            self._close_through(index)

    def _implicit_close(self, tag: str) -> None:
        """Close elements whose end tags HTML allows an author to omit."""
        if tag not in _LEAF_TAGS and tag not in _CONTAINER_TAGS:
            return
        if tag == "tr":
            self._close_nearest(_TABLE_CELL_TAGS)
        for opener, closes in _IMPLICIT_END_TAGS.items():
            if tag == opener:
                self._close_nearest(closes)
        self._close_nearest(_PARAGRAPH_TAG)

    # Parser callbacks -------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = {name.lower(): (value or "") for name, value in attrs}
        if self._dropped_depth:
            if tag in _DROPPED_TAGS and tag not in _VOID_TAGS:
                self._dropped_depth += 1
            return
        if tag in _DROPPED_TAGS:
            self._warn(
                "HTML_NON_CONTENT_ELEMENT_OMITTED",
                "Script, style, and embedded-object elements are omitted from content.",
            )
            if tag not in _VOID_TAGS:
                self._dropped_depth = 1
            return
        if tag in {"br"}:
            self._append(InlineSpan(InlineKind.TEXT, "\n"))
            return
        if tag == "img":
            self._image(attributes)
            return
        if tag == "meta":
            self._metadata(attributes)
            return
        if tag in _VOID_TAGS:
            if tag == "hr":
                self._flush_leaf()
            return

        self._implicit_close(tag)
        if len(self._elements) >= _MAX_ELEMENT_DEPTH:
            self._warn(
                "HTML_NESTING_DEPTH_EXCEEDED",
                "Elements nested beyond the supported depth were flattened into their parent.",
            )
            return
        path = self._element_path(tag)
        element = _Element(tag, path)
        if tag == "title":
            self._in_title = True
        elif tag == "head":
            self._head_depth += 1
        elif tag == "a":
            self._links.append(_safe_link(attributes.get("href")))
        elif tag in {"ins", "del"}:
            self._revisions.append(
                InlineKind.INSERTION if tag == "ins" else InlineKind.DELETION,
            )
        elif tag in _LIST_TAGS:
            self._flush_leaf()
            self._lists.append(_List(tag == "ol", _list_start(attributes)))
            element.opened_list = True
        elif tag == "table":
            self._flush_leaf()
            self._tables.append(_Table(self._anchor(path, attributes)))
            element.opened_table = True
        elif tag == "tr" and self._tables:
            self._flush_leaf()
            self._tables[-1].row = []
            element.opened_row = True
        elif tag in _TABLE_CELL_TAGS and self._tables:
            self._flush_leaf()
            if self._tables[-1].row is None:
                self._tables[-1].row = []
            self._tables[-1].cell = []
            element.opened_cell = True
            if _spans_cells(attributes):
                self._tables[-1].irregular = True
        elif tag in _LEAF_TAGS:
            self._open_leaf(self._leaf_for(tag, path, attributes))
            element.opened_leaf = True
        elif tag in _CONTAINER_TAGS:
            self._flush_leaf()
        self._elements.append(element)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._dropped_depth:
            if tag in _DROPPED_TAGS:
                self._dropped_depth -= 1
            return
        if tag == "a" and self._links:
            self._links.pop()
        elif tag in {"ins", "del"} and self._revisions:
            self._revisions.pop()
        elif tag == "title":
            self._in_title = False
        index = next(
            (
                position
                for position in range(len(self._elements) - 1, -1, -1)
                if self._elements[position].tag == tag
            ),
            None,
        )
        if index is None:
            return
        self._close_through(index)

    def handle_data(self, data: str) -> None:
        if self._dropped_depth or not data:
            return
        if self._in_title:
            title = _collapse(data).strip()
            if title:
                self.title = f"{self.title} {title}" if self.title else title
            return
        if self._head_depth:
            return
        preformatted = self._leaf is not None and self._leaf.preformatted
        text = data if preformatted else _collapse(data)
        if not text.strip() and self._leaf is None:
            return
        if not text:
            return
        self._append(InlineSpan(self._inline_kind(), text, target=self._link()))

    def close(self) -> None:
        """Finish parsing and close every element the document left open."""
        super().close()
        self._close_through(0)
        self._flush_leaf()

    # Helpers ----------------------------------------------------------------

    def _link(self) -> str | None:
        return self._links[-1] if self._links else None

    def _inline_kind(self) -> InlineKind:
        if self._revisions:
            return self._revisions[-1]
        return InlineKind.LINK if self._links and self._links[-1] else InlineKind.TEXT

    def _leaf_for(self, tag: str, path: str, attributes: dict[str, str]) -> _Leaf:
        anchor = self._anchor(path, attributes)
        if tag in _HEADING_TAGS:
            return _Leaf(BlockKind.HEADING, level=_HEADING_TAGS[tag], anchor=anchor)
        if tag == "li":
            list_level = max(len(self._lists) - 1, 0)
            leaf = _Leaf(BlockKind.LIST_ITEM, list_level=list_level, anchor=anchor)
            if self._lists and self._lists[-1].ordered:
                leaf.spans.append(InlineSpan(InlineKind.TEXT, f"{self._lists[-1].counter}. "))
                self._lists[-1].counter += 1
            return leaf
        return _Leaf(BlockKind.PARAGRAPH, anchor=anchor, preformatted=tag == "pre")

    def _close_element(self, element: _Element) -> None:
        self._elements.pop()
        if element.tag == "head":
            self._head_depth = max(self._head_depth - 1, 0)
        if element.opened_cell and self._tables:
            table = self._tables[-1]
            self._flush_leaf()
            cell = table.cell or []
            table.cell = None
            if table.row is not None:
                table.row.append(_strip_spans(cell))
            return
        if element.opened_row and self._tables:
            table = self._tables[-1]
            self._flush_leaf()
            if table.row is not None:
                table.rows.append(tuple(table.row))
            table.row = None
            return
        if element.opened_table and self._tables:
            self._flush_leaf()
            self._close_table()
            return
        if element.opened_list and self._lists:
            self._flush_leaf()
            self._lists.pop()
            return
        if element.opened_leaf:
            self._flush_leaf()
            return
        if element.tag in _CONTAINER_TAGS:
            self._flush_leaf()

    def _close_table(self) -> None:
        table = self._tables.pop()
        if table.row:
            table.rows.append(tuple(table.row))
        if not table.rows:
            return
        widths = {len(row) for row in table.rows}
        if len(widths) > 1 or table.irregular:
            self._warn(
                "INCOMPLETE_TABLE_STRUCTURE",
                "A table has merged or uneven cells that cannot be represented exactly.",
            )
        self._emit(
            ContentBlock(
                BlockKind.TABLE,
                rows=tuple(table.rows),
                source_anchor=table.anchor,
            )
        )

    def _metadata(self, attributes: dict[str, str]) -> None:
        name = (attributes.get("name") or attributes.get("property") or "").casefold()
        content = attributes.get("content", "").strip()
        if not name or not content or name in self.meta:
            return
        self.meta[name] = content

    def _image(self, attributes: dict[str, str]) -> None:
        alt = _collapse(attributes.get("alt", "")).strip()
        source = attributes.get("src", "").strip()
        asset = self._image_asset(source)
        if asset is not None:
            self.assets.append(asset)
            self._append(InlineSpan(InlineKind.IMAGE, alt or "image", asset_id=asset.asset_id))
            return
        target = _safe_link(source)
        if target is None and not alt:
            return
        self._append(InlineSpan(InlineKind.IMAGE, alt or "image", target=target))
        if target is not None:
            self._warn(
                "HTML_EXTERNAL_ASSET_REFERENCED",
                "Images referenced by URL are linked rather than embedded as assets.",
            )

    def _image_asset(self, source: str) -> ContentAsset | None:
        if not source.casefold().startswith("data:"):
            return None
        header, _, payload = source[len("data:") :].partition(",")
        parameters = header.split(";")
        media_type = parameters[0].strip().casefold() or "text/plain"
        if not media_type.startswith("image/"):
            self._warn(
                "HTML_ASSET_DECODE_FAILED",
                "An inline data URI could not be decoded as an embedded image.",
            )
            return None
        try:
            data = (
                b64decode(payload, validate=True)
                if "base64" in {item.strip().casefold() for item in parameters[1:]}
                else unquote_to_bytes(payload)
            )
        except (BinasciiError, ValueError):
            self._warn(
                "HTML_ASSET_DECODE_FAILED",
                "An inline data URI could not be decoded as an embedded image.",
            )
            return None
        if not data or self._asset_bytes + len(data) > _MAX_EMBEDDED_ASSET_BYTES:
            self._warn(
                "HTML_ASSET_LIMIT_EXCEEDED",
                "Inline image data exceeded the embedded-asset limit and was not extracted.",
            )
            return None
        self._asset_bytes += len(data)
        suffix = _IMAGE_EXTENSIONS.get(media_type, ".bin")
        filename = f"image-{len(self.assets) + 1:04d}{suffix}"
        return ContentAsset(filename, filename, media_type, data)


def _table_spans(block: ContentBlock) -> list[InlineSpan]:
    """Flatten one nested table into tab-separated and newline-separated text."""
    text = "\n".join(
        "\t".join("".join(span.text for span in cell) for cell in row) for row in block.rows
    )
    return [InlineSpan(InlineKind.TEXT, text)] if text.strip() else []


def _spans_cells(attributes: dict[str, str]) -> bool:
    for name in ("colspan", "rowspan"):
        try:
            if int(attributes.get(name, "1")) > 1:
                return True
        except ValueError:
            continue
    return False


def _list_start(attributes: dict[str, str]) -> int:
    try:
        return int(attributes.get("start", "1"))
    except ValueError:
        return 1


def _safe_link(target: str | None) -> str | None:
    if not target:
        return None
    value = target.strip()
    if not value:
        return None
    scheme = urlsplit(value).scheme.casefold()
    return value if scheme in {"", "http", "https", "mailto"} else None


def _decode(raw: bytes) -> tuple[str, ConversionWarning | None]:
    """Decode HTML bytes using the declared charset, falling back to UTF-8."""
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", errors="replace"), None
    match = _CHARSET.search(raw[:4096])
    declared = match.group(1).decode("ascii", errors="ignore") if match is not None else None
    for encoding in (declared, "utf-8"):
        if encoding is None:
            continue
        try:
            return raw.decode(encoding), None
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", errors="replace"), ConversionWarning(
        "HTML_ENCODING_REPLACED",
        "Undecodable bytes were replaced while reading the HTML source.",
    )


def _metadata_from(
    title: str | None, meta: dict[str, str], detail: MetadataDetail
) -> DocumentMetadata | None:
    if detail is MetadataDetail.NONE:
        return None

    def first(*names: str) -> str | None:
        return next((meta[name] for name in names if name in meta), None)

    metadata = DocumentMetadata(
        title=title,
        subject=first("description", "og:description", "dcterms.description"),
        creator=first("author", "dc.creator", "dcterms.creator"),
        keywords=first("keywords", "dc.subject"),
        created=first("dcterms.created", "date", "article:published_time"),
        modified=first("dcterms.modified", "last-modified", "article:modified_time"),
    )
    if any(
        value is not None
        for value in (
            metadata.title,
            metadata.subject,
            metadata.creator,
            metadata.keywords,
            metadata.created,
            metadata.modified,
        )
    ):
        return metadata
    return DocumentMetadata()


def extract_html_content(
    source_path: Path,
    *,
    metadata_detail: MetadataDetail = MetadataDetail.BASIC,
) -> NormalizedContent:
    """Extract normalized blocks, inline data-URI images, and metadata from HTML."""
    validate_source_document(source_path, SourceFormat.HTML)
    try:
        text, encoding_warning = _decode(source_path.read_bytes())
        parser = _HtmlContentParser()
        parser.feed(text)
        parser.close()
    except InvalidInputError:
        raise
    except (OSError, ValueError) as exc:
        raise InvalidInputError("HTML content could not be extracted") from exc

    warnings = list(parser.warnings)
    if encoding_warning is not None:
        warnings.insert(0, encoding_warning)
    layout = LayoutMetadata()
    if metadata_detail is MetadataDetail.LAYOUT:
        layout = LayoutMetadata(LayoutAvailability.UNAVAILABLE)
        warnings.append(
            ConversionWarning(
                "LAYOUT_METADATA_UNAVAILABLE",
                "HTML layout metadata requires a configured layout provider.",
            )
        )
    return NormalizedContent(
        source_format=SourceFormat.HTML,
        blocks=tuple(parser.blocks),
        assets=tuple(parser.assets),
        warnings=tuple(warnings),
        metadata=_metadata_from(parser.title, parser.meta, metadata_detail),
        layout=layout,
        source_sha256=file_sha256(source_path),
    )
