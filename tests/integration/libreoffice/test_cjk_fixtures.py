"""LibreOffice rendering coverage for the synthetic CJK fixture matrix."""

from __future__ import annotations

from pathlib import Path

import pytest

from gordon_doc_converter.engines.libreoffice import LibreOfficeEngine
from gordon_doc_converter.models import CommentMode, RevisionMode
from gordon_doc_converter.validation import validate_pdf

pytestmark = pytest.mark.integration

FIXTURE_DIRECTORY = Path(__file__).parents[2] / "fixtures" / "docx" / "cjk"
FIXTURES = tuple(sorted(FIXTURE_DIRECTORY.glob("*.docx")))


@pytest.mark.parametrize("source", FIXTURES, ids=lambda path: path.stem)
def test_cjk_fixture_converts_to_valid_pdf(source: Path, tmp_path: Path) -> None:
    """Every phase-7 fixture must render to a parseable, non-empty PDF."""
    engine = LibreOfficeEngine()
    probe = engine.probe()
    if not probe.available:
        pytest.skip(probe.reason or "LibreOffice is unavailable")

    output = tmp_path / f"{source.stem}.pdf"
    result = engine.convert(
        source,
        output,
        timeout_seconds=90,
        revision_mode=RevisionMode.FINAL,
        comment_mode=CommentMode.OMIT,
    )

    validation = validate_pdf(result.output_path)
    assert validation.valid is True
    assert validation.page_count is not None
    assert validation.page_count >= (2 if source.name == "multi-page-table.docx" else 1)
