"""Direct ODF text extraction into the engine-neutral semantic content model."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree
from zipfile import ZipFile

from gordon_doc_converter.content.counters import OrdinalSystem, format_ordinal
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
from gordon_doc_converter.models import (
    AnnotationAnchor,
    AnnotationKind,
    CommentMode,
    ConversionWarning,
    MetadataDetail,
    NormalizedAnnotation,
    RevisionMode,
    SourceFormat,
)
from gordon_doc_converter.security import file_sha256, validate_source_document

_OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
_TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
_TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
_DRAW = "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
_STYLE = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"
_META = "urn:oasis:names:tc:opendocument:xmlns:meta:1.0"
_SVG = "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
_FO = "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
_XLINK = "http://www.w3.org/1999/xlink"
_DC = "http://purl.org/dc/elements/1.1/"

_CONTENT_PART = "content.xml"
_STYLES_PART = "styles.xml"
_META_PART = "meta.xml"
_MAX_LIST_LEVELS = 10
_MAX_HEADING_LEVEL = 6
_ELEMENT_PREFIXES = {
    _OFFICE: "office",
    _TEXT: "text",
    _TABLE: "table",
    _DRAW: "draw",
}

# LibreOffice writes ODF numbering systems as sample sequences rather than tokens.
# ODF encodes spaces in style names as "_20_".
_QUOTE_STYLE_NAMES = frozenset({"quotations", "quote", "blockquote"})
_CODE_BLOCK_STYLE_NAMES = frozenset({"preformattedtext", "sourcecode", "code"})
_MONOSPACE_FONTS = frozenset(
    {
        "consolas",
        "courier",
        "couriernew",
        "dejavusansmono",
        "liberationmono",
        "lucidaconsole",
        "menlo",
        "monaco",
    }
)


def _normalized_style_name(value: str | None) -> str:
    return (value or "").replace("_20_", " ").casefold().replace(" ", "").replace("_", "")


_NUMBER_FORMATS: dict[str, OrdinalSystem] = {
    "1": OrdinalSystem.DECIMAL,
    "a": OrdinalSystem.LOWER_LETTER,
    "A": OrdinalSystem.UPPER_LETTER,
    "i": OrdinalSystem.LOWER_ROMAN,
    "I": OrdinalSystem.UPPER_ROMAN,
    "一": OrdinalSystem.CJK_DECIMAL,
    "壹": OrdinalSystem.CJK_FINANCIAL,
    "甲": OrdinalSystem.HEAVENLY_STEM,
    "子": OrdinalSystem.EARTHLY_BRANCH,
}
_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".svg": "image/svg+xml",
    ".svm": "image/x-svm",
    ".emf": "image/emf",
    ".wmf": "image/wmf",
    ".pdf": "application/pdf",
}


def _q(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def _prefixed_name(tag: str) -> str:
    """Render one qualified tag as the `prefix:local` form used by source anchors."""
    namespace, _, local_name = tag.rpartition("}")
    prefix = _ELEMENT_PREFIXES.get(namespace.lstrip("{"))
    return f"{prefix}:{local_name}" if prefix else local_name


@dataclass(frozen=True, slots=True)
class _ListLevel:
    """One resolved level of an ODF list, outline, or bullet numbering style."""

    system: OrdinalSystem | None
    prefix: str
    suffix: str
    start_value: int
    display_levels: int


@dataclass(frozen=True, slots=True)
class _ParagraphStyle:
    """Allowlisted paragraph-style facts that influence normalized block kinds."""

    display_name: str
    parent: str | None
    outline_level: int | None
    formatting: frozenset[InlineStyle] = frozenset()


@dataclass(frozen=True, slots=True)
class _TextStyle:
    """One ODF character style resolved to normalized inline formatting."""

    parent: str | None
    formatting: frozenset[InlineStyle]


@dataclass(frozen=True, slots=True)
class _ChangedRegion:
    """One tracked-change region declared by `text:tracked-changes`."""

    kind: AnnotationKind
    author: str | None
    timestamp: str | None
    content: ElementTree.Element | None


@dataclass(slots=True)
class _State:
    """Mutable extraction state shared by the ODF block and inline walkers."""

    archive: ZipFile
    revision_mode: RevisionMode
    comment_mode: CommentMode
    include_metadata: bool
    paragraph_styles: dict[str, _ParagraphStyle]
    list_styles: dict[str, dict[int, _ListLevel]]
    outline_levels: dict[int, _ListLevel]
    changed_regions: dict[str, _ChangedRegion]
    text_styles: dict[str, _TextStyle] = field(default_factory=dict)
    active_styles: list[InlineStyle] = field(default_factory=list)
    assets: list[ContentAsset] = field(default_factory=list)
    annotations: list[NormalizedAnnotation] = field(default_factory=list)
    warnings: list[ConversionWarning] = field(default_factory=list)
    asset_by_part: dict[str, ContentAsset] = field(default_factory=dict)
    warned_codes: set[str] = field(default_factory=set)
    list_counters: dict[str, list[int]] = field(default_factory=dict)
    outline_counters: list[int] = field(default_factory=lambda: [0] * _MAX_HEADING_LEVEL)
    active_insertions: list[str] = field(default_factory=list)
    source_order: int = 0

    def warn(self, code: str, message: str) -> None:
        """Record one warning code at most once per extraction pass."""
        if code in self.warned_codes:
            return
        self.warned_codes.add(code)
        self.warnings.append(ConversionWarning(code, message))

    def annotation(
        self,
        annotation_id: str,
        kind: AnnotationKind,
        *,
        text: str | None = None,
        author: str | None = None,
        timestamp: str | None = None,
    ) -> None:
        """Append one normalized annotation in source order."""
        self.annotations.append(
            NormalizedAnnotation(
                annotation_id=annotation_id,
                kind=kind,
                source_order=self.source_order,
                anchor=AnnotationAnchor(exact=False),
                text=text,
                author=author if self.include_metadata else None,
                timestamp=timestamp if self.include_metadata else None,
            )
        )
        self.source_order += 1


def _parse_xml(archive: ZipFile, name: str) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(archive.read(name))
    except (KeyError, ElementTree.ParseError) as exc:
        raise InvalidInputError(f"ODT contains an invalid {name} part") from exc


def _optional_xml(archive: ZipFile, name: str) -> ElementTree.Element | None:
    return _parse_xml(archive, name) if name in archive.namelist() else None


def _document_metadata(archive: ZipFile) -> DocumentMetadata:
    root = _optional_xml(archive, _META_PART)
    if root is None:
        return DocumentMetadata()
    meta = root.find(_q(_OFFICE, "meta"))
    if meta is None:
        return DocumentMetadata()

    def text(namespace: str, name: str) -> str | None:
        element = meta.find(_q(namespace, name))
        return element.text if element is not None and element.text else None

    keywords = [element.text for element in meta.findall(_q(_META, "keyword")) if element.text]
    return DocumentMetadata(
        title=text(_DC, "title"),
        subject=text(_DC, "subject"),
        creator=text(_META, "initial-creator") or text(_DC, "creator"),
        keywords=", ".join(keywords) or None,
        created=text(_META, "creation-date"),
        modified=text(_DC, "date"),
    )


def _number_system(value: str | None) -> OrdinalSystem | None:
    """Map an ODF `style:num-format` sample sequence onto a shared numbering system."""
    if value is None:
        return OrdinalSystem.DECIMAL
    sample = value.strip()
    return _NUMBER_FORMATS.get(sample[:1]) if sample else None


def _list_level(element: ElementTree.Element) -> _ListLevel:
    start = element.get(_q(_TEXT, "start-value"))
    display = element.get(_q(_TEXT, "display-levels"))
    numbered = element.tag in {
        _q(_TEXT, "list-level-style-number"),
        _q(_TEXT, "outline-level-style"),
    }
    return _ListLevel(
        system=_number_system(element.get(_q(_STYLE, "num-format"))) if numbered else None,
        prefix=element.get(_q(_STYLE, "num-prefix"), ""),
        suffix=element.get(_q(_STYLE, "num-suffix"), ""),
        start_value=int(start) if start is not None and start.isdigit() else 1,
        display_levels=int(display) if display is not None and display.isdigit() else 1,
    )


def _level_definitions(container: ElementTree.Element, attribute: str) -> dict[int, _ListLevel]:
    levels: dict[int, _ListLevel] = {}
    for child in container:
        value = child.get(_q(_TEXT, attribute))
        if value is None or not value.isdigit():
            continue
        level = int(value) - 1
        if 0 <= level < _MAX_LIST_LEVELS:
            levels[level] = _list_level(child)
    return levels


def _text_style_formatting(style: ElementTree.Element) -> frozenset[InlineStyle]:
    """Map one ODF text style's properties to normalized character formatting."""
    properties = style.find(_q(_STYLE, "text-properties"))
    if properties is None:
        return frozenset()
    styles: set[InlineStyle] = set()
    weight = properties.get(_q(_FO, "font-weight"), "")
    if weight and weight != "normal":
        styles.add(InlineStyle.STRONG)
    if properties.get(_q(_FO, "font-style"), "") in {"italic", "oblique"}:
        styles.add(InlineStyle.EMPHASIS)
    fonts = {
        _normalized_style_name(properties.get(_q(_STYLE, attribute)))
        for attribute in ("font-name", "font-name-complex", "font-name-asian")
    }
    if fonts & _MONOSPACE_FONTS or properties.get(_q(_STYLE, "font-pitch")) == "fixed":
        styles.add(InlineStyle.CODE)
    return frozenset(styles)


