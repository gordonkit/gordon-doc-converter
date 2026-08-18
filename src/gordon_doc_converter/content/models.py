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
