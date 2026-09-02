"""Normalized semantic content extraction and deterministic writers."""

from gordon_doc_converter.content.docx import extract_docx_content
from gordon_doc_converter.content.html import render_html
from gordon_doc_converter.content.html_source import extract_html_content
from gordon_doc_converter.content.markdown import render_markdown
from gordon_doc_converter.content.markdown_source import extract_markdown_content
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
    PageContentKind,
    SourceAnchor,
)
from gordon_doc_converter.content.odt import extract_odt_content
from gordon_doc_converter.content.pdf import extract_pdf_content
from gordon_doc_converter.content.structured import (
    build_jsonl_records,
    build_structured_payload,
    render_json,
    render_jsonl,
    render_yaml,
)
from gordon_doc_converter.content.writers import ContentWriteResult, write_content_artifacts

__all__ = [
    "BlockKind",
    "ContentAsset",
    "ContentBlock",
    "ContentWriteResult",
    "DocumentMetadata",
    "InlineKind",
    "InlineSpan",
    "InlineStyle",
    "LayoutAvailability",
    "LayoutMetadata",
    "NormalizedContent",
    "PageContentKind",
    "SourceAnchor",
    "build_jsonl_records",
    "build_structured_payload",
    "extract_docx_content",
    "extract_html_content",
    "extract_markdown_content",
    "extract_odt_content",
    "extract_pdf_content",
    "render_html",
    "render_json",
    "render_jsonl",
    "render_markdown",
    "render_yaml",
    "write_content_artifacts",
]
