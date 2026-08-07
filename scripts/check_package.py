"""Build-independent smoke check for an installed distribution wheel."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from venv import EnvBuilder


def _venv_executable(environment: Path, name: str) -> Path:
    scripts = environment / ("Scripts" if os.name == "nt" else "bin")
    suffix = ".exe" if os.name == "nt" else ""
    return scripts / f"{name}{suffix}"


def check_wheel(wheel: Path) -> None:
    """Install a wheel into a clean environment and smoke-test its public entry points."""
    if not wheel.is_file() or wheel.suffix != ".whl":
        raise ValueError(f"wheel does not exist: {wheel}")
    with TemporaryDirectory(prefix="gordon-package-check-") as temporary:
        environment = Path(temporary) / "venv"
        EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_executable(environment, "python")
        subprocess.run(
            [str(python), "-m", "pip", "install", "--disable-pip-version-check", str(wheel)],
            check=True,
            timeout=180,
        )
        subprocess.run(
            [
                str(python),
                "-c",
                "import importlib.metadata as m; import gordon_doc_converter; "
                "assert m.version('gordon-doc-converter') == gordon_doc_converter.__version__",
            ],
            check=True,
            timeout=30,
        )
        command = _venv_executable(environment, "gordon-doc")
        if command.exists():
            subprocess.run([str(command), "--help"], check=True, timeout=30)


def main() -> int:
    """Run the clean-environment wheel check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    arguments = parser.parse_args()
    check_wheel(arguments.wheel.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
