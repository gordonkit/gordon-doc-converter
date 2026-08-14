"""Starter document templates for authoring print-ready markup."""

from __future__ import annotations

from pathlib import Path

from gordon_doc_converter.exceptions import OutputExistsError
from gordon_doc_converter.models import PageOrientation


def blank_html_template(orientation: PageOrientation = PageOrientation.PORTRAIT) -> str:
    """Return a blank A4 HTML document with print-oriented CSS."""
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Untitled document</title>
  <style>
    @page {{
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
      font-family: "Noto Sans CJK TC", "Microsoft JhengHei", sans-serif;
      font-size: 10.5pt;
      line-height: 1.5;
    }}

    h1, h2, h3, h4, h5, h6 {{
      break-after: avoid;
      page-break-after: avoid;
    }}

    table, figure, img, pre {{
      max-width: 100%;
      break-inside: avoid;
      page-break-inside: avoid;
    }}

    img {{
      height: auto;
    }}

    .page-break {{
      break-before: page;
      page-break-before: always;
    }}
  </style>
</head>
<body>
  <h1>Document title</h1>
  <p>Replace this text with your content.</p>
</body>
</html>
"""


def write_blank_html_template(
    output_path: Path,
    *,
    orientation: PageOrientation = PageOrientation.PORTRAIT,
    overwrite: bool = False,
) -> None:
    """Write an editable blank A4 HTML template."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.casefold() not in {".html", ".htm"}:
        raise ValueError("HTML template output must use the .html or .htm extension")
    if output_path.exists() and not overwrite:
        raise OutputExistsError("HTML template already exists")
    mode = "w" if overwrite else "x"
    with output_path.open(mode, encoding="utf-8", newline="\n") as stream:
        stream.write(blank_html_template(orientation))
