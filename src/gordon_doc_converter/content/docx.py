"""Direct OOXML extraction into the engine-neutral semantic content model."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree
from zipfile import ZipFile

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

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_PR = "http://schemas.openxmlformats.org/package/2006/relationships"
_MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
_W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
_CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
_DC = "http://purl.org/dc/elements/1.1/"
_DCTERMS = "http://purl.org/dc/terms/"


def _q(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


@dataclass(frozen=True, slots=True)
class _Relationship:
    target: str
    external: bool


@dataclass(frozen=True, slots=True)
class _Style:
    name: str
    based_on: str | None
    outline_level: int | None
    num_id: str | None
    list_level: int | None


@dataclass(frozen=True, slots=True)
class _NumberLevel:
    start: int
    number_format: str
    level_text: str


@dataclass(frozen=True, slots=True)
class _NumberingDefinition:
    abstract_id: str
    levels: dict[int, _NumberLevel]


@dataclass(slots=True)
class _State:
    archive: ZipFile
    relationships: dict[str, _Relationship]
    revision_mode: RevisionMode
    comment_mode: CommentMode
    include_metadata: bool
    assets: list[ContentAsset]
    annotations: list[NormalizedAnnotation]
    warnings: list[ConversionWarning]
    asset_by_part: dict[str, ContentAsset]
    comments: dict[str, ElementTree.Element]
    emitted_comments: set[str]
    styles: dict[str, _Style]
    numbering: dict[str, _NumberingDefinition]
    counters: dict[str, list[int]]
    manual_list_indents: list[tuple[int, int]]
    source_order: int = 0

    def annotation(
        self,
        annotation_id: str,
        kind: AnnotationKind,
        element: ElementTree.Element,
        *,
        text: str | None = None,
    ) -> None:
        author = element.get(_q(_W, "author")) if self.include_metadata else None
        timestamp = element.get(_q(_W, "date")) if self.include_metadata else None
        self.annotations.append(
            NormalizedAnnotation(
                annotation_id=annotation_id,
                kind=kind,
                source_order=self.source_order,
                anchor=AnnotationAnchor(exact=False),
                text=text,
                author=author,
                timestamp=timestamp,
            )
        )
        self.source_order += 1


def _parse_xml(archive: ZipFile, name: str) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(archive.read(name))
    except (KeyError, ElementTree.ParseError) as exc:
        raise InvalidInputError(f"DOCX contains an invalid {name} part") from exc


def _core_properties(archive: ZipFile) -> DocumentMetadata:
    if "docProps/core.xml" not in archive.namelist():
        return DocumentMetadata()
    root = _parse_xml(archive, "docProps/core.xml")

    def text(namespace: str, name: str) -> str | None:
        element = root.find(_q(namespace, name))
        return element.text if element is not None and element.text else None

    return DocumentMetadata(
        title=text(_DC, "title"),
        subject=text(_DC, "subject"),
        creator=text(_DC, "creator"),
        keywords=text(_CP, "keywords"),
        created=text(_DCTERMS, "created"),
        modified=text(_DCTERMS, "modified"),
    )


def _relationships(archive: ZipFile) -> dict[str, _Relationship]:
    name = "word/_rels/document.xml.rels"
    if name not in archive.namelist():
        return {}
    root = _parse_xml(archive, name)
    return {
        element.get("Id", ""): _Relationship(
            target=element.get("Target", ""),
            external=element.get("TargetMode") == "External",
        )
        for element in root.findall(_q(_PR, "Relationship"))
        if element.get("Id")
    }


def _integer_attribute(element: ElementTree.Element | None, name: str) -> int | None:
    if element is None:
        return None
    value = element.get(_q(_W, name))
    return int(value) if value is not None and value.isdigit() else None


def _styles(archive: ZipFile) -> dict[str, _Style]:
    if "word/styles.xml" not in archive.namelist():
        return {}
    root = _parse_xml(archive, "word/styles.xml")
    styles: dict[str, _Style] = {}
    for element in root.findall(_q(_W, "style")):
        style_id = element.get(_q(_W, "styleId"))
        if not style_id:
            continue
        properties = element.find(_q(_W, "pPr"))
        num_properties = properties.find(_q(_W, "numPr")) if properties is not None else None
        name = element.find(_q(_W, "name"))
        based_on = element.find(_q(_W, "basedOn"))
        num_id = num_properties.find(_q(_W, "numId")) if num_properties is not None else None
        styles[style_id] = _Style(
            name.get(_q(_W, "val"), "") if name is not None else "",
            based_on.get(_q(_W, "val")) if based_on is not None else None,
            _integer_attribute(
                properties.find(_q(_W, "outlineLvl")) if properties is not None else None,
                "val",
            ),
            num_id.get(_q(_W, "val")) if num_id is not None else None,
            _integer_attribute(
                num_properties.find(_q(_W, "ilvl")) if num_properties is not None else None,
                "val",
            ),
        )
    return styles


def _number_level(element: ElementTree.Element) -> _NumberLevel:
    start = _integer_attribute(element.find(_q(_W, "start")), "val") or 1
    number_format = element.find(_q(_W, "numFmt"))
    level_text = element.find(_q(_W, "lvlText"))
    return _NumberLevel(
        start,
        number_format.get(_q(_W, "val"), "decimal") if number_format is not None else "decimal",
        level_text.get(_q(_W, "val"), "") if level_text is not None else "",
    )


def _numbering(archive: ZipFile) -> dict[str, _NumberingDefinition]:
    if "word/numbering.xml" not in archive.namelist():
        return {}
    root = _parse_xml(archive, "word/numbering.xml")
    abstract: dict[str, dict[int, _NumberLevel]] = {}
    for definition in root.findall(_q(_W, "abstractNum")):
        identifier = definition.get(_q(_W, "abstractNumId"))
        if identifier:
            abstract[identifier] = {
                level: _number_level(element)
                for element in definition.findall(_q(_W, "lvl"))
                if (level := _integer_attribute(element, "ilvl")) is not None
            }
    numbering: dict[str, _NumberingDefinition] = {}
    for instance in root.findall(_q(_W, "num")):
        num_id = instance.get(_q(_W, "numId"))
        abstract_id = instance.find(_q(_W, "abstractNumId"))
        if not num_id or abstract_id is None:
            continue
        abstract_value = abstract_id.get(_q(_W, "val"), "")
        levels = dict(abstract.get(abstract_value, {}))
        for override in instance.findall(_q(_W, "lvlOverride")):
            level = _integer_attribute(override, "ilvl")
            if level is None:
                continue
            replacement = override.find(_q(_W, "lvl"))
            if replacement is not None:
                levels[level] = _number_level(replacement)
            start_override = _integer_attribute(override.find(_q(_W, "startOverride")), "val")
            if start_override is not None and level in levels:
                current = levels[level]
                levels[level] = _NumberLevel(
                    start_override, current.number_format, current.level_text
                )
        numbering[num_id] = _NumberingDefinition(abstract_value, levels)
    return numbering


def _media_type(filename: str) -> str:
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".svg": "image/svg+xml",
        ".emf": "image/emf",
        ".wmf": "image/wmf",
    }.get(Path(filename).suffix.casefold(), "application/octet-stream")


def _asset_span(state: _State, relationship_id: str, alt_text: str) -> InlineSpan | None:
    relationship = state.relationships.get(relationship_id)
    if relationship is None or relationship.external:
        state.warnings.append(
            ConversionWarning("DOCX_IMAGE_UNAVAILABLE", "An image relationship could not be read.")
        )
        return None
    part = str(PurePosixPath("word", relationship.target))
    if part.startswith("word/../"):
        part = part.removeprefix("word/../")
    if part not in state.archive.namelist():
        state.warnings.append(
            ConversionWarning("DOCX_IMAGE_UNAVAILABLE", "An embedded image part is missing.")
        )
        return None
    asset = state.asset_by_part.get(part)
    if asset is None:
        suffix = Path(part).suffix.casefold()
        safe_suffix = suffix if suffix and suffix[1:].isalnum() else ".bin"
        filename = f"asset-{len(state.assets) + 1:04d}{safe_suffix}"
        asset = ContentAsset(filename, filename, _media_type(part), state.archive.read(part))
        state.assets.append(asset)
        state.asset_by_part[part] = asset
    return InlineSpan(InlineKind.IMAGE, alt_text, asset_id=asset.asset_id)


def _comment_reference_span(element: ElementTree.Element, state: _State) -> InlineSpan | None:
    if state.comment_mode is CommentMode.OMIT:
        return None
    source_id = element.get(_q(_W, "id"), "unknown")
    identifier = f"comment-{source_id}"
    if source_id not in state.emitted_comments:
        comment = state.comments.get(source_id, element)
        text = "".join(node.text or "" for node in comment.iter(_q(_W, "t")))
        state.annotation(identifier, AnnotationKind.COMMENT, comment, text=text or None)
        state.emitted_comments.add(source_id)
    return InlineSpan(InlineKind.COMMENT_REFERENCE, annotation_id=identifier)


def _run_text(element: ElementTree.Element) -> str:
    text_parts: list[str] = []
    for child in element:
        if child.tag == _q(_W, "txbxContent"):
            continue
        if child.tag in {_q(_W, "t"), _q(_W, "delText")}:
            text_parts.append(child.text or "")
        elif child.tag == _q(_W, "tab"):
            text_parts.append("\t")
        elif child.tag == _q(_W, "br"):
            text_parts.append("\n")
        else:
            text_parts.append(_run_text(child))
    return "".join(text_parts)


def _run_spans(element: ElementTree.Element, state: _State) -> list[InlineSpan]:
    spans: list[InlineSpan] = []
    text = _run_text(element)
    if text:
        spans.append(InlineSpan(InlineKind.TEXT, text))
    for drawing in element.iter(_q(_A, "blip")):
        relationship_id = drawing.get(_q(_R, "embed"))
        if relationship_id:
            description = ""
            doc_properties = element.find(f".//{{{_W}}}drawing/..")
            if doc_properties is not None:
                description = doc_properties.get("descr", "")
            span = _asset_span(state, relationship_id, description)
            if span is not None:
                spans.append(span)
    for reference in element.iter(_q(_W, "commentReference")):
        span = _comment_reference_span(reference, state)
        if span is not None:
            spans.append(span)
    return spans


def _inline_children(element: ElementTree.Element, state: _State) -> list[InlineSpan]:
    spans: list[InlineSpan] = []
    for child in element:
        if child.tag == _q(_W, "r"):
            spans.extend(_run_spans(child, state))
        elif child.tag == _q(_W, "hyperlink"):
            nested = _inline_children(child, state)
            relationship = state.relationships.get(child.get(_q(_R, "id"), ""))
            target = (
                relationship.target if relationship is not None and relationship.external else None
            )
            spans.extend(
                InlineSpan(InlineKind.LINK, span.text, target=target)
                if span.kind is InlineKind.TEXT
                else span
                for span in nested
            )
        elif child.tag in {_q(_W, "ins"), _q(_W, "del")}:
            insertion = child.tag == _q(_W, "ins")
            revision_spans: list[InlineSpan] = []
            include = (
                state.revision_mode is RevisionMode.MARKUP
                or (insertion and state.revision_mode is RevisionMode.FINAL)
                or (not insertion and state.revision_mode is RevisionMode.ORIGINAL)
            )
            if include:
                revision_spans = _inline_children(child, state)
                if state.revision_mode is RevisionMode.MARKUP:
                    inline_kind = InlineKind.INSERTION if insertion else InlineKind.DELETION
                    revision_spans = [InlineSpan(inline_kind, span.text) for span in revision_spans]
                spans.extend(revision_spans)
            if state.revision_mode is RevisionMode.MARKUP:
                annotation_kind = AnnotationKind.INSERTION if insertion else AnnotationKind.DELETION
                identifier = f"revision-{state.source_order + 1:04d}"
                state.annotation(
                    identifier,
                    annotation_kind,
                    child,
                    text="".join(span.text for span in revision_spans),
                )
        elif child.tag == _q(_W, "commentReference"):
            span = _comment_reference_span(child, state)
            if span is not None:
                spans.append(span)
        else:
            spans.extend(_inline_children(child, state))
    return spans


def _load_comments(archive: ZipFile, comment_mode: CommentMode) -> dict[str, ElementTree.Element]:
    if comment_mode is CommentMode.OMIT or "word/comments.xml" not in archive.namelist():
        return {}
    root = _parse_xml(archive, "word/comments.xml")
    return {
        comment.get(_q(_W, "id"), "unknown"): comment for comment in root.findall(_q(_W, "comment"))
    }


def _warn_about_comment_anchors(state: _State) -> None:
    if state.emitted_comments:
        state.warnings.append(
            ConversionWarning(
                "INEXACT_COMMENT_ANCHOR",
                "DOCX comment ranges are retained as references without exact text offsets.",
            )
        )


def _warn_about_revision_anchors(state: _State) -> None:
    if any(
        annotation.kind in {AnnotationKind.INSERTION, AnnotationKind.DELETION}
        for annotation in state.annotations
    ):
        state.warnings.append(
            ConversionWarning(
                "INEXACT_REVISION_ANCHOR",
                "DOCX revision ranges are retained without exact text offsets.",
            )
        )


def _resolved_style(style_id: str, state: _State) -> _Style | None:
    chain: list[_Style] = []
    seen: set[str] = set()
    while style_id and style_id not in seen:
        seen.add(style_id)
        style = state.styles.get(style_id)
        if style is None:
            break
        chain.append(style)
        style_id = style.based_on or ""
    if not chain:
        return None
    return _Style(
        next((item.name for item in chain if item.name), ""),
        None,
        next((item.outline_level for item in chain if item.outline_level is not None), None),
        next((item.num_id for item in chain if item.num_id is not None), None),
        next((item.list_level for item in chain if item.list_level is not None), None),
    )


def _heading_level(style_id: str, style: _Style | None) -> int | None:
    if style is not None and style.outline_level is not None and style.outline_level < 6:
        return style.outline_level + 1
    names = {style_id.casefold().replace(" ", "")}
    if style is not None:
        names.add(style.name.casefold().replace(" ", ""))
    for name in names:
        if name.startswith("heading") and name[7:].isdigit():
            return min(max(int(name[7:]), 1), 6)
        if name.startswith("標題") and name[2:].isdigit():
            return min(max(int(name[2:]), 1), 6)
    chinese_levels = {"章名": 1, "節名": 2, "小節": 3, "小小節": 4}
    return next((chinese_levels[name] for name in names if name in chinese_levels), None)


def _traditional_number(value: int, *, financial: bool = False) -> str:
    digits = "零壹貳參肆伍陸柒捌玖" if financial else "零一二三四五六七八九"
    units = ("", "拾", "佰", "仟") if financial else ("", "十", "百", "千")
    if value <= 0 or value >= 10000:
        return str(value)
    result = ""
    pending_zero = False
    for position in range(3, -1, -1):
        divisor = 10**position
        digit, value = divmod(value, divisor)
        if digit:
            if pending_zero and result:
                result += digits[0]
            if not (digit == 1 and position == 1 and not result and not financial):
                result += digits[digit]
            result += units[position]
            pending_zero = False
        elif result and value:
            pending_zero = True
    return result


def _format_number(value: int, number_format: str) -> str:
    if number_format in {"ideographTraditional", "taiwaneseCountingThousand"}:
        return _traditional_number(value)
    if number_format == "ideographLegalTraditional":
        return _traditional_number(value, financial=True)
    if number_format == "lowerLetter":
        return chr(ord("a") + (value - 1) % 26)
    if number_format == "upperLetter":
        return chr(ord("A") + (value - 1) % 26)
    if number_format in {"lowerRoman", "upperRoman"}:
        parts: list[str] = []
        remainder = value
        for amount, token in (
            (1000, "M"),
            (900, "CM"),
            (500, "D"),
            (400, "CD"),
            (100, "C"),
            (90, "XC"),
            (50, "L"),
            (40, "XL"),
            (10, "X"),
            (9, "IX"),
            (5, "V"),
            (4, "IV"),
            (1, "I"),
        ):
            while remainder >= amount:
                parts.append(token)
                remainder -= amount
        rendered = "".join(parts)
        return rendered.lower() if number_format == "lowerRoman" else rendered
    return str(value)


def _number_prefix(num_id: str | None, level: int | None, state: _State) -> str:
    if num_id is None:
        return ""
    numbering = state.numbering.get(num_id)
    if numbering is None:
        return ""
    levels = numbering.levels
    list_level = level or 0
    definition = levels.get(list_level)
    if definition is None:
        return ""
    counters = state.counters.setdefault(num_id, [0] * 9)
    counters[list_level] = counters[list_level] + 1 if counters[list_level] else definition.start
    for sibling_id, sibling_counters in state.counters.items():
        sibling = state.numbering.get(sibling_id)
        if sibling is None or sibling.abstract_id != numbering.abstract_id:
            continue
        for deeper in range(list_level + 1, len(sibling_counters)):
            sibling_counters[deeper] = 0
    if definition.number_format == "bullet":
        return f"{definition.level_text} "
    rendered = definition.level_text
    for referenced_level in range(9):
        placeholder = f"%{referenced_level + 1}"
        if placeholder not in rendered:
            continue
        referenced = levels.get(referenced_level)
        value = counters[referenced_level]
        replacement = (
            _format_number(value, referenced.number_format)
            if referenced is not None and value
            else ""
        )
        rendered = rendered.replace(placeholder, replacement)
    return f"{rendered} " if rendered else ""


_MANUAL_NUMBER = re.compile(
    r"^(?:[\(（][0-9一二三四五六七八九十]+[\)）]|[A-Za-z][.)、]|[0-9]+[.)、])"
)


def _manual_list_level(
    text: str, properties: ElementTree.Element | None, state: _State
) -> int | None:
    if not _MANUAL_NUMBER.match(text):
        return None
    indentation = properties.find(_q(_W, "ind")) if properties is not None else None
    left = _integer_attribute(indentation, "left")
    if left is None:
        left = _integer_attribute(indentation, "start")
    if left is None:
        return None
    hanging = _integer_attribute(indentation, "hanging") or 0
    while state.manual_list_indents and left < state.manual_list_indents[-1][0]:
        state.manual_list_indents.pop()
    if not state.manual_list_indents or left > state.manual_list_indents[-1][0]:
        state.manual_list_indents.append((left, hanging))
    return len(state.manual_list_indents) - 1


def _manual_continuation_level(properties: ElementTree.Element | None, state: _State) -> int | None:
    indentation = properties.find(_q(_W, "ind")) if properties is not None else None
    left = _integer_attribute(indentation, "left")
    if left is None:
        left = _integer_attribute(indentation, "start")
    if left is None:
        state.manual_list_indents.clear()
        return None
    for level in range(len(state.manual_list_indents) - 1, -1, -1):
        marker_left, hanging = state.manual_list_indents[level]
        if left >= marker_left - hanging:
            return level
    state.manual_list_indents.clear()
    return None


def _paragraph(
    element: ElementTree.Element,
    state: _State,
    source_anchor: SourceAnchor | None = None,
) -> ContentBlock:
    properties = element.find(_q(_W, "pPr"))
    style = properties.find(_q(_W, "pStyle")) if properties is not None else None
    style_value = style.get(_q(_W, "val"), "") if style is not None else ""
    style_definition = _resolved_style(style_value, state)
    heading_level = _heading_level(style_value, style_definition)
    numbering = properties.find(_q(_W, "numPr")) if properties is not None else None
    num_id_element = numbering.find(_q(_W, "numId")) if numbering is not None else None
    level_element = numbering.find(_q(_W, "ilvl")) if numbering is not None else None
    num_id = (
        num_id_element.get(_q(_W, "val"))
        if num_id_element is not None
        else style_definition.num_id
        if style_definition is not None
        else None
    )
    numbering_disabled = num_id_element is not None and num_id == "0"
    if numbering_disabled:
        num_id = None
    list_level = (
        _integer_attribute(level_element, "val")
        if level_element is not None
        else style_definition.list_level
        if style_definition is not None
        else None
    )
    custom_heading_names = {"章名", "節名", "小節", "小小節"}
    # A style merely named like a heading yields to numbering the paragraph declares itself.
    if (
        heading_level is not None
        and style_definition is not None
        and style_definition.name in custom_heading_names
        and style_definition.outline_level is None
        and num_id_element is not None
    ):
        heading_level = None
    if heading_level is not None:
        kind = BlockKind.HEADING
    elif num_id is not None:
        kind = BlockKind.LIST_ITEM
    else:
        kind = BlockKind.PARAGRAPH
    spans = _inline_children(element, state)
    prefix = _number_prefix(num_id, list_level, state)
    if prefix:
        spans.insert(0, InlineSpan(InlineKind.TEXT, prefix))
    manual_level = None
    if kind is BlockKind.PARAGRAPH and numbering_disabled:
        manual_level = _manual_list_level("".join(span.text for span in spans), properties, state)
        if manual_level is not None:
            kind = BlockKind.LIST_ITEM
    continuation_level = None
    if kind is BlockKind.PARAGRAPH and manual_level is None and state.manual_list_indents:
        continuation_level = _manual_continuation_level(properties, state)
    if heading_level is not None or (num_id is not None and kind is BlockKind.LIST_ITEM):
        state.manual_list_indents.clear()
    return ContentBlock(
        kind,
        tuple(spans),
        level=heading_level,
        list_level=(
            list_level
            if kind is BlockKind.LIST_ITEM and num_id is not None
            else manual_level
            if manual_level is not None
            else continuation_level
        ),
        source_anchor=source_anchor,
    )


def _table(
    element: ElementTree.Element,
    state: _State,
    source_anchor: SourceAnchor | None = None,
) -> ContentBlock:
    rows: list[tuple[tuple[InlineSpan, ...], ...]] = []
    widths: set[int] = set()
    for row in element.findall(_q(_W, "tr")):
        cells: list[tuple[InlineSpan, ...]] = []
        for cell in row.findall(_q(_W, "tc")):
            spans: list[InlineSpan] = []
            for paragraph in cell.findall(_q(_W, "p")):
                if spans:
                    spans.append(InlineSpan(InlineKind.TEXT, "\n"))
                spans.extend(_paragraph(paragraph, state).inlines)
            cells.append(tuple(spans))
        widths.add(len(cells))
        rows.append(tuple(cells))
    if len(widths) > 1 or element.find(f".//{{{_W}}}vMerge") is not None:
        state.warnings.append(
            ConversionWarning(
                "INCOMPLETE_TABLE_STRUCTURE",
                "A table has merged or uneven cells that cannot be represented exactly.",
            )
        )
    return ContentBlock(BlockKind.TABLE, rows=tuple(rows), source_anchor=source_anchor)


def _textbox_contents(element: ElementTree.Element) -> list[ElementTree.Element]:
    contents: list[ElementTree.Element] = []
    for child in element:
        if child.tag == _q(_W, "txbxContent"):
            contents.append(child)
        elif child.tag == _q(_MC, "AlternateContent"):
            choice = child.find(_q(_MC, "Choice"))
            fallback = child.find(_q(_MC, "Fallback"))
            selected = choice if choice is not None else fallback
            if selected is not None:
                contents.extend(_textbox_contents(selected))
        else:
            contents.extend(_textbox_contents(child))
    return contents


def _blocks(
    element: ElementTree.Element,
    state: _State,
    *,
    element_path: str,
) -> list[ContentBlock]:
    blocks: list[ContentBlock] = []
    tag_counts: dict[str, int] = {}
    for child in element:
        local_name = child.tag.rsplit("}", 1)[-1]
        tag_counts[local_name] = tag_counts.get(local_name, 0) + 1
        child_path = f"{element_path}/w:{local_name}[{tag_counts[local_name]}]"
        anchor = SourceAnchor(
            "ooxml-element",
            part="word/document.xml",
            element_path=child_path,
            native_id=child.get(_q(_W14, "paraId")),
        )
        if child.tag == _q(_W, "p"):
            for textbox_index, textbox in enumerate(_textbox_contents(child), start=1):
                blocks.extend(
                    _blocks(
                        textbox,
                        state,
                        element_path=f"{child_path}/textbox[{textbox_index}]",
                    )
                )
            paragraph = _paragraph(child, state, anchor)
            if paragraph.inlines:
                blocks.append(paragraph)
        elif child.tag == _q(_W, "tbl"):
            blocks.append(_table(child, state, anchor))
        elif child.tag in {_q(_W, "sdt"), _q(_W, "sdtContent"), _q(_W, "customXml")}:
            blocks.extend(_blocks(child, state, element_path=child_path))
    return blocks


def extract_docx_content(
    source_path: Path,
    *,
    revision_mode: RevisionMode = RevisionMode.FINAL,
    comment_mode: CommentMode = CommentMode.OMIT,
    include_annotation_metadata: bool = False,
    metadata_detail: MetadataDetail = MetadataDetail.BASIC,
) -> NormalizedContent:
    """Extract a validated DOCX directly from OOXML without modifying the source."""
    validate_source_document(source_path, SourceFormat.DOCX)
    with ZipFile(source_path) as archive:
        state = _State(
            archive,
            _relationships(archive),
            revision_mode,
            comment_mode,
            include_annotation_metadata,
            [],
            [],
            [],
            {},
            _load_comments(archive, comment_mode),
            set(),
            _styles(archive),
            _numbering(archive),
            {},
            [],
        )
        root = _parse_xml(archive, "word/document.xml")
        body = root.find(_q(_W, "body"))
        if body is None:
            raise InvalidInputError("DOCX document has no body")
        blocks = _blocks(body, state, element_path="/w:document/w:body")
        _warn_about_comment_anchors(state)
        _warn_about_revision_anchors(state)
        metadata = None if metadata_detail is MetadataDetail.NONE else _core_properties(archive)
        layout = LayoutMetadata()
        if metadata_detail is MetadataDetail.LAYOUT:
            layout = LayoutMetadata(LayoutAvailability.UNAVAILABLE)
            state.warnings.append(
                ConversionWarning(
                    "LAYOUT_METADATA_UNAVAILABLE",
                    "DOCX layout metadata requires a configured layout provider.",
                )
            )
        if any(name.startswith(("word/header", "word/footer")) for name in archive.namelist()):
            state.warnings.append(
                ConversionWarning(
                    "HEADER_FOOTER_OMITTED",
                    "Headers and footers are not part of the normalized reading order.",
                )
            )
        return NormalizedContent(
            source_format=SourceFormat.DOCX,
            blocks=tuple(blocks),
            assets=tuple(state.assets),
            annotations=tuple(state.annotations),
            warnings=tuple(state.warnings),
            metadata=metadata,
            layout=layout,
            source_sha256=file_sha256(source_path),
        )