def _collect_styles(
    roots: tuple[ElementTree.Element, ...],
) -> tuple[
    dict[str, _ParagraphStyle],
    dict[str, dict[int, _ListLevel]],
    dict[int, _ListLevel],
    dict[str, _TextStyle],
]:
    """Merge paragraph, text, list, and outline styles from the content and styles parts."""
    paragraph_styles: dict[str, _ParagraphStyle] = {}
    list_styles: dict[str, dict[int, _ListLevel]] = {}
    outline_levels: dict[int, _ListLevel] = {}
    text_styles: dict[str, _TextStyle] = {}
    for root in roots:
        for container_name in ("styles", "automatic-styles"):
            container = root.find(_q(_OFFICE, container_name))
            if container is None:
                continue
            for style in container.findall(_q(_STYLE, "style")):
                name = style.get(_q(_STYLE, "name"))
                if not name:
                    continue
                if style.get(_q(_STYLE, "family")) == "text":
                    text_styles[name] = _TextStyle(
                        parent=style.get(_q(_STYLE, "parent-style-name")),
                        formatting=_text_style_formatting(style),
                    )
                    continue
                if style.get(_q(_STYLE, "family")) != "paragraph":
                    continue
                outline = style.get(_q(_STYLE, "default-outline-level"))
                paragraph_styles[name] = _ParagraphStyle(
                    display_name=style.get(_q(_STYLE, "display-name"), name),
                    parent=style.get(_q(_STYLE, "parent-style-name")),
                    outline_level=int(outline)
                    if outline is not None and outline.isdigit()
                    else None,
                    formatting=_text_style_formatting(style),
                )
            for style in container.findall(_q(_TEXT, "list-style")):
                name = style.get(_q(_STYLE, "name"))
                if name:
                    list_styles[name] = _level_definitions(style, "level")
        outline_style = root.find(f"{_q(_OFFICE, 'styles')}/{_q(_TEXT, 'outline-style')}")
        if outline_style is not None:
            outline_levels.update(_level_definitions(outline_style, "level"))
    return paragraph_styles, list_styles, outline_levels, text_styles


