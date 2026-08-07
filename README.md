# GordonKit Document Converter

GordonKit Document Converter is a Python 3.12+ orchestration library for diagnosable,
multi-engine DOCX-to-PDF conversion. It delegates rendering to Microsoft Word, LibreOffice,
or (in a later release) Gotenberg; it does not implement a document layout engine.

The current development state includes the cross-platform request/result contracts,
engine-selection policy, PDF validation, and an isolated LibreOffice adapter. The adapter
can be used as a library primitive when LibreOffice is installed. Word COM, the complete
orchestration service, and the `gordon-doc` CLI are not yet available.

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

## Contract example

```python
from pathlib import Path

from gordon_doc_converter import ConversionRequest

request = ConversionRequest.from_source(Path("example.docx"))
assert request.to_dict()["artifacts"] == ["pdf"]
```

Microsoft Word and LibreOffice can render the same document differently. The project will
report the selected engine and fallback reason; it will never promise identical output or
silently switch an explicitly selected engine.

See [README.zh-TW.md](README.zh-TW.md) for Traditional Chinese documentation.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
