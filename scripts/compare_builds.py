"""Compare two build directories for byte-for-byte reproducibility."""

from __future__ import annotations

import argparse
import hashlib
import tarfile
from pathlib import Path


def _artifact_digest(path: Path) -> str:
    """Hash wheels bytewise and source distributions by canonical member content."""
    if path.name.endswith(".tar.gz"):
        digest = hashlib.sha256()
        with tarfile.open(path, "r:gz") as archive:
            for member in sorted(archive.getmembers(), key=lambda item: item.name):
                digest.update(member.name.encode())
                digest.update(str(member.mode).encode())
                digest.update(str(member.size).encode())
                extracted = archive.extractfile(member) if member.isfile() else None
                if extracted is not None:
                    digest.update(extracted.read())
        return digest.hexdigest()
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digests(directory: Path) -> dict[str, str]:
    return {
        path.name: _artifact_digest(path)
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name.endswith((".whl", ".tar.gz"))
    }


def main() -> int:
    """Compare matching distribution artifacts in two directories."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    arguments = parser.parse_args()
    first = _digests(arguments.first)
    second = _digests(arguments.second)
    if not first or first != second:
        raise RuntimeError(f"builds differ: {first!r} != {second!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
