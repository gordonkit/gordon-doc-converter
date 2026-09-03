# Repository Guidance

## Purpose and Current Scope

GordonKit Document Converter is a Python 3.12+ orchestration library for converting
DOCX files to PDF through external rendering engines. It does not implement a document
renderer. The v0.1 deliverables are the core Python library and CLI; API and container
work belong to later phases unless a task explicitly changes the roadmap.

The package name is `gordon-doc-converter`, the import package is
`gordon_doc_converter`, and the CLI command is `gordon-doc`.

## Tooling and Standard Commands

- Use `uv` for dependency management and command execution.
- Install or synchronize the environment with `uv sync --dev`.
- Format with `uv run ruff format .`.
- Lint with `uv run ruff check .`.
- Type-check with `uv run mypy src` after `src/` exists.
- Run tests with `uv run pytest` after `tests/` exists.
- Before handing off a code change, run every relevant check above. If a check cannot
  run because the corresponding source or test directory does not exist yet, state that
  clearly instead of creating placeholder files only to satisfy the command.

Do not edit `uv.lock` manually. Update it through `uv` when dependency changes are
authorized.

## Architecture Boundaries

- Keep the core library independent of CLI and API frameworks.
- CLI commands and future API routes call the application service; they must not call
  conversion engines directly.
- All conversion engines implement one shared engine protocol.
- Keep engine selection, deployment-mode policy, fallback, and orchestration outside
  individual engine adapters.
- Do not expose Word COM, LibreOffice, or Gotenberg-specific response types through the
  public core API.
- Separate operating-system detection from engine execution.
- Import Windows-only dependencies lazily so the core package remains importable on
  Windows, Linux, and macOS.
- Prefer small, focused functions and composition. Avoid premature abstractions and
  hidden global state.

The intended dependency direction is:

```text
Library / CLI / future API
          -> application service and orchestrator
          -> shared engine protocol
          -> Word COM / LibreOffice / optional Gotenberg adapters
          -> PDF validation and structured conversion result
```

## Conversion and Platform Rules

- Use Word COM automatically only on an interactive Windows desktop.
- Never select Word COM automatically for server or container modes.
- Server mode prefers Gotenberg, then LibreOffice. Container mode uses LibreOffice or
  Gotenberg according to its image profile.
- Explicit engine selection and strict modes must never silently fall back.
- Automatic fallback results must identify the attempted engine, failure reason, final
  engine, and a warning.
- Do not promise identical rendering between Microsoft Word and LibreOffice.
- Do not download, bundle, or redistribute Microsoft fonts or Office components.

## Python and Process Safety

- Follow the Ruff and strict mypy settings in `pyproject.toml`.
- Add complete type annotations and English docstrings to public APIs.
- Use `pathlib.Path` for internal filesystem operations and UTF-8 for text files.
- Support Traditional Chinese filenames and paths containing spaces.
- Do not overwrite an existing output unless the caller explicitly requests it.
- Restrict subprocess use to engine adapters or a dedicated process utility.
- Pass subprocess arguments as a sequence, never use `shell=True`, always set a timeout,
  and capture stdout and stderr.
- Isolate temporary directories and LibreOffice profiles per conversion. Clean up on
  success, error, and timeout, including child processes where applicable.
- Preserve the original exception as the cause when mapping failures to project
  exceptions. Never swallow broad exceptions.
- Never silently switch conversion engines after a failure.

## Security and Privacy

- Treat filenames, paths, document metadata, and document contents as untrusted input.
- Do not log document contents, credentials, tokens, customer documents, sensitive full
  paths, or non-redistributable fonts.
- User-facing API responses must not expose sensitive local paths or raw tracebacks.
- Fixtures must contain public or generated content only; never commit customer data or
  licensed documents.
- Validate extension, MIME type, and OOXML ZIP structure when input validation is in
  scope. Protect against oversized input, decompression bombs, corrupt files, and
  encrypted files.

## Testing Expectations

- Add tests for every new public behavior and a regression test for every bug fix.
- Unit tests must not require Microsoft Word, LibreOffice, or Gotenberg. Mock external
  tools and platform APIs.
- Mark integration and platform-specific tests explicitly with pytest markers.
- Cover policy branches, stable error mapping, JSON serialization, fallback and strict
  behavior, timeout, cleanup, and PDF validation as applicable.
- Real Word integration tests run only on a controlled Windows environment with a
  licensed Office installation. Do not assume hosted CI runners provide Word.

## Release Process

- A release is triggered by pushing a tag matching `v[0-9]+.[0-9]+.[0-9]+`, and by nothing
  else. Merging a release pull request publishes nothing. Existing tags are annotated; keep
  that convention.
- The tag publishes to PyPI, Docker Hub, and GitHub Releases at once. None of it can be
  undone: a PyPI version number can never be reused, so a broken `0.9.0` must be abandoned
  in favour of `0.9.1`.
- Rehearse first with `gh workflow run test-release.yml --ref main -f target=all`, which
  publishes to TestPyPI, downloads the wheel back, and builds the container image without
  pushing it. Use `target=containers` to exercise only the Docker path, or `target=pypi`
  for only the package. TestPyPI version numbers are equally unreusable, so bump the
  version before rehearsing the same release twice.
- `scripts/check_release.py` gates the tag. It requires `project.version` in
  `pyproject.toml`, `__version__` in `src/gordon_doc_converter/__init__.py`, and the tag to
  agree, plus a dated `## [X.Y.Z] - YYYY-MM-DD` section in `CHANGELOG.md`. Run
  `uv run python scripts/check_release.py --tag vX.Y.Z` before tagging.
- Bumping a version touches five tracked places — `pyproject.toml`, `__version__`,
  the CLI version assertion in `tests/unit/cli/test_app.py`, `uv.lock` (through `uv lock`),
  and the exported OpenAPI contract (through `npm run openapi:export` plus `npm run build`,
  which refreshes the committed `docs/` copy).
- In `CHANGELOG.md`, keep the empty `## [Unreleased]` heading and insert the dated release
  section directly below it. Write the entries when the change lands, not at release time.
- `release.yml` runs only on a tag and matches no path filter in `ci.yml`, so a dependency
  bump inside it is unexercised by ordinary CI. The rehearsal covers the login, metadata,
  and build steps; the `type=semver` tag templates are reached only by a real tag.

## Documentation and Change Discipline

- Use English for public API names and docstrings. User documentation may have
  Traditional Chinese, Simplified Chinese, and Japanese translations.
- Keep behavior, CLI options, error codes, and documented examples synchronized.
- Prefer narrow changes that match the requested phase and preserve public contracts.
- Do not add production dependencies without checking necessity, license, maintenance,
  and security impact.
- Follow Conventional Commits using
  `<type>(<scope>): <imperative summary>`, concise English, and at most 72 characters.
- Treat `AGENTS.zh-TW.md` as a human-readable translation. This file is the authoritative
  Codex instruction source; update both files together when these rules change.

