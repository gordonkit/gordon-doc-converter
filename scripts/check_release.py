"""Validate release versions across package metadata, source, tag, and changelog."""

from __future__ import annotations

import argparse
import ast
import re
import tomllib
from pathlib import Path


def _source_version(source: Path) -> str:
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        version_target = any(
            isinstance(target, ast.Name) and target.id == "__version__"
            for target in statement.targets
        )
        if version_target:
            value = ast.literal_eval(statement.value)
            if isinstance(value, str):
                return value
    raise ValueError(f"__version__ string not found in {source}")


def check_release(root: Path, *, tag: str | None = None) -> str:
    """Return the release version after validating all repository version sources."""
    metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project_version = metadata["project"]["version"]
    if not isinstance(project_version, str):
        raise ValueError("project.version must be a string")

    source_version = _source_version(root / "src/gordon_doc_converter/__init__.py")
    if source_version != project_version:
        raise ValueError(
            f"source version {source_version!r} does not match project version {project_version!r}"
        )

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    release_heading = rf"^## \[{re.escape(project_version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$"
    if re.search(release_heading, changelog, re.MULTILINE) is None:
        raise ValueError(f"dated changelog section for {project_version!r} not found")

    if tag is not None and tag != f"v{project_version}":
        raise ValueError(f"tag {tag!r} does not match project version {project_version!r}")
    return project_version


def main() -> int:
    """Validate release metadata from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--tag")
    arguments = parser.parse_args()
    version = check_release(arguments.root.resolve(), tag=arguments.tag)
    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
