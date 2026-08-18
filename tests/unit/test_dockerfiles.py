"""Container build policy tests."""

from pathlib import Path

import pytest

_ROOT = Path(__file__).parents[2]


@pytest.mark.parametrize(
    "dockerfile",
    (
        "docker/Dockerfile.cli",
        "docker/Dockerfile.standalone-lo",
        "docker/Dockerfile.gateway-gotenberg",
    ),
)
def test_runtime_images_upgrade_base_packages_before_install(dockerfile: str) -> None:
    content = (_ROOT / dockerfile).read_text(encoding="utf-8")
    runtime_stage = content.rsplit("FROM python:3.12-slim", maxsplit=1)[1]

    assert runtime_stage.index("apt-get update") < runtime_stage.index("apt-get upgrade -y")
    assert runtime_stage.index("apt-get upgrade -y") < runtime_stage.index("apt-get install")
