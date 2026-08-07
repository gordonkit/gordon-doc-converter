# Contributing

Use Python 3.12 or newer and `uv`. Before submitting a change, run:

```console
uv sync --dev
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest
uv build
```

Add tests for public behavior and regression tests for fixes. Unit tests must mock external
renderers. Do not commit customer documents, licensed fonts, credentials, or generated build
output. Commit messages use Conventional Commits in the form
`<type>(<scope>): <imperative summary>` and stay within 72 characters.

By participating, you agree to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
