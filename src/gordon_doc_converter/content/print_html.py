"""Print-ready HTML intermediate rendered from normalized content."""

from __future__ import annotations

from html import escape
from pathlib import Path

from gordon_doc_converter.content.html import document_language, render_body_html
from gordon_doc_converter.content.models import NormalizedContent
from gordon_doc_converter.models import PageOrientation
from gordon_doc_converter.template import print_stylesheet

ASSET_DIRECTORY_NAME = "assets"
DOCUMENT_FILENAME = "document.html"


def render_print_html(
    content: NormalizedContent,
    *,
    asset_directory: str = ASSET_DIRECTORY_NAME,
    orientation: PageOrientation = PageOrientation.PORTRAIT,
) -> str:
    """Serialize normalized content to a standalone A4 HTML document.

    The result carries the same print CSS as the authoring template, so every
    markup source reaches the rendering engines with one consistent look.
    """
    metadata = content.metadata
    title = metadata.title if metadata and metadata.title else "Document"
    head = [
        '<meta charset="utf-8">',
        f"<title>{escape(title)}</title>",
    ]
    if metadata is not None:
        for name, value in (
            ("author", metadata.creator),
            ("description", metadata.subject),
            ("keywords", metadata.keywords),
        ):
            if value:
                head.append(f'<meta name="{name}" content="{escape(value, quote=True)}">')
    head.append("<style>")
    head.append(print_stylesheet(orientation))
    head.append("</style>")
    body = render_body_html(content, asset_directory=asset_directory)
    return (
        "<!doctype html>\n"
        f'<html lang="{document_language(content)}">\n'
        "<head>\n" + "\n".join(head) + "\n</head>\n"
        "<body>\n" + body + "\n</body>\n</html>\n"
    )


def write_print_document(
    content: NormalizedContent,
    directory: Path,
    *,
    orientation: PageOrientation = PageOrientation.PORTRAIT,
) -> Path:
    """Write the print-ready intermediate and its assets into a working directory."""
    directory.mkdir(parents=True, exist_ok=True)
    if content.assets:
        assets = directory / ASSET_DIRECTORY_NAME
        assets.mkdir(parents=True, exist_ok=True)
        for asset in content.assets:
            (assets / asset.filename).write_bytes(asset.data)
    document = directory / DOCUMENT_FILENAME
    with document.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(render_print_html(content, orientation=orientation))
    return document
