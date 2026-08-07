"""Direct OOXML extraction into the engine-neutral semantic content model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree
from zipfile import ZipFile

from gordon_doc_converter.content.models import (
    BlockKind,
    ContentAsset,
    ContentBlock,
    InlineKind,
    InlineSpan,
    NormalizedContent,
)
from gordon_doc_converter.exceptions import InvalidInputError
from gordon_doc_converter.models import (
    AnnotationAnchor,
    AnnotationKind,
    CommentMode,
    ConversionWarning,
    NormalizedAnnotation,
    RevisionMode,
    SourceFormat,
)
from gordon_doc_converter.security import validate_source_document

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_PR = "http://schemas.openxmlformats.org/package/2006/relationships"


def _q(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


@dataclass(frozen=True, slots=True)
class _Relationship:
    target: str
    external: bool


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


def _run_spans(element: ElementTree.Element, state: _State) -> list[InlineSpan]:
    spans: list[InlineSpan] = []
    text_parts: list[str] = []
    for child in element.iter():
        if child.tag in {_q(_W, "t"), _q(_W, "delText")}:
            text_parts.append(child.text or "")
        elif child.tag == _q(_W, "tab"):
            text_parts.append("\t")
        elif child.tag == _q(_W, "br"):
            text_parts.append("\n")
    text = "".join(text_parts)
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


def _paragraph(element: ElementTree.Element, state: _State) -> ContentBlock:
    properties = element.find(_q(_W, "pPr"))
    style = properties.find(_q(_W, "pStyle")) if properties is not None else None
    style_value = style.get(_q(_W, "val"), "") if style is not None else ""
    heading_level: int | None = None
    normalized_style = style_value.casefold().replace(" ", "")
    if normalized_style.startswith("heading") and normalized_style[7:].isdigit():
        heading_level = min(max(int(normalized_style[7:]), 1), 6)
    numbering = properties.find(_q(_W, "numPr")) if properties is not None else None
    if heading_level is not None:
        kind = BlockKind.HEADING
    elif numbering is not None:
        kind = BlockKind.LIST_ITEM
    else:
        kind = BlockKind.PARAGRAPH
    return ContentBlock(kind, tuple(_inline_children(element, state)), level=heading_level)


def _table(element: ElementTree.Element, state: _State) -> ContentBlock:
    rows: list[tuple[tuple[InlineSpan, ...], ...]] = []
    widths: set[int] = set()
    for row in element.findall(_q(_W, "tr")):
        cells: list[tuple[InlineSpan, ...]] = []
        for cell in row.findall(_q(_W, "tc")):
            spans: list[InlineSpan] = []
            for paragraph in cell.findall(_q(_W, "p")):
                if spans:
                    spans.append(InlineSpan(InlineKind.TEXT, "\n"))
                spans.extend(_inline_children(paragraph, state))
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
    return ContentBlock(BlockKind.TABLE, rows=tuple(rows))


def extract_docx_content(
    source_path: Path,
    *,
    revision_mode: RevisionMode = RevisionMode.FINAL,
    comment_mode: CommentMode = CommentMode.OMIT,
    include_annotation_metadata: bool = False,
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
        )
        root = _parse_xml(archive, "word/document.xml")
        body = root.find(_q(_W, "body"))
        if body is None:
            raise InvalidInputError("DOCX document has no body")
        blocks: list[ContentBlock] = []
        for child in body:
            if child.tag == _q(_W, "p"):
                blocks.append(_paragraph(child, state))
            elif child.tag == _q(_W, "tbl"):
                blocks.append(_table(child, state))
        _warn_about_comment_anchors(state)
        _warn_about_revision_anchors(state)
        if any(name.startswith(("word/header", "word/footer")) for name in archive.namelist()):
            state.warnings.append(
                ConversionWarning(
                    "HEADER_FOOTER_OMITTED",
                    "Headers and footers are not part of the normalized reading order.",
                )
            )
        return NormalizedContent(
            SourceFormat.DOCX,
            tuple(blocks),
            tuple(state.assets),
            tuple(state.annotations),
            tuple(state.warnings),
        )
