"""Tests for the static OpenAPI export."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from gordon_doc_converter.api.openapi import export_openapi


def test_export_openapi_writes_and_checks_deterministic_contract(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"

    export_openapi(output)
    schema = json.loads(output.read_text(encoding="utf-8"))

    assert schema["openapi"].startswith("3.1.")
    assert schema["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"
    assert "/conversions" in schema["paths"]
    export_openapi(output, check=True)


def test_export_openapi_check_rejects_stale_contract(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"
    output.write_text("{}\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="out of date"):
        export_openapi(output, check=True)
