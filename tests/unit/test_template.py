"""Tests for editable print-ready HTML templates."""

from pathlib import Path

import pytest

from gordon_doc_converter.exceptions import OutputExistsError
from gordon_doc_converter.models import PageOrientation
from gordon_doc_converter.template import blank_html_template, write_blank_html_template


def test_blank_template_contains_a4_orientation_and_print_units() -> None:
    html = blank_html_template(PageOrientation.LANDSCAPE)

    assert "size: A4 landscape" in html
    assert "margin: 20mm" in html
    assert "font-size: 10.5pt" in html


def test_template_writer_does_not_overwrite_by_default(tmp_path: Path) -> None:
    output = tmp_path / "blank.html"
    write_blank_html_template(output)

    with pytest.raises(OutputExistsError):
        write_blank_html_template(output)

    assert output.read_text(encoding="utf-8").startswith("<!doctype html>")
