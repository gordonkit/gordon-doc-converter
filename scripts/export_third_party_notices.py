"""Export third-party notices for dependencies bundled into the documentation site."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

PACKAGE_LICENSE_FILES = {
    "@heroicons/react": ("LICENSE",),
    "react": ("LICENSE",),
    "react-dom": ("LICENSE",),
    "swagger-ui-dist": ("LICENSE", "NOTICE"),
}
DEFAULT_OUTPUTS = (
    Path("THIRD_PARTY_NOTICES.txt"),
    Path("docs-src/public/THIRD_PARTY_NOTICES.txt"),
)


def _package_path(root: Path, package_name: str) -> Path:
    return root / "node_modules" / Path(*package_name.split("/"))


def _render_notices(root: Path) -> str:
    lock_data: dict[str, Any] = json.loads((root / "package-lock.json").read_text(encoding="utf-8"))
    packages = lock_data.get("packages")
    if not isinstance(packages, dict):
        raise ValueError("package-lock.json does not contain a packages object")

    sections = [
        "GordonKit Document Converter - Third-Party Notices",
        "",
        "This file is generated from package-lock.json and the license files supplied by",
        "dependencies bundled into the static documentation site. Do not edit it manually.",
    ]
    for package_name, filenames in PACKAGE_LICENSE_FILES.items():
        lock_entry = packages.get(f"node_modules/{package_name}")
        if not isinstance(lock_entry, dict) or not isinstance(lock_entry.get("version"), str):
            raise ValueError(f"locked package metadata not found for {package_name}")
        sections.extend(("", "=" * 80, f"{package_name} {lock_entry['version']}", "=" * 80))
        package_path = _package_path(root, package_name)
        for filename in filenames:
            license_path = package_path / filename
            license_text = license_path.read_text(encoding="utf-8").strip()
            sections.extend(("", f"--- {filename} ---", "", license_text))
    return "\n".join(sections) + "\n"


def export_third_party_notices(root: Path, outputs: Sequence[Path], *, check: bool = False) -> None:
    """Write or verify deterministic third-party notice files."""
    content = _render_notices(root)
    for output in outputs:
        output_path = output if output.is_absolute() else root / output
        if check:
            if not output_path.is_file() or output_path.read_text(encoding="utf-8") != content:
                raise RuntimeError(f"{output_path} is out of date")
            continue
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8", newline="\n")


def main() -> int:
    """Export or verify the third-party notice files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", action="append", type=Path, dest="outputs")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    outputs = tuple(arguments.outputs) if arguments.outputs else DEFAULT_OUTPUTS
    export_third_party_notices(arguments.root.resolve(), outputs, check=arguments.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