def _changed_regions(body: ElementTree.Element) -> dict[str, _ChangedRegion]:
    """Index `text:changed-region` declarations by the id body markers reference."""
    regions: dict[str, _ChangedRegion] = {}
    tracked = body.find(_q(_TEXT, "tracked-changes"))
    if tracked is None:
        return regions
    for region in tracked.findall(_q(_TEXT, "changed-region")):
        identifier = region.get(_q(_TEXT, "id")) or region.get(_q(_XLINK, "href"), "").lstrip("#")
        if not identifier:
            continue
        insertion = region.find(_q(_TEXT, "insertion"))
        deletion = region.find(_q(_TEXT, "deletion"))
        change = insertion if insertion is not None else deletion
        if change is None:
            continue
        info = change.find(_q(_OFFICE, "change-info"))
        author = info.find(_q(_DC, "creator")) if info is not None else None
        date = info.find(_q(_DC, "date")) if info is not None else None
        regions[identifier] = _ChangedRegion(
            kind=AnnotationKind.INSERTION if insertion is not None else AnnotationKind.DELETION,
            author=author.text if author is not None else None,
            timestamp=date.text if date is not None else None,
            content=deletion,
        )
    return regions


def _media_type(part: str) -> str:
    return _MEDIA_TYPES.get(PurePosixPath(part).suffix.casefold(), "application/octet-stream")


def _internal_part(href: str) -> str | None:
    """Resolve a package-relative `xlink:href` to a ZIP part name."""
    split = urlsplit(href)
    if split.scheme or split.netloc:
        return None
    path = unquote(split.path).lstrip("/")
    if not path or path.startswith("../"):
        return None
    return str(PurePosixPath(path))


