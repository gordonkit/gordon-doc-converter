"""Public service integration coverage across installed local engines."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from gordon_doc_converter import (
    ConversionOptions,
    ConversionRequest,
    ConversionResult,
    EngineName,
    convert,
)
from gordon_doc_converter.service import probe_engines

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
    <w:p><w:r><w:t>GordonKit 公開服務繁中轉換測試</w:t></w:r></w:p>
    <w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr>
  </w:body>
</w:document>
"""


def _write_generated_docx(path: Path) -> None:
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _PACKAGE_RELS)
        archive.writestr("word/document.xml", _DOCUMENT)


def test_public_convert_returns_same_contract_for_installed_engines(tmp_path: Path) -> None:
    source = tmp_path / "公開 API 文件.docx"
    _write_generated_docx(source)
    source_before = source.read_bytes()
    available = {
        probe.engine
        for probe in probe_engines((EngineName.WORD_COM, EngineName.LIBREOFFICE))
        if probe.available
    }
    results: list[ConversionResult] = []
    for engine in (EngineName.WORD_COM, EngineName.LIBREOFFICE):
        if engine not in available:
            continue
        output = tmp_path / f"{engine.value}.pdf"
        request = ConversionRequest.from_source(
            source,
            options=ConversionOptions(output_path=output, engine=engine, timeout_seconds=60),
        )
        result = convert(request)
        assert result.success is True
        assert result.selected_engine is engine
        assert output.is_file()
        results.append(result)

    if not results:
        pytest.skip("no local conversion engine is available")
    result_keys = set(results[0].to_dict())
    artifact_keys = set(results[0].artifacts[0].to_dict())
    assert all(set(result.to_dict()) == result_keys for result in results)
    assert all(set(result.artifacts[0].to_dict()) == artifact_keys for result in results)
    assert source.read_bytes() == source_before
