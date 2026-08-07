"""Tests for the public synthetic CJK fixture matrix."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

FIXTURE_DIRECTORY = Path(__file__).parents[1] / "fixtures" / "docx" / "cjk"


def test_committed_fixtures_are_reproducible() -> None:
    """The committed OOXML packages must exactly match the generator."""
    subprocess.run(
        [sys.executable, "scripts/generate_cjk_fixtures.py", "--check"],
        check=True,
        timeout=30,
    )


def test_fixture_manifest_covers_required_cjk_matrix() -> None:
    """Every phase-7 layout feature must have a fixture."""
    manifest = json.loads((FIXTURE_DIRECTORY / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["format"] == "gordon-doc-converter-cjk-fixtures-v1"
    assert manifest["license"] == "CC0-1.0"
    assert len(manifest["fixtures"]) == 10


def test_all_fixtures_are_valid_ooxml_zip_packages() -> None:
    """Every fixture must include the minimum WordprocessingML package parts."""
    required = {
        "[Content_Types].xml",
        "_rels/.rels",
        "word/_rels/document.xml.rels",
        "word/document.xml",
        "word/settings.xml",
        "word/styles.xml",
    }
    for path in sorted(FIXTURE_DIRECTORY.glob("*.docx")):
        with ZipFile(path) as archive:
            assert archive.testzip() is None
            assert required <= set(archive.namelist())
            for name in archive.namelist():
                if name.endswith((".xml", ".rels")):
                    ElementTree.fromstring(archive.read(name))