def _asset_span(state: _State, href: str, alt_text: str) -> InlineSpan | None:
    part = _internal_part(href)
    if part is None:
        state.warn(
            "ODT_IMAGE_UNAVAILABLE",
            "An image linked outside the ODT package was not embedded.",
        )
        return None
    if part not in state.archive.namelist():
        state.warn("ODT_IMAGE_UNAVAILABLE", "An embedded image part is missing.")
        return None
    asset = state.asset_by_part.get(part)
    if asset is None:
        suffix = PurePosixPath(part).suffix.casefold()
        safe_suffix = suffix if suffix and suffix[1:].isalnum() else ".bin"
        filename = f"asset-{len(state.assets) + 1:04d}{safe_suffix}"
        asset = ContentAsset(filename, filename, _media_type(part), state.archive.read(part))
        state.assets.append(asset)
        state.asset_by_part[part] = asset
    return InlineSpan(InlineKind.IMAGE, alt_text, asset_id=asset.asset_id)


def _frame_span(element: ElementTree.Element, state: _State) -> InlineSpan | None:
    image = element.find(_q(_DRAW, "image"))
    if image is None:
        return None
    description = element.find(_q(_SVG, "desc"))
    if description is None:
        description = element.find(_q(_SVG, "title"))
    alt_text = (description.text or "") if description is not None else ""
    href = image.get(_q(_XLINK, "href"), "")
    if not href:
        state.warn("ODT_IMAGE_UNAVAILABLE", "An image frame declared no source.")
        return None
    return _asset_span(state, href, alt_text)


def _text_span(state: _State, text: str) -> InlineSpan | None:
    """Classify one literal run against the active tracked-insertion context."""
    if not text:
        return None
    styles = frozenset(state.active_styles)
    if not state.active_insertions:
        return InlineSpan(InlineKind.TEXT, text, styles=styles)
    if state.revision_mode is RevisionMode.ORIGINAL:
        return None
    if state.revision_mode is RevisionMode.MARKUP:
        return InlineSpan(InlineKind.INSERTION, text, styles=styles)
    return InlineSpan(InlineKind.TEXT, text, styles=styles)


def _deletion_spans(state: _State, region: _ChangedRegion) -> list[InlineSpan]:
    if state.revision_mode is RevisionMode.FINAL or region.content is None:
        return []
    parts: list[str] = []
    for child in region.content:
        if child.tag == _q(_OFFICE, "change-info"):
            continue
        parts.extend(
            "".join(node.itertext())
            for node in child.iter()
            if node.tag in {_q(_TEXT, "p"), _q(_TEXT, "h")}
        )
    text = "\n".join(part for part in parts if part)
    if not text:
        return []
    kind = InlineKind.DELETION if state.revision_mode is RevisionMode.MARKUP else InlineKind.TEXT
    return [InlineSpan(kind, text)]


def _annotation_span(element: ElementTree.Element, state: _State) -> InlineSpan | None:
    if state.comment_mode is CommentMode.OMIT:
        return None
    identifier = element.get(_q(_OFFICE, "name")) or f"comment-{state.source_order + 1:04d}"
    author = element.find(_q(_DC, "creator"))
    date = element.find(_q(_DC, "date"))
    text = "\n".join("".join(paragraph.itertext()) for paragraph in element.findall(_q(_TEXT, "p")))
    state.annotation(
        identifier,
        AnnotationKind.COMMENT,
        text=text or None,
        author=author.text if author is not None else None,
        timestamp=date.text if date is not None else None,
    )
    state.warn(
        "INEXACT_COMMENT_ANCHOR",
        "ODT annotation ranges are retained as references without exact text offsets.",
    )
    return InlineSpan(InlineKind.COMMENT_REFERENCE, annotation_id=identifier)


def _note_spans(element: ElementTree.Element, state: _State) -> list[InlineSpan]:
    """Keep a footnote or endnote citation inline and leave its body out of the flow."""
    citation = element.find(_q(_TEXT, "note-citation"))
    state.warn(
        "NOTE_BODY_OMITTED",
        "Footnote and endnote bodies are not part of the normalized reading order.",
    )
    label = "".join(citation.itertext()) if citation is not None else ""
    span = _text_span(state, label)
    return [span] if span is not None else []


def _change_marker_spans(element: ElementTree.Element, state: _State) -> list[InlineSpan]:
    """Apply one tracked-change marker, returning any text the marker itself contributes."""
    identifier = element.get(_q(_TEXT, "change-id"), "")
    region = state.changed_regions.get(identifier)
    if region is None:
        return []
    if element.tag == _q(_TEXT, "change-end"):
        if identifier in state.active_insertions:
            state.active_insertions.remove(identifier)
        return []
    if region.kind is AnnotationKind.INSERTION:
        if element.tag == _q(_TEXT, "change-start"):
            state.active_insertions.append(identifier)
        if state.revision_mode is RevisionMode.MARKUP:
            state.annotation(
                f"revision-{identifier}",
                AnnotationKind.INSERTION,
                author=region.author,
                timestamp=region.timestamp,
            )
            state.warn(
                "INEXACT_REVISION_ANCHOR",
                "ODT tracked changes are retained without exact text offsets.",
            )
        return []
    spans = _deletion_spans(state, region)
    if state.revision_mode is RevisionMode.MARKUP:
        state.annotation(
            f"revision-{identifier}",
            AnnotationKind.DELETION,
            text="".join(span.text for span in spans) or None,
            author=region.author,
            timestamp=region.timestamp,
        )
        state.warn(
            "INEXACT_REVISION_ANCHOR",
            "ODT tracked changes are retained without exact text offsets.",
        )
    return spans


