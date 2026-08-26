# GordonKit Document Converter

[![CI](https://github.com/gordonkit/gordon-doc-converter/actions/workflows/ci.yml/badge.svg)](https://github.com/gordonkit/gordon-doc-converter/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/gordonkit/gordon-doc-converter/blob/main/LICENSE)
[![Development Status: Pre-Alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](https://pypi.org/classifiers/)

[繁體中文](https://github.com/gordonkit/gordon-doc-converter/blob/main/README.zh-TW.md) ·
[简体中文](https://github.com/gordonkit/gordon-doc-converter/blob/main/README.zh-CN.md) ·
[日本語](https://github.com/gordonkit/gordon-doc-converter/blob/main/README.ja.md)

[Documentation](https://docs.gordonkit.com/)

GordonKit Document Converter converts DOCX and other document formats to PDF, HTML,
Markdown, images, and more. It provides a Python library, CLI, and HTTP API, using Microsoft
Word, LibreOffice, Pandoc, or Gotenberg for rendering.

## Supported format conversions

| Input | DOCX | PDF | ODT | HTML | Markdown | YAML | JSON | Images |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DOCX | × | Auto | LO | ✓ | ✓ | ✓ | ✓ | PDF |
| PDF | — | × | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| ODT | LO | LO | × | — | — | — | — | — |
| HTML | P | P+ | — | × | — | — | — | — |
| Markdown | P | P+ | — | — | × | — | — | — |

`Auto` policy-based engine selection · `✓` built in · `LO` LibreOffice · `P` Pandoc ·
`P+` Pandoc with a PDF backend · `PDF` via an intermediate PDF · `—` not supported ·
`×` same format; not a conversion

Page-image output is available as PNG or JPEG. Markdown, HTML, YAML, JSON, and image files are
output artifacts for DOCX/PDF sources; Markdown and HTML are also accepted as input for
PDF/DOCX conversion. The project does not convert Markdown and HTML directly between each
other.

DOCX-to-ODT, ODT-to-DOCX, and ODT-to-PDF conversion use LibreOffice. DOCX conversion follows
these engine policies:

- DOCX to PDF on interactive Windows: automatic mode prefers Word COM.
- DOCX to PDF on servers: automatic mode prefers Gotenberg, then LibreOffice.
- DOCX to PDF on other hosts: automatic mode prefers LibreOffice.
- DOCX to HTML: semantic extraction is the default. On a Windows desktop with Word COM
    available, Word rendering provides higher visual fidelity.
- Use `--engine word-com` to force Word COM HTML, or `--mode server` to force semantic
    extraction.
- Explicit engine and strict modes never fall back.
- Rendering may differ between engines.

ODT support targets ODF-CNS 15251 / ISO/IEC 26300 Writer documents. It validates package
structure and content readability, but does not promise pixel-identical round trips.

HTML/Markdown conversion requires Pandoc; PDF output additionally requires a Pandoc PDF
backend such as `wkhtmltopdf`. Create an editable, print-ready A4 starting point with
`gordon-doc template report.html`, then convert it with
`gordon-doc convert report.html --to pdf` or `--to docx`. Use `--orientation landscape` for
an A4 horizontal layout.

## Interfaces

| Interface | Intended use |
| --- | --- |
| Python library | Embed typed conversion calls, batches, and engine diagnostics in Python applications |
| `gordon-doc` CLI | Run local conversions from a terminal, script, or CI job |
| HTTP API | Send authenticated conversion requests to a private service deployment |
| Container profiles | Run the CLI or HTTP API with renderer dependencies in isolated images |

Every interface enters through the same application service and preserves structured results,
engine policy, and diagnostics. Choose the interface that matches where the conversion is
initiated, then follow its quick start below.

## Installation

| Interface | Installation |
| --- | --- |
| Python library | `python -m pip install gordon-doc-converter` |
| `gordon-doc` CLI | Included with `gordon-doc-converter`; verify with `gordon-doc version` |
| HTTP API | `python -m pip install "gordon-doc-converter[api]"` |
| Container profiles | Install Docker Engine or Docker Desktop with Compose v2; no local Python package is required |

Rendering and output capabilities may require an optional extra:
`gordon-doc-converter[images]`, `gordon-doc-converter[gotenberg]`, or
`gordon-doc-converter[word]`. See the [online documentation](https://docs.gordonkit.com/)
for engine and platform requirements.

## Quick start

### Python library

Use the library when conversion is part of a Python application:

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

### CLI

Use the CLI for interactive use, shell scripts, and CI jobs:

```console
gordon-doc convert example.docx --output example.pdf
```

### Containers

Use the single container image when you do not want to install Python or LibreOffice on the
host. The `cli` profile mounts the current directory at `/work` and does not require an API
key. This command is the same in Bash and PowerShell:

```console
docker compose -f docker/compose.yaml --profile cli run --rm cli convert /work/example.docx --output /work/example.pdf
```

For a private HTTP service with LibreOffice in the same image, set an API key and start the
`standalone-lo` profile. A `.env` file works in Bash and PowerShell:

```dotenv
GORDON_DOC_API_KEY=replace-with-a-strong-random-value
```

```console
docker compose -f docker/compose.yaml --env-file .env --profile standalone-lo up --build
```

Use `gateway-gotenberg` instead to run the same API image with a separate Gotenberg renderer
on a shared Docker network. Setting `GORDON_DOC_GOTENBERG_URL` makes Gotenberg the API's
explicit default; a failed Gotenberg request does not silently fall back to LibreOffice.
Container profiles, security notes, and smoke checks are documented in
[container documentation](https://github.com/gordonkit/gordon-doc-converter/blob/main/docker/README.md).
Tagged releases publish `gordonkit/gordon-doc-converter` to Docker Hub. The required repository
variables, secrets, and release steps are documented there.

### HTTP API

Once the API is running, submit the DOCX bytes with the original filename and bearer token:

```sh
curl --fail -H "Authorization: Bearer replace-me" \
    -H "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document" \
    -H "X-Filename: example.docx" --data-binary @example.docx \
    http://localhost:8000/conversions --output example.pdf
```

On PowerShell, use `Invoke-WebRequest -InFile ... -OutFile ...`. Complete Bash and PowerShell
examples for the LibreOffice and Gotenberg profiles, including shutdown, are in the
[container documentation](docker/README.md).

Install `.[images]` for PDFium/Pillow rasterization, `.[gotenberg]` for the remote adapter,
`.[api]` for FastAPI, or `.[word]` for Windows COM.

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
gordon-doc convert example.docx --to markdown --to html --to yaml --to json
gordon-doc convert example.docx --to html --engine word-com
gordon-doc convert example.docx --to yaml --metadata layout --progress
gordon-doc compare expected.pdf actual.pdf --diff-dir differences --json
gordon-doc batch one.docx two.docx --output-dir converted --json
gordon-doc version
```

Use `--engine word-com`, `--engine libreoffice`, or a configured `--engine gotenberg` for
strict explicit selection. For DOCX-to-HTML, `--engine word-com` renders through Word COM;
omit it or use `--mode server` for semantic extraction. Conversion options also include
`--mode`, `--revisions`, `--comments`, `--metadata`, `--timeout`, `--overwrite`, image
format/quality/page selection, and an optional `--gotenberg-url`. Page images use
`<stem>.pages/0001.png`; semantic artifacts use `.md`, `.html`, `.yaml`, `.json`, shared
`.assets/`, and an annotation sidecar when present.
YAML and JSON share a versioned heading/paragraph/list/table schema intended for downstream
indexing. `--to json` writes that document artifact; the separate `--json` flag emits the CLI
result contract for automation.

PDF sources have no semantic tags, so blocks are inferred from layout. The converter rebuilds
text lines from glyph positions, drops repeated running headers and footers, and classifies
headings from the PDF outline, relative font size, weight, spacing, and ordinal markers.
Markers are parsed by system, style, and unit, covering Arabic, Roman, Latin, circled, and CJK
numerals, so heading levels follow the document's own numbering rather than font size alone.
Inference is heuristic and reading order remains reported as inferred.

Metadata detail is `none`, `basic` (the default allowlisted document properties), or `layout`.
PDF physical pages are one-based and identify `pypdf` as their provider. DOCX physical pages
and display page labels are omitted with an explicit unavailable capability until a layout
provider is configured; the converter does not present inferred page numbers as exact.

Structured artifacts include cross-format reverse locators. `source.sha256` identifies the
exact source file, while each `source_anchor` includes a normalized-content SHA-256 for
verification. DOCX blocks locate `word/document.xml` elements (and table cells by row/cell);
PDF blocks locate their one-based physical page. PDF anchors currently identify a page rather
than a bounding box; a future layout provider can add page coordinates without changing the
DOCX locator contract. Optional locator fields are omitted instead of being serialized as null.

```yaml
schema_version: "1.3"
source: {format: "pdf", sha256: "<source-file-sha256>"}
root_blocks: [{
    id: "block-000001",
    source_order: 0,
    kind: "paragraph",
    physical_page_number: 1,
    text: "Page text",
    source_anchor: {
        locator: "pdf-page",
        page_number: 1,
        content_sha256: "<normalized-content-sha256>"
    }
}]
```

Byte offsets are deliberately not part of the stable locator contract. A DOCX offset points
into a compressed ZIP member and changes when Office rewrites or recompresses the package. A
PDF offset identifies serialized objects or streams and changes after optimization,
linearization, or incremental saves. Use the source fingerprint plus OOXML element path or PDF
page anchor instead. Byte offsets may be added later only as non-authoritative diagnostic hints.

`convert` and `batch` show conversion phases automatically on interactive terminals. Progress
is written only to stderr and is automatically disabled for `--json` or redirected output;
use `--progress` or `--no-progress` to override the automatic choice.

Stable exit codes are `0` for success, `2` for invalid input or an existing output, `3` for
engine or capability unavailability, `4` for conversion failure, timeout, or missing output,
and `5` for PDF validation failure.

Microsoft Word and LibreOffice can render the same document differently. The project will
report the selected engine and fallback reason; it will never promise identical output or
silently switch an explicitly selected engine.

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

The static documentation is a React site built with Vite, Tailwind CSS, bundled Heroicons,
and a bundled Swagger UI. Install the API and frontend dependencies before rebuilding
`docs/`; the build exports the current FastAPI contract to `openapi.json` automatically:

```console
uv sync --dev --extra api --locked
npm ci
npm run build
```

The generated site is self-contained under `docs/` and is published at
[docs.gordonkit.com](https://docs.gordonkit.com/). It generates indexable pages under
`/en/<topic>/`, `/zh-TW/<topic>/`, `/zh-CN/<topic>/`, and `/ja/<topic>/` with localized metadata, canonical and
alternate links, structured data, a sitemap, and robots directives. The site also supports a
language dropdown for English, Traditional Chinese, Simplified Chinese, and Japanese,
search, responsive layouts,
and a light/dark theme.
The generated API contract is available at `docs/openapi.json`, and the read-only Swagger UI
is available at `docs/swagger/index.html`. Run `npm run openapi:check` to detect a stale export.

Browse the [English documentation](https://docs.gordonkit.com/en/overview/),
[Traditional Chinese documentation](https://docs.gordonkit.com/zh-TW/overview/),
[Simplified Chinese documentation](https://docs.gordonkit.com/zh-CN/overview/), or
[Japanese documentation](https://docs.gordonkit.com/ja/overview/) for the technical reference,
user guide, compatibility notes, and development standards.

## License

Apache License 2.0. See [LICENSE](https://github.com/gordonkit/gordon-doc-converter/blob/main/LICENSE),
[NOTICE](https://github.com/gordonkit/gordon-doc-converter/blob/main/NOTICE), and
[THIRD_PARTY_NOTICES.txt](https://github.com/gordonkit/gordon-doc-converter/blob/main/THIRD_PARTY_NOTICES.txt).
