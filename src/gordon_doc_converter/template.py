"""Starter document templates for authoring print-ready markup."""

from __future__ import annotations

from pathlib import Path

from gordon_doc_converter.exceptions import OutputExistsError
from gordon_doc_converter.models import PageOrientation, SourceFormat

CJK_FONT_STACK = (
    '"Noto Sans CJK TC", "Noto Sans TC", "Source Han Sans TC", '
    '"Microsoft JhengHei", "PingFang TC", sans-serif'
)
CJK_MONOSPACE_STACK = (
    '"Noto Sans Mono CJK TC", "Cascadia Mono", "Consolas", "DejaVu Sans Mono", monospace'
)


def print_stylesheet(orientation: PageOrientation = PageOrientation.PORTRAIT) -> str:
    """Return the shared A4 print CSS used by templates and rendered intermediates."""
    return f"""@page {{
  size: A4 {orientation.value};
  margin: 20mm;
}}

:root {{
  color-scheme: light;
}}

html, body {{
  margin: 0;
  padding: 0;
}}

body {{
  color: #111827;
  font-family: {CJK_FONT_STACK};
  font-size: 10.5pt;
  line-height: 1.5;
}}

h1, h2, h3, h4, h5, h6 {{
  break-after: avoid;
  page-break-after: avoid;
  line-height: 1.3;
}}

table, figure, img, pre {{
  max-width: 100%;
  break-inside: avoid;
  page-break-inside: avoid;
}}

img {{
  height: auto;
}}

table {{
  border-collapse: collapse;
}}

th, td {{
  border: 0.5pt solid #9ca3af;
  padding: 2mm 3mm;
  text-align: left;
  vertical-align: top;
}}

th {{
  background: #f3f4f6;
}}

pre, code {{
  font-family: {CJK_MONOSPACE_STACK};
  font-size: 9.5pt;
}}

pre {{
  background: #f3f4f6;
  padding: 3mm;
  white-space: pre-wrap;
  word-wrap: break-word;
}}

blockquote {{
  margin: 0 0 0 4mm;
  padding-left: 4mm;
  border-left: 1mm solid #d1d5db;
  color: #374151;
}}

hr {{
  border: 0;
  border-top: 0.5pt solid #9ca3af;
}}

.page-break {{
  break-before: page;
  page-break-before: always;
}}
"""


def _indent(text: str, spaces: int) -> str:
    """Indent every non-empty line of a block of CSS for embedding in HTML."""
    prefix = " " * spaces
    return "\n".join(prefix + line if line else line for line in text.splitlines())


def blank_html_template(orientation: PageOrientation = PageOrientation.PORTRAIT) -> str:
    """Return a blank A4 HTML document with print-oriented CSS."""
    styles = _indent(print_stylesheet(orientation), 4)
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Untitled document</title>
  <style>
{styles}
  </style>
</head>
<body>
  <h1>Document title</h1>
  <p>Replace this text with your content.</p>
</body>
</html>
"""


def blank_markdown_template() -> str:
    """Return a blank Markdown document whose front matter carries document metadata.

    Markdown holds no page setup of its own: rendering applies the A4 print stylesheet
    and the orientation requested at conversion time. The body opens on a section
    heading, because the rendered document takes its title from the front matter.
    """
    return """---
title: Untitled document
author: Author name
---

# Section heading

Replace this text with your content.
"""


def write_blank_template(
    output_path: Path,
    *,
    orientation: PageOrientation = PageOrientation.PORTRAIT,
    overwrite: bool = False,
) -> SourceFormat:
    """Write the editable starter its extension names, returning the format written."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.casefold()
    if suffix in {".html", ".htm"}:
        source_format = SourceFormat.HTML
        body = blank_html_template(orientation)
    elif suffix == ".md":
        source_format = SourceFormat.MARKDOWN
        body = blank_markdown_template()
    else:
        raise ValueError("template output must use the .html, .htm, or .md extension")
    if output_path.exists() and not overwrite:
        raise OutputExistsError("template already exists")
    mode = "w" if overwrite else "x"
    with output_path.open(mode, encoding="utf-8", newline="\n") as stream:
        stream.write(body)
    return source_format
