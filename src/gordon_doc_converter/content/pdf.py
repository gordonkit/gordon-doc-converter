"""Text and embedded-image extraction from validated PDF documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader

from gordon_doc_converter.content.models import (
    BlockKind,
    ContentAsset,
    ContentBlock,
    InlineKind,
    InlineSpan,
    LayoutAvailability,
    LayoutMetadata,
    NormalizedContent,
    PageContentKind,
    SourceAnchor,
)
from gordon_doc_converter.content.pdf_layout import TextLine, build_lines, collect_fragments
from gordon_doc_converter.content.pdf_structure import infer_blocks
from gordon_doc_converter.exceptions import InvalidInputError
from gordon_doc_converter.models import ConversionWarning, MetadataDetail, SourceFormat
from gordon_doc_converter.security import file_sha256, validate_source_document


def _image_media_type(name: str) -> str:
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".jp2": "image/jp2",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }.get(Path(name).suffix.casefold(), "application/octet-stream")


def _has_image_xobject(page: Any) -> bool:
    """Return whether page resources declare at least one image XObject."""
    try:
        resources = page.get("/Resources", {}).get_object()
        xobjects = resources.get("/XObject", {}).get_object()
        return any(
            xobject.get_object().get("/Subtype") == "/Image" for xobject in xobjects.values()
        )
    except (AttributeError, KeyError, TypeError, ValueError):
        return False


def _page_images(
    page: Any, page_number: int
) -> tuple[list[ContentAsset], list[InlineSpan], bool, bool]:
    assets: list[ContentAsset] = []
    spans: list[InlineSpan] = []
    failed = False
    detected = _has_image_xobject(page)
    try:
        images = page.images
        for image in images:
            original_name = str(image.name)
            suffix = Path(original_name).suffix.casefold()
            safe_suffix = suffix if suffix and suffix[1:].isalnum() else ".bin"
            filename = f"page-{page_number:04d}-image-{len(assets) + 1:04d}{safe_suffix}"
            asset = ContentAsset(
                filename,
                filename,
                _image_media_type(original_name),
                bytes(image.data),
                page_number,
            )
            assets.append(asset)
            spans.append(InlineSpan(InlineKind.IMAGE, "embedded image", asset_id=filename))
    except (AttributeError, ImportError, KeyError, TypeError, ValueError):
        failed = True
    return assets, spans, detected, failed


def _fallback_line(text: str, page_number: int) -> TextLine:
    """Represent a page whose operators exposed no usable text coordinates."""
    return TextLine(
        text=" ".join(text.split()),
        page_number=page_number,
        x=0.0,
        y=0.0,
        size=10.0,
        bold=False,
    )


def _append_image_blocks(
    blocks: list[ContentBlock], trailing_images: list[tuple[int, list[InlineSpan]]]
) -> None:
    """Attach each page's image spans after the last text block of that page."""
    for page_number, spans in trailing_images:
        block = ContentBlock(
            BlockKind.PARAGRAPH,
            tuple(spans),
            page_number=page_number,
            source_anchor=SourceAnchor("pdf-page", page_number=page_number),
        )
        position = len(blocks)
        for index in range(len(blocks) - 1, -1, -1):
            existing = blocks[index].page_number
            if existing is None or existing > page_number:
                position = index
                continue
            break
        blocks.insert(position, block)


def extract_pdf_content(
    source_path: Path,
    *,
    metadata_detail: MetadataDetail = MetadataDetail.BASIC,
) -> NormalizedContent:
    """Extract per-page text and supported embedded images with page provenance."""
    validate_source_document(source_path, SourceFormat.PDF)
    try:
        reader = PdfReader(source_path)
        blocks: list[ContentBlock] = []
        assets: list[ContentAsset] = []
        warnings: list[ConversionWarning] = []
        page_kinds: list[PageContentKind] = []
        lines: list[TextLine] = []
        trailing_images: list[tuple[int, list[InlineSpan]]] = []
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                fragments, text = collect_fragments(page)
            except (KeyError, TypeError, ValueError):
                fragments, text = [], ""
                warnings.append(
                    ConversionWarning(
                        "PDF_TEXT_EXTRACTION_FAILED",
                        f"Text could not be extracted from page {page_number}.",
                    )
                )
            page_assets, image_spans, image_detected, image_failed = _page_images(page, page_number)
            assets.extend(page_assets)
            if image_failed:
                warnings.append(
                    ConversionWarning(
                        "PDF_IMAGE_EXTRACTION_INCOMPLETE",
                        f"Some embedded images on page {page_number} could not be extracted.",
                    )
                )
            has_text = bool(text.strip())
            has_images = image_detected
            if has_text and has_images:
                kind = PageContentKind.MIXED
            elif has_text:
                kind = PageContentKind.TEXT
            elif has_images:
                kind = PageContentKind.IMAGE
            else:
                kind = PageContentKind.EMPTY
            page_kinds.append(kind)
            if has_text:
                page_lines = build_lines(fragments, page_number)
                if page_lines:
                    lines.extend(page_lines)
                else:
                    lines.append(_fallback_line(text, page_number))
                warnings.append(
                    ConversionWarning(
                        "PDF_READING_ORDER_INFERRED",
                        f"Reading order on page {page_number} is inferred from PDF operators.",
                    )
                )
            if image_spans:
                trailing_images.append((page_number, image_spans))
            if kind in {PageContentKind.IMAGE, PageContentKind.MIXED}:
                warnings.append(
                    ConversionWarning(
                        "OCR_REQUIRED",
                        f"Page {page_number} contains image content that requires OCR "
                        "for complete text.",
                    )
                )
            elif kind is PageContentKind.EMPTY:
                warnings.append(
                    ConversionWarning(
                        "PDF_EMPTY_PAGE",
                        f"Page {page_number} has no extractable text or supported embedded images.",
                    )
                )
        blocks = infer_blocks(lines, len(reader.pages))
        _append_image_blocks(blocks, trailing_images)
        layout = LayoutMetadata()
        if metadata_detail is MetadataDetail.LAYOUT:
            layout = LayoutMetadata(
                LayoutAvailability.AVAILABLE,
                provider="pypdf",
                confidence="exact",
            )
        return NormalizedContent(
            SourceFormat.PDF,
            tuple(blocks),
            tuple(assets),
            warnings=tuple(warnings),
            page_kinds=tuple(page_kinds),
            layout=layout,
            source_sha256=file_sha256(source_path),
        )
    except InvalidInputError:
        raise
    except Exception as exc:
        raise InvalidInputError("PDF content could not be extracted") from exc
