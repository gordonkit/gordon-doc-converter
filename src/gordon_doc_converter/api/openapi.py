"""OpenAPI export utilities for the optional HTTP adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from gordon_doc_converter.api.app import ApiSettings, create_app


def render_openapi() -> str:
    """Return a deterministic JSON representation of the public API contract."""
    app = create_app(settings=ApiSettings())
    schema = cast("dict[str, Any]", app.openapi())
    return f"{json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True)}\n"


def export_openapi(output: Path, *, check: bool = False) -> None:
    """Write the API contract, or verify that an existing export is current."""
    rendered = render_openapi()
    if check:
        if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
            raise RuntimeError(f"OpenAPI export is out of date: {output}")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
