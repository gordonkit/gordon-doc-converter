# GordonKit Document Converter

[![CI](https://github.com/gordonkit/gordon-doc-converter/actions/workflows/ci.yml/badge.svg)](https://github.com/gordonkit/gordon-doc-converter/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Development Status: Pre-Alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](https://pypi.org/classifiers/)

[Documentation](https://docs.gordonkit.com/)

GordonKit Document Converter is a Python 3.12+ orchestration library for diagnosable,
multi-engine document conversion. It delegates rendering to Microsoft Word, LibreOffice,
or optional Gotenberg; it does not implement a document layout engine.

Its primary purpose is file-format conversion. The Python library, command-line interface,
and HTTP API are different ways to access the same conversion service.

## Supported format conversions

| Input | DOCX | PDF | HTML | Markdown | ODT | Images |
| --- | --- | --- | --- | --- | --- | --- |
| DOCX | × | Auto | ✓ | ✓ | LO | PDF |
| PDF | — | × | ✓ | ✓ | — | ✓ |
| HTML | P | P+ | × | — | — | — |
| Markdown | P | P+ | — | × | — | — |
| ODT | LO | LO | — | — | × | — |

`Auto` policy-based engine selection · `✓` built in · `LO` LibreOffice · `P` Pandoc ·
`P+` Pandoc with a PDF backend · `PDF` via an intermediate PDF · `—` not supported ·
`×` same format; not a conversion

Page-image output is available as PNG or JPEG. Markdown, HTML, and image files are output
artifacts for DOCX/PDF sources; Markdown and HTML are also accepted as input for PDF/DOCX
conversion. The project does not convert Markdown and HTML directly between each other.

DOCX-to-ODT, ODT-to-DOCX, and ODT-to-PDF conversion use LibreOffice; DOCX-to-PDF can use
the selected Word, LibreOffice, or Gotenberg engine. ODT support targets ODF-CNS 15251 /
ISO/IEC 26300 Writer documents. It validates package structure and content readability, but
does not promise pixel-identical round trips.

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

Use a container when you do not want to install Python or LibreOffice on the host. The `cli`
profile mounts the current directory at `/work`:

```console
docker compose -f docker/compose.yaml --profile cli run --rm cli convert /work/example.docx --output /work/example.pdf
```

For a private HTTP service with LibreOffice in the same image, set an API key and start the
`standalone-lo` profile:

```sh
GORDON_DOC_API_KEY=replace-me docker compose -f docker/compose.yaml \
    --profile standalone-lo up --build
```

Use `gateway-gotenberg` instead to run the API with a separate Gotenberg renderer. Container
profiles, security notes, and smoke checks are documented in
[docker/README.md](docker/README.md).

### HTTP API

Once the API is running, submit the DOCX bytes with the original filename and bearer token:

```sh
curl --fail -H "Authorization: Bearer replace-me" \
    -H "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document" \
    -H "X-Filename: example.docx" --data-binary @example.docx \
    http://localhost:8000/conversions --output example.pdf
```

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

The generated site is self-contained under `docs/` and uses relative links. It is published
at [docs.gordonkit.com](https://docs.gordonkit.com/). Its single documentation index supports
English/Traditional Chinese navigation, search, responsive layouts, and a light/dark theme.
The generated API contract is available at `docs/openapi.json`, and the read-only Swagger UI
is available at `docs/swagger/index.html`. Run `npm run openapi:check` to detect a stale export.

Browse the [documentation index](docs/index.html) for the technical reference, user guide,
compatibility notes, and development standards. Use its language control for Traditional
Chinese, or see [README.zh-TW.md](README.zh-TW.md).

## License

Apache License 2.0. See [LICENSE](LICENSE), [NOTICE](NOTICE), and
[THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).
