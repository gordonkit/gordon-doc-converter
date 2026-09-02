"""Tests for the editable print-ready HTML and Markdown starter templates."""

from pathlib import Path

import pytest

from gordon_doc_converter.exceptions import OutputExistsError
from gordon_doc_converter.models import PageOrientation, SourceFormat
from gordon_doc_converter.template import (
    blank_html_template,
    blank_markdown_template,
    write_blank_template,
)


def test_blank_template_contains_a4_orientation_and_print_units() -> None:
    html = blank_html_template(PageOrientation.LANDSCAPE)

    assert "size: A4 landscape" in html
    assert "margin: 20mm" in html
    assert "font-size: 10.5pt" in html


def test_template_writer_does_not_overwrite_by_default(tmp_path: Path) -> None:
    output = tmp_path / "blank.html"
    write_blank_template(output)

    with pytest.raises(OutputExistsError):
        write_blank_template(output)

    assert output.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_markdown_template_carries_front_matter_metadata_and_no_page_setup() -> None:
    markdown = blank_markdown_template()

    assert markdown.splitlines()[0] == "---"
    assert "title: Untitled document" in markdown
    assert "# Section heading" in markdown
    assert "@page" not in markdown


def test_template_writer_picks_the_format_named_by_the_extension(tmp_path: Path) -> None:
    html = tmp_path / "報告.html"
    markdown = tmp_path / "報告.md"

    assert write_blank_template(html) is SourceFormat.HTML
    assert write_blank_template(markdown, orientation=PageOrientation.LANDSCAPE) is (
        SourceFormat.MARKDOWN
    )
    assert html.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert markdown.read_text(encoding="utf-8") == blank_markdown_template()


def test_template_writer_rejects_an_extension_it_cannot_write(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=".html, .htm, or .md"):
        write_blank_template(tmp_path / "report.docx")
