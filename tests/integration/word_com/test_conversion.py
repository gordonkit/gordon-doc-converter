"""Controlled Microsoft Word integration coverage for a generated CJK DOCX."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from gordon_doc_converter.engines.word_com import WordComEngine
from gordon_doc_converter.models import CommentMode, RevisionMode
from gordon_doc_converter.validation import validate_pdf

pytestmark = pytest.mark.integration

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
    '  <Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
    '  <Default Extension="xml" ContentType="application/xml"/>\n'
    '  <Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.'
    'wordprocessingml.document.main+xml"/>\n'
    "</Types>\n"
)
_PACKAGE_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
    '  <Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
    'relationships/officeDocument" Target="word/document.xml"/>\n'
    "</Relationships>\n"
)
_DOCUMENT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>GordonKit Microsoft Word 臺灣文件轉換測試</w:t></w:r></w:p>
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
    </w:sectPr>
  </w:body>
</w:document>
"""


def _write_generated_docx(path: Path) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _PACKAGE_RELS)
        archive.writestr("word/document.xml", _DOCUMENT)


def test_generated_cjk_docx_converts_to_valid_pdf(tmp_path: Path) -> None:
    engine = WordComEngine()
    probe = engine.probe()
    if not probe.available:
        pytest.skip(probe.reason or "Microsoft Word COM is unavailable")

    source = tmp_path / "臺灣 Word 文件.docx"
    output = tmp_path / "臺灣 Word 文件.pdf"
    _write_generated_docx(source)
    source_before = source.read_bytes()

    result = engine.convert(
        source,
        output,
        timeout_seconds=60,
        revision_mode=RevisionMode.FINAL,
        comment_mode=CommentMode.OMIT,
    )

    validation = validate_pdf(result.output_path)
    assert validation.valid is True
    assert validation.page_count == 1
    assert source.read_bytes() == source_before
