# GordonKit Document Converter

GordonKit Document Converter is a Python 3.12+ orchestration library for diagnosable,
multi-engine DOCX-to-PDF conversion. It delegates rendering to Microsoft Word, LibreOffice,
or (in a later release) Gotenberg; it does not implement a document layout engine.

The current development state includes the cross-platform request/result contracts,
engine-selection policy, PDF validation, isolated LibreOffice and Microsoft Word COM
adapters, and the public conversion service. The `gordon-doc` CLI is not yet available.

## Development setup

```console
uv sync --dev
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

Microsoft Word and LibreOffice can render the same document differently. The project will
report the selected engine and fallback reason; it will never promise identical output or
silently switch an explicitly selected engine.

See [README.zh-TW.md](README.zh-TW.md) for Traditional Chinese documentation.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
