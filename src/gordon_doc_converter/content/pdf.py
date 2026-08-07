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
    NormalizedContent,
    PageContentKind,
)
from gordon_doc_converter.exceptions import InvalidInputError
from gordon_doc_converter.models import ConversionWarning, SourceFormat
from gordon_doc_converter.security import validate_source_document


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


def extract_pdf_content(source_path: Path) -> NormalizedContent:
    """Extract per-page text and supported embedded images with page provenance."""
    validate_source_document(source_path, SourceFormat.PDF)
    try:
        reader = PdfReader(source_path)
        blocks: list[ContentBlock] = []
        assets: list[ContentAsset] = []
        warnings: list[ConversionWarning] = []
        page_kinds: list[PageContentKind] = []
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except (KeyError, TypeError, ValueError):
                text = ""
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
            inlines: list[InlineSpan] = []
            if has_text:
                inlines.append(InlineSpan(InlineKind.TEXT, text))
                warnings.append(
                    ConversionWarning(
                        "PDF_READING_ORDER_INFERRED",
                        f"Reading order on page {page_number} is inferred from PDF operators.",
                    )
                )
            inlines.extend(image_spans)
            if inlines:
                blocks.append(
                    ContentBlock(BlockKind.PARAGRAPH, tuple(inlines), page_number=page_number)
                )
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
        return NormalizedContent(
            SourceFormat.PDF,
            tuple(blocks),
            tuple(assets),
            warnings=tuple(warnings),
            page_kinds=tuple(page_kinds),
        )
    except InvalidInputError:
        raise
    except Exception as exc:
        raise InvalidInputError("PDF content could not be extracted") from exc
