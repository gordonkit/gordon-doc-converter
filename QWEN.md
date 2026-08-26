# QWEN.md — GordonKit Document Converter

> Context for AI assistants working on this repository.

## Project Overview

**GordonKit Document Converter** (`gordon-doc-converter`) is a Python 3.12+ orchestration library that converts DOCX files (and other document formats) to PDF through external rendering engines. It provides a Python library, CLI (`gordon-doc`), HTTP API, and container profiles.

- **Package name**: `gordon-doc-converter`
- **Import package**: `gordon_doc_converter`
- **CLI command**: `gordon-doc`
- **Current version**: See `pyproject.toml`
- **License**: Apache-2.0

This project does **not** implement a document renderer. It orchestrates external engines: Microsoft Word COM (Windows only), LibreOffice, Gotenberg (remote), and Pandoc (for text formats).

## Source Structure

```
src/gordon_doc_converter/    # Core Python package
  __init__.py                # Public exports
  cli.py                     # Typer CLI entrypoint (gordon-doc)
  core/                      # Application service, orchestrator, engine protocol
  engines/                   # Engine adapters (word, libreoffice, gotenberg, pandoc)
  models/                    # Pydantic/dataclass models for requests/results
  validators/                # PDF validation, input validation
tests/                       # pytest tests
  unit/                      # No external dependencies
  integration/               # Requires Word/LibreOffice/Gotenberg (marked)
docker/                      # Docker Compose profiles and container config
docs/                        # Generated documentation site (do not edit manually)
docs-src/                    # React + Vite + Tailwind source for docs site
manual-fixtures/             # Test fixtures (public/generated content only)
```

## Development Commands

Use `uv` for all Python operations. The `.python-version` and `pyproject.toml` specify Python 3.12+.

```bash
# Setup / sync environment
uv sync --dev
uv sync --dev --all-extras    # With all optional dependencies

# Code quality
uv run ruff format .          # Format code
uv run ruff check .           # Lint
uv run mypy src               # Type-check

# Testing
uv run pytest                 # All unit tests
uv run pytest -m integration  # Integration tests (requires external engines)

# Build
uv build                      # Build distribution packages
```

**Do not edit `uv.lock` manually.** Update it through `uv` when dependency changes are authorized.

## Architecture Principles

1. **Dependency direction**: Library/CLI/API → application service → shared engine protocol → engine adapters → PDF validation
2. **Engine independence**: Core library must remain independent of CLI/API frameworks; engines implement a shared protocol
3. **No silent fallback**: Explicit engine selection and strict modes never silently fall back; automatic fallback must report attempted engine, failure reason, final engine, and warning
4. **No identical rendering promise**: Word and LibreOffice render differently; never claim identical output
5. **Lazy Windows imports**: `pywin32` imported lazily so package works on all platforms
6. **Subprocess safety**: Arguments as sequences, never `shell=True`, always timeout, capture stdout/stderr, isolate temp directories, clean up on success/error/timeout

## Public API

```python
from gordon_doc_converter import ConversionRequest, convert

request = ConversionRequest.from_source(Path("example.docx"))
result = convert(request)
```

Key exports: `ConversionRequest`, `convert`, `DocumentConversionService`, `convert_batch`, `probe_engines`

## CLI Stable Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Invalid input or existing output |
| 3 | Engine or capability unavailability |
| 4 | Conversion failure, timeout, or missing output |
| 5 | PDF validation failure |

## Optional Dependencies

| Extra | Purpose |
|-------|---------|
| `word` | pywin32 for Word COM (Windows only) |
| `gotenberg` | httpx for Gotenberg remote adapter |
| `api` | FastAPI + uvicorn for HTTP API |
| `images` | Pillow + pypdfium2 for rasterization |

## Testing Conventions

- Unit tests must **not** require external engines; mock tools and platform APIs
- Integration tests marked with `@pytest.mark.integration`
- Word integration: Windows + licensed Office only, controlled environment
- Never commit customer data or licensed documents as fixtures

## Commit Convention

Conventional Commits: `<type>(<scope>): <imperative summary>`, ≤72 chars.

```
feat(engines): add Gotenberg timeout configuration
fix(cli): handle spaces in output path
docs(README): add Chinese translation link
```

## Documentation

- Public APIs use English docstrings; user documentation may have Traditional Chinese, Simplified Chinese, and Japanese translations
- `AGENTS.md` is the authoritative instruction source for AI assistants
- `AGENTS.zh-TW.md` is the human-readable translation
- Docs site source: `docs-src/`; generated output: `docs/` (do not edit directly)
- Rebuild docs: `uv sync --dev --extra api --locked && npm ci && npm run build`

## Security Rules

- Treat all input (filenames, paths, metadata, contents) as untrusted
- Do not log document contents, credentials, tokens, or sensitive paths
- Validate extension, MIME type, and OOXML ZIP structure when in scope
- Protect against oversized input, decompression bombs, corrupt/encrypted files
- API responses must not expose sensitive local paths or raw tracebacks

## Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Dependencies, tool config, build system |
| `AGENTS.md` | Authoritative AI assistant instructions |
| `CHANGELOG.md` | Version history and changes |
| `SECURITY.md` | Security policy and reporting |
| `docker/compose.yaml` | Container profiles for deployment |