def _append_text(spans: list[InlineSpan], state: _State, text: str) -> None:
    span = _text_span(state, text)
    if span is not None:
        spans.append(span)


def _inline_children(
    element: ElementTree.Element,
    state: _State,
    *,
    link_target: str | None = None,
) -> list[InlineSpan]:
    """Flatten one ODF text container into normalized inline spans."""
    spans: list[InlineSpan] = []
    _append_text(spans, state, element.text or "")
    for child in element:
        tag = child.tag
        if tag == _q(_TEXT, "s"):
            count = child.get(_q(_TEXT, "c"))
            _append_text(spans, state, " " * (int(count) if count and count.isdigit() else 1))
        elif tag == _q(_TEXT, "tab"):
            _append_text(spans, state, "\t")
        elif tag == _q(_TEXT, "line-break"):
            _append_text(spans, state, "\n")
        elif tag == _q(_TEXT, "a"):
            target = child.get(_q(_XLINK, "href")) or None
            spans.extend(_inline_children(child, state, link_target=target))
        elif tag == _q(_TEXT, "span"):
            applied = _resolved_text_styles(child.get(_q(_TEXT, "style-name")), state)
            state.active_styles.extend(applied)
            try:
                spans.extend(_inline_children(child, state, link_target=link_target))
            finally:
                for style in applied:
                    state.active_styles.remove(style)
        elif tag == _q(_DRAW, "frame"):
            span = _frame_span(child, state)
            if span is not None:
                spans.append(span)
        elif tag == _q(_OFFICE, "annotation"):
            span = _annotation_span(child, state)
            if span is not None:
                spans.append(span)
        elif tag == _q(_OFFICE, "annotation-end"):
            pass
        elif tag == _q(_TEXT, "note"):
            spans.extend(_note_spans(child, state))
        elif tag in {
            _q(_TEXT, "change"),
            _q(_TEXT, "change-start"),
            _q(_TEXT, "change-end"),
        }:
            spans.extend(_change_marker_spans(child, state))
        else:
            spans.extend(_inline_children(child, state, link_target=link_target))
        _append_text(spans, state, child.tail or "")
    if link_target is not None:
        return [
            InlineSpan(InlineKind.LINK, span.text, target=link_target, styles=span.styles)
            if span.kind is InlineKind.TEXT
            else span
            for span in spans
        ]
    return spans


def _resolved_text_styles(name: str | None, state: _State) -> tuple[InlineStyle, ...]:
    """Follow one text style's parent chain into its normalized formatting."""
    formatting: set[InlineStyle] = set()
    seen: set[str] = set()
    current = name
    while current and current not in seen:
        seen.add(current)
        style = state.text_styles.get(current)
        if style is None:
            break
        formatting |= style.formatting
        current = style.parent
    return tuple(formatting)


def _resolved_paragraph_style(name: str | None, state: _State) -> _ParagraphStyle | None:
    """Follow `style:parent-style-name` links into one merged paragraph style."""
    chain: list[_ParagraphStyle] = []
    seen: set[str] = set()
    current = name
    while current and current not in seen:
        seen.add(current)
        style = state.paragraph_styles.get(current)
        if style is None:
            break
        chain.append(style)
        current = style.parent
    if not chain:
        return None
    return _ParagraphStyle(
        display_name=next((item.display_name for item in chain if item.display_name), ""),
        parent=None,
        outline_level=next(
            (item.outline_level for item in chain if item.outline_level is not None), None
        ),
        formatting=frozenset().union(*(item.formatting for item in chain)),
    )


def _paragraph_style_names(name: str | None, state: _State) -> set[str]:
    """Return every normalized name one paragraph style inherits from.

    Writers routinely derive an automatic style such as `P1` from a document
    style such as `Quotations`, so the whole parent chain has to be inspected.
    """
    names: set[str] = set()
    seen: set[str] = set()
    current = name
    while current and current not in seen:
        seen.add(current)
        names.add(_normalized_style_name(current))
        style = state.paragraph_styles.get(current)
        if style is None:
            break
        names.add(_normalized_style_name(style.display_name))
        current = style.parent
    return names


