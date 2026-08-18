"""Engine-neutral normalized semantic content models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from gordon_doc_converter.models import ConversionWarning, NormalizedAnnotation, SourceFormat


class InlineKind(StrEnum):
    """Semantic inline categories retained from a source document."""

    TEXT = "text"
    INSERTION = "insertion"
    DELETION = "deletion"
    LINK = "link"
    IMAGE = "image"
    COMMENT_REFERENCE = "comment-reference"


class BlockKind(StrEnum):
    """Normalized block categories supported by deterministic writers."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list-item"
    TABLE = "table"


class PageContentKind(StrEnum):
    """Extractability classification for a PDF page."""

    TEXT = "text"
    IMAGE = "image"
    MIXED = "mixed"
    EMPTY = "empty"


class LayoutAvailability(StrEnum):
    """Availability of source layout metadata for semantic blocks."""

    NOT_REQUESTED = "not-requested"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class DocumentMetadata:
    """Allowlisted portable document properties."""

    title: str | None = None
    subject: str | None = None
    creator: str | None = None
    keywords: str | None = None
    created: str | None = None
    modified: str | None = None


@dataclass(frozen=True, slots=True)
class LayoutMetadata:
    """Provenance and availability of physical/display page metadata."""

    availability: LayoutAvailability = LayoutAvailability.NOT_REQUESTED
    provider: str | None = None
    confidence: str | None = None


@dataclass(frozen=True, slots=True)
class SourceAnchor:
    """Source-specific locator for reversing one normalized block to its origin."""

    locator: str
    part: str | None = None
    element_path: str | None = None
    native_id: str | None = None
    page_number: int | None = None


@dataclass(frozen=True, slots=True)
class InlineSpan:
    """One normalized inline text, link, image, or annotation reference."""

    kind: InlineKind
    text: str = ""
    target: str | None = None
    asset_id: str | None = None
    annotation_id: str | None = None


@dataclass(frozen=True, slots=True)
class ContentBlock:
    """One normalized semantic block with optional table cells and page source."""

    kind: BlockKind
    inlines: tuple[InlineSpan, ...] = ()
    level: int | None = None
    list_level: int | None = None
    rows: tuple[tuple[tuple[InlineSpan, ...], ...], ...] = ()
    page_number: int | None = None
    display_page_label: str | None = None
    source_anchor: SourceAnchor | None = None

    @property
    def text(self) -> str:
        """Return plain text from the block's direct inline spans."""
        return "".join(span.text for span in self.inlines)


@dataclass(frozen=True, slots=True)
class ContentAsset:
    """Binary asset with a generated safe name and source-neutral identifier."""

    asset_id: str
    filename: str
    media_type: str
    data: bytes
    page_number: int | None = None


@dataclass(frozen=True, slots=True)
class NormalizedContent:
    """Shared semantic representation written to Markdown, HTML, and sidecars."""

    source_format: SourceFormat
    blocks: tuple[ContentBlock, ...]
    assets: tuple[ContentAsset, ...] = ()
    annotations: tuple[NormalizedAnnotation, ...] = ()
    warnings: tuple[ConversionWarning, ...] = ()
    page_kinds: tuple[PageContentKind, ...] = ()
    metadata: DocumentMetadata | None = None
    layout: LayoutMetadata = LayoutMetadata()
    source_sha256: str | None = None
