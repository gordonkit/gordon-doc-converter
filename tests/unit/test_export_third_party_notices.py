"""Tests for deterministic third-party notice exports."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[2] / "scripts/export_third_party_notices.py"
PACKAGE_LICENSE_FILES = {
    "@heroicons/react": ("LICENSE",),
    "react": ("LICENSE",),
    "react-dom": ("LICENSE",),
    "swagger-ui-dist": ("LICENSE", "NOTICE"),
}


def test_export_third_party_notices_writes_and_checks_locked_licenses(tmp_path: Path) -> None:
    packages: dict[str, object] = {"": {"dependencies": {}}}
    for package_name, filenames in PACKAGE_LICENSE_FILES.items():
        packages[f"node_modules/{package_name}"] = {"version": "1.2.3"}
        package_path = tmp_path / "node_modules" / Path(*package_name.split("/"))
        package_path.mkdir(parents=True)
        for filename in filenames:
            (package_path / filename).write_text(
                f"{package_name} {filename} text\n", encoding="utf-8"
            )
    (tmp_path / "package-lock.json").write_text(
        json.dumps({"packages": packages}), encoding="utf-8"
    )
    output = Path("THIRD_PARTY_NOTICES.txt")

    export_result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), "--output", str(output)],
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )

    assert export_result.returncode == 0
    content = (tmp_path / output).read_text(encoding="utf-8")
    assert "@heroicons/react 1.2.3" in content
    assert "swagger-ui-dist NOTICE text" in content
    check_result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(tmp_path),
            "--output",
            str(output),
            "--check",
        ],
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    assert check_result.returncode == 0

    (tmp_path / output).write_text("stale\n", encoding="utf-8")
    stale_result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(tmp_path),
            "--output",
            str(output),
            "--check",
        ],
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    assert stale_result.returncode != 0
    assert "out of date" in stale_result.stderr