def _style_heading_level(name: str | None, state: _State) -> int | None:
    """Infer a heading level from an ODF paragraph style name or its parents."""
    style = _resolved_paragraph_style(name, state)
    if style is not None and style.outline_level is not None:
        return min(max(style.outline_level, 1), _MAX_HEADING_LEVEL)
    candidates = {(name or "").replace("_20_", " ")}
    if style is not None:
        candidates.add(style.display_name)
    for candidate in candidates:
        normalized = candidate.casefold().replace(" ", "").replace("_", "")
        if normalized.startswith("heading") and normalized[7:].isdigit():
            return min(max(int(normalized[7:]), 1), _MAX_HEADING_LEVEL)
        if normalized.startswith("標題") and normalized[2:].isdigit():
            return min(max(int(normalized[2:]), 1), _MAX_HEADING_LEVEL)
    return None


def _rendered_number(
    definition: _ListLevel,
    system: OrdinalSystem,
    counters: list[int],
    level: int,
    levels: dict[int, _ListLevel],
) -> str:
    """Render the counters `text:display-levels` asks this level to show, joined by periods."""
    first = max(0, level - definition.display_levels + 1)
    parts: list[str] = []
    for index in range(first, level + 1):
        if not counters[index]:
            continue
        referenced = levels.get(index)
        shown = referenced.system if referenced is not None and referenced.system else system
        parts.append(format_ordinal(counters[index], shown))
    return f"{definition.prefix}{'.'.join(parts)}{definition.suffix}"


def _marker_prefix(state: _State, style_name: str | None, level: int) -> str:
    """Render the visible marker for one list item at the given nesting level."""
    levels = state.list_styles.get(style_name or "", {})
    definition = levels.get(level)
    if definition is None:
        return ""
    counters = state.list_counters.setdefault(style_name or "", [0] * _MAX_LIST_LEVELS)
    counters[level] = counters[level] + 1 if counters[level] else definition.start_value
    for deeper in range(level + 1, _MAX_LIST_LEVELS):
        counters[deeper] = 0
    if definition.system is None:
        return ""
    rendered = _rendered_number(definition, definition.system, counters, level, levels)
    return f"{rendered} " if rendered else ""


def _outline_prefix(state: _State, level: int) -> str:
    """Render the chapter-numbering marker `text:outline-style` assigns to a heading."""
    index = level - 1
    definition = state.outline_levels.get(index)
    counters = state.outline_counters
    counters[index] = (
        counters[index] + 1
        if counters[index]
        else (definition.start_value if definition is not None else 1)
    )
    for deeper in range(index + 1, _MAX_HEADING_LEVEL):
        counters[deeper] = 0
    if definition is None or definition.system is None:
        return ""
    rendered = _rendered_number(
        definition, definition.system, counters, index, state.outline_levels
    )
    return f"{rendered} " if rendered else ""


def _paragraph_block(
    element: ElementTree.Element,
    state: _State,
    anchor: SourceAnchor,
    *,
    list_level: int | None,
    list_style: str | None,
    numbered: bool,
    list_leading: bool,
) -> ContentBlock:
    style_name = element.get(_q(_TEXT, "style-name"))
    heading_attribute = element.get(_q(_TEXT, "outline-level"))
    heading_level: int | None = None
    if element.tag == _q(_TEXT, "h"):
        heading_level = (
            min(max(int(heading_attribute), 1), _MAX_HEADING_LEVEL)
            if heading_attribute is not None and heading_attribute.isdigit()
            else _style_heading_level(style_name, state) or 1
        )
    elif list_level is None:
        heading_level = _style_heading_level(style_name, state)
    resolved = _resolved_paragraph_style(style_name, state)
    applied = tuple(resolved.formatting) if resolved is not None else ()
    state.active_styles.extend(applied)
    try:
        spans = _inline_children(element, state)
    finally:
        for style in applied:
            state.active_styles.remove(style)
    style_names = _paragraph_style_names(style_name, state)
    quote_level = 1 if style_names & _QUOTE_STYLE_NAMES else None
    if heading_level is not None:
        kind = BlockKind.HEADING
        if element.get(_q(_TEXT, "is-list-header")) != "true":
            prefix = _outline_prefix(state, heading_level)
            if prefix:
                spans.insert(0, InlineSpan(InlineKind.TEXT, prefix))
    elif list_level is not None:
        kind = BlockKind.LIST_ITEM if list_leading else BlockKind.PARAGRAPH
        if numbered and list_leading:
            prefix = _marker_prefix(state, list_style, list_level)
            if prefix:
                spans.insert(0, InlineSpan(InlineKind.TEXT, prefix))
    elif style_names & _CODE_BLOCK_STYLE_NAMES:
        kind = BlockKind.CODE_BLOCK
    else:
        kind = BlockKind.PARAGRAPH
    return ContentBlock(
        kind,
        tuple(spans),
        level=heading_level,
        list_level=None if kind is BlockKind.HEADING else list_level,
        quote_level=quote_level,
        source_anchor=anchor,
    )


