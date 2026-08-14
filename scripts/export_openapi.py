"""Export the FastAPI OpenAPI contract for the static documentation site."""

from __future__ import annotations

import argparse
from pathlib import Path

from gordon_doc_converter.api.openapi import export_openapi

DEFAULT_OUTPUT = Path("docs-src/public/openapi.json")


def main() -> int:
    """Export or verify the static OpenAPI document."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    export_openapi(arguments.output, check=arguments.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
