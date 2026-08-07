"""Minimal standard-library smoke client for a running API container."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _get_json(url: str, *, token: str | None = None) -> object:
    headers = {} if token is None else {"Authorization": f"Bearer {token}"}
    with urlopen(Request(url, headers=headers), timeout=10) as response:  # noqa: S310
        return json.load(response)


def main() -> int:
    """Check health and optionally exercise one DOCX-to-PDF conversion."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", required=True)
    parser.add_argument("--docx", type=Path)
    args = parser.parse_args()
    base_url = str(args.base_url).rstrip("/")
    if _get_json(f"{base_url}/live") != {"status": "ok"}:
        raise RuntimeError("liveness check failed")
    _get_json(f"{base_url}/engines", token=str(args.token))
    if args.docx is not None:
        source = args.docx
        request = Request(
            f"{base_url}/conversions",
            data=source.read_bytes(),
            headers={
                "Authorization": f"Bearer {args.token}",
                "Content-Type": DOCX_MIME,
                "X-Filename": source.name,
            },
            method="POST",
        )
        with urlopen(request, timeout=180) as response:  # noqa: S310
            if not response.read().startswith(b"%PDF"):
                raise RuntimeError("conversion did not return a PDF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
