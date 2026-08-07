"""Optional FastAPI interface for private document-conversion deployments."""

from __future__ import annotations

from typing import Any


def create_app(**kwargs: Any) -> Any:
    """Create the API application, importing the optional framework on demand."""
    from gordon_doc_converter.api.app import create_app as _create_app

    return _create_app(**kwargs)


__all__ = ["create_app"]
