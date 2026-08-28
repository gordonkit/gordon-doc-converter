"""Shared builders for synthetic source packages used across the test suite."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

import pytest

_ODF_TEXT_MIME = "application/vnd.oasis.opendocument.text"
_ODF_NAMESPACES = """xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
 xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
 xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
 xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
 xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0"
 xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"
 xmlns:xlink="http://www.w3.org/1999/xlink"
 xmlns:dc="http://purl.org/dc/elements/1.1/\""""
_ODF_MANIFEST = f"""<manifest:manifest
 xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3">
<manifest:file-entry manifest:full-path="/" manifest:media-type="{_ODF_TEXT_MIME}"/>
<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
</manifest:manifest>"""


def _odf_part(root: str, inner: str) -> str:
    return f'<{root} {_ODF_NAMESPACES} office:version="1.3">{inner}</{root}>'


@pytest.fixture
def write_odt() -> Callable[..., Path]:
    """Return a builder writing one valid ODF text package from markup fragments."""

    def build(
        path: Path,
        body_xml: str = "",
        *,
        styles_xml: str = "",
        document_styles: str = "",
        document_meta: str = "",
        parts: dict[str, str | bytes] | None = None,
        content_xml: str | None = None,
    ) -> Path:
        content = content_xml or _odf_part(
            "office:document-content",
            f"{styles_xml}<office:body><office:text>{body_xml}</office:text></office:body>",
        )
        with ZipFile(path, "w", ZIP_DEFLATED) as archive:
            archive.writestr("mimetype", _ODF_TEXT_MIME, compress_type=ZIP_STORED)
            archive.writestr("META-INF/manifest.xml", _ODF_MANIFEST)
            archive.writestr("content.xml", content)
            if document_styles:
                archive.writestr("styles.xml", _odf_part("office:document-styles", document_styles))
            if document_meta:
                archive.writestr("meta.xml", _odf_part("office:document-meta", document_meta))
            for name, payload in (parts or {}).items():
                archive.writestr(name, payload)
        return path

    return build