def _cell_spans(cell: ElementTree.Element, state: _State) -> tuple[InlineSpan, ...]:
    spans: list[InlineSpan] = []
    for paragraph in cell.iter():
        if paragraph.tag not in {_q(_TEXT, "p"), _q(_TEXT, "h")}:
            continue
        if spans:
            spans.append(InlineSpan(InlineKind.TEXT, "\n"))
        spans.extend(_inline_children(paragraph, state))
    return tuple(spans)


def _table_block(element: ElementTree.Element, state: _State, anchor: SourceAnchor) -> ContentBlock:
    rows: list[tuple[tuple[InlineSpan, ...], ...]] = []
    widths: set[int] = set()
    merged = False
    for row in element.iter(_q(_TABLE, "table-row")):
        cells: list[tuple[InlineSpan, ...]] = []
        for cell in row:
            if cell.tag == _q(_TABLE, "covered-table-cell"):
                merged = True
                cells.append(())
                continue
            if cell.tag != _q(_TABLE, "table-cell"):
                continue
            if cell.get(_q(_TABLE, "number-rows-spanned")) not in {None, "1"}:
                merged = True
            repeat = cell.get(_q(_TABLE, "number-columns-repeated"))
            count = int(repeat) if repeat is not None and repeat.isdigit() else 1
            spans = _cell_spans(cell, state)
            cells.extend([spans] * min(count, 64))
        widths.add(len(cells))
        rows.append(tuple(cells))
    if len(widths) > 1 or merged:
        state.warn(
            "INCOMPLETE_TABLE_STRUCTURE",
            "A table has merged or uneven cells that cannot be represented exactly.",
        )
    return ContentBlock(BlockKind.TABLE, rows=tuple(rows), source_anchor=anchor)


def _list_blocks(
    element: ElementTree.Element,
    state: _State,
    *,
    element_path: str,
    level: int,
    inherited_style: str | None,
) -> list[ContentBlock]:
    """Walk one `text:list` subtree, tracking nesting depth and marker continuation."""
    style_name = element.get(_q(_TEXT, "style-name")) or inherited_style
    counters = state.list_counters.setdefault(style_name or "", [0] * _MAX_LIST_LEVELS)
    continued = element.get(_q(_TEXT, "continue-numbering")) == "true" or element.get(
        _q(_TEXT, "continue-list")
    )
    if not continued:
        for index in range(level, _MAX_LIST_LEVELS):
            counters[index] = 0
    blocks: list[ContentBlock] = []
    depth = min(level, _MAX_LIST_LEVELS - 1)
    for index, item in enumerate(element, start=1):
        if item.tag not in {_q(_TEXT, "list-item"), _q(_TEXT, "list-header")}:
            continue
        numbered = item.tag == _q(_TEXT, "list-item")
        item_path = f"{element_path}/{_prefixed_name(item.tag)}[{index}]"
        blocks.extend(
            _blocks(
                item,
                state,
                element_path=item_path,
                list_level=depth,
                list_style=style_name,
                numbered=numbered,
            )
        )
    return blocks


def _textbox_contents(element: ElementTree.Element) -> list[ElementTree.Element]:
    """Collect drawing text boxes anchored to a paragraph, which hold their own flow."""
    contents: list[ElementTree.Element] = []
    for child in element.iter(_q(_DRAW, "text-box")):
        contents.append(child)
    return contents


