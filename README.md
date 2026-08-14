# GordonKit Document Converter

GordonKit Document Converter is a Python 3.12+ orchestration library for diagnosable,
multi-engine document conversion. It delegates rendering to Microsoft Word, LibreOffice,
or optional Gotenberg; it does not implement a document layout engine.

The current development state includes the cross-platform request/result contracts,
engine-selection policy, PDF validation, isolated LibreOffice and Microsoft Word COM
adapters, semantic DOCX/PDF extraction, Markdown/HTML and page-image artifacts, rendered PDF
comparison, a private FastAPI adapter, hardened container profiles, and the `gordon-doc` CLI.

## Development setup

```console
uv sync --dev
uv sync --dev --all-extras
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
uv build
```

The real LibreOffice integration test is skipped when `soffice` is unavailable. Run it on
a host with LibreOffice installed using
`uv run pytest -m integration tests/integration/libreoffice`.

The Microsoft Word integration test requires Windows, licensed Microsoft Word, and the
`word` optional dependency. Run it only in a controlled interactive environment using
`uv sync --dev --extra word --locked` followed by
`uv run pytest -m integration tests/integration/word_com`.

The static documentation uses locally built Tailwind CSS and local SVG icons. Install the
frontend dependency and rebuild the CSS before publishing `docs/`:

```console
npm ci
npm run build:css
```

The generated site is self-contained under `docs/` and uses relative links, so it can be
served from a Cloudflare Pages project subdirectory. The documentation index supports
English/Traditional Chinese navigation and a light/dark theme preference.

## Conversion example

```python
from pathlib import Path

from gordon_doc_converter import ConversionRequest, convert

request = ConversionRequest.from_source(Path("example.docx"))
result = convert(request)
if not result.success:
    raise RuntimeError(result.error.message if result.error else "conversion failed")
print(result.artifacts[0].path)
```

`convert()` selects an engine according to the deployment policy, validates staged output,
and publishes the PDF only after validation succeeds. Use `DocumentConversionService` for
engine injection, `convert_batch()` for sequential failure-isolated batches, and
`probe_engines()` for capability diagnostics.

## Supported format conversions

| Input | PDF | DOCX | ODT | Markdown | HTML | Page images |
| --- | --- | --- | --- | --- | --- |
| DOCX | Yes | Yes, via LibreOffice | Yes, via LibreOffice | Yes | Yes | Yes, via an intermediate PDF |
| ODT | Yes, via LibreOffice | Yes, via LibreOffice | Yes | No | No | No |
| PDF | Yes, validated copy | No | No | Yes | Yes | Yes |
| HTML | Yes, with Pandoc and a PDF backend | Yes, with Pandoc | No | No | No | No |
| Markdown | Yes, with Pandoc and a PDF backend | Yes, with Pandoc | No | No | No | No |

Page-image output is available as PNG or JPEG. Markdown, HTML, and image files are output
artifacts for DOCX/PDF sources; Markdown and HTML are also accepted as input for PDF/DOCX
conversion. The project does not convert Markdown and HTML directly between each other.
PDF-to-PDF validates and publishes the source rather than re-rendering it. DOCX/ODT office-file
conversion uses LibreOffice; DOCX-to-PDF can also use the selected Word or Gotenberg engine.
ODT support targets ODF-CNS 15251 / ISO/IEC 26300 Writer documents. It validates package
structure and content readability, but does not promise pixel-identical round trips.

Create an editable, print-ready A4 HTML starting point with `gordon-doc template report.html`.
Use `--orientation landscape` for A4 horizontal layout, then convert it with
`gordon-doc convert report.html --to pdf` or `--to docx`. HTML/Markdown conversion requires
Pandoc; PDF output additionally requires a Pandoc PDF backend such as `wkhtmltopdf`.

## Command-line interface

```console
gordon-doc doctor
gordon-doc engines --json
gordon-doc template report.html --orientation portrait
gordon-doc convert example.docx --output example.pdf
gordon-doc convert report.odt --to docx
gordon-doc convert example.docx --to odt --engine libreoffice
gordon-doc convert report.html --to pdf --orientation landscape
gordon-doc convert report.html --to docx
gordon-doc convert example.pdf --to images --dpi 144
gordon-doc convert example.docx --to markdown --to html
gordon-doc compare expected.pdf actual.pdf --diff-dir differences --json
gordon-doc batch one.docx two.docx --output-dir converted --json
gordon-doc version
```

Use `--engine word-com`, `--engine libreoffice`, or a configured `--engine gotenberg` for
strict explicit selection. Conversion options also include `--mode`, `--revisions`,
`--comments`, `--timeout`, `--overwrite`, image format/quality/page selection, and an optional
`--gotenberg-url`. Page images use `<stem>.pages/0001.png`; semantic artifacts use `.md`,
`.html`, shared `.assets/`, and an annotation sidecar when present. Every command supports
`--json` for automation.

Install `.[images]` for PDFium/Pillow rasterization, `.[gotenberg]` for the remote adapter,
`.[api]` for FastAPI, or `.[word]` for Windows COM. Container and private API deployment is
documented in [docker/README.md](docker/README.md).

Stable exit codes are `0` for success, `2` for invalid input or an existing output, `3` for
engine or capability unavailability, `4` for conversion failure, timeout, or missing output,
and `5` for PDF validation failure.

Microsoft Word and LibreOffice can render the same document differently. The project will
report the selected engine and fallback reason; it will never promise identical output or
silently switch an explicitly selected engine.

Browse the [documentation index](docs/index.html) for the technical reference, user guide,
compatibility notes, and development standards. See [README.zh-TW.md](README.zh-TW.md) for
Traditional Chinese documentation, or open the [Traditional Chinese documentation index](docs/index.zh-TW.html).

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
