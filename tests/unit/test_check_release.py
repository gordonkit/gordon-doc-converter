"""Tests for release metadata validation."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "scripts/check_release.py"


def _repository(tmp_path: Path, *, project_version: str, source_version: str) -> Path:
    source = tmp_path / "src/gordon_doc_converter"
    source.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "example"\nversion = "{project_version}"\n', encoding="utf-8"
    )
    (source / "__init__.py").write_text(f'__version__ = "{source_version}"\n', encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [{project_version}] - 2026-08-14\n", encoding="utf-8"
    )
    return tmp_path


def test_check_release_accepts_matching_sources(tmp_path: Path) -> None:
    root = _repository(tmp_path, project_version="0.4.0", source_version="0.4.0")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--tag", "v0.4.0"],
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "0.4.0"


def test_check_release_rejects_mismatched_source_version(tmp_path: Path) -> None:
    root = _repository(tmp_path, project_version="0.4.0", source_version="0.3.0")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )

    assert result.returncode != 0
    assert "does not match project version" in result.stderr