def _blocks(
    element: ElementTree.Element,
    state: _State,
    *,
    element_path: str,
    list_level: int | None = None,
    list_style: str | None = None,
    numbered: bool = True,
) -> list[ContentBlock]:
    """Convert one ODF container's children into normalized blocks in reading order."""
    blocks: list[ContentBlock] = []
    tag_counts: dict[str, int] = {}
    first_item_paragraph = True
    for child in element:
        qualified = _prefixed_name(child.tag)
        tag_counts[qualified] = tag_counts.get(qualified, 0) + 1
        child_path = f"{element_path}/{qualified}[{tag_counts[qualified]}]"
        anchor = SourceAnchor(
            "odf-element",
            part=_CONTENT_PART,
            element_path=child_path,
            native_id=child.get(_q(_TEXT, "id")),
        )
        if child.tag in {_q(_TEXT, "p"), _q(_TEXT, "h")}:
            for box_index, box in enumerate(_textbox_contents(child), start=1):
                blocks.extend(
                    _blocks(box, state, element_path=f"{child_path}/draw:text-box[{box_index}]")
                )
            # Only a list item's first paragraph carries the marker; the rest continue it.
            paragraph = _paragraph_block(
                child,
                state,
                anchor,
                list_level=list_level,
                list_style=list_style,
                numbered=numbered,
                list_leading=first_item_paragraph,
            )
            first_item_paragraph = False
            if paragraph.inlines:
                blocks.append(paragraph)
        elif child.tag == _q(_TABLE, "table"):
            blocks.append(_table_block(child, state, anchor))
        elif child.tag == _q(_TEXT, "list"):
            blocks.extend(
                _list_blocks(
                    child,
                    state,
                    element_path=child_path,
                    level=0 if list_level is None else list_level + 1,
                    inherited_style=list_style,
                )
            )
        elif child.tag in {
            _q(_TEXT, "section"),
            _q(_TEXT, "index-body"),
            _q(_TEXT, "index-title"),
            _q(_TEXT, "table-of-content"),
            _q(_TEXT, "illustration-index"),
            _q(_TEXT, "table-index"),
            _q(_TEXT, "alphabetical-index"),
            _q(_TEXT, "user-index"),
            _q(_TEXT, "bibliography"),
            _q(_TEXT, "soft-page-break"),
        }:
            blocks.extend(
                _blocks(
                    child,
                    state,
                    element_path=child_path,
                    list_level=list_level,
                    list_style=list_style,
                    numbered=numbered,
                )
            )
    return blocks


def _warn_about_headers_and_footers(archive: ZipFile, state: _State) -> None:
    root = _optional_xml(archive, _STYLES_PART)
    if root is None:
        return
    for master in root.iter(_q(_STYLE, "master-page")):
        if any(
            child.tag in {_q(_STYLE, "header"), _q(_STYLE, "footer")} and len(child) > 0
            for child in master
        ):
            state.warn(
                "HEADER_FOOTER_OMITTED",
                "Headers and footers are not part of the normalized reading order.",
            )
            return


def extract_odt_content(
    source_path: Path,
    *,
    revision_mode: RevisionMode = RevisionMode.FINAL,
    comment_mode: CommentMode = CommentMode.OMIT,
    include_annotation_metadata: bool = False,
    metadata_detail: MetadataDetail = MetadataDetail.BASIC,
) -> NormalizedContent:
    """Extract a validated ODT directly from ODF XML without modifying the source."""
    validate_source_document(source_path, SourceFormat.ODT)
    with ZipFile(source_path) as archive:
        content_root = _parse_xml(archive, _CONTENT_PART)
        style_roots = tuple(
            root
            for root in (content_root, _optional_xml(archive, _STYLES_PART))
            if root is not None
        )
        paragraph_styles, list_styles, outline_levels, text_styles = _collect_styles(style_roots)
        body = content_root.find(f"{_q(_OFFICE, 'body')}/{_q(_OFFICE, 'text')}")
        if body is None:
            raise InvalidInputError("ODT document has no text body")
        state = _State(
            archive=archive,
            revision_mode=revision_mode,
            comment_mode=comment_mode,
            include_metadata=include_annotation_metadata,
            paragraph_styles=paragraph_styles,
            list_styles=list_styles,
            outline_levels=outline_levels,
            changed_regions=_changed_regions(body),
            text_styles=text_styles,
        )
        blocks = _blocks(body, state, element_path="/office:document-content/office:body")
        _warn_about_headers_and_footers(archive, state)
        metadata = None if metadata_detail is MetadataDetail.NONE else _document_metadata(archive)
        layout = LayoutMetadata()
        if metadata_detail is MetadataDetail.LAYOUT:
            layout = LayoutMetadata(LayoutAvailability.UNAVAILABLE)
            state.warn(
                "LAYOUT_METADATA_UNAVAILABLE",
                "ODT layout metadata requires a configured layout provider.",
            )
        return NormalizedContent(
            source_format=SourceFormat.ODT,
            blocks=tuple(blocks),
            assets=tuple(state.assets),
            annotations=tuple(state.annotations),
            warnings=tuple(state.warnings),
            metadata=metadata,
            layout=layout,
            source_sha256=file_sha256(source_path),
        )
