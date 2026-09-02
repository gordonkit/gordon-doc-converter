"""Container build policy tests."""

from pathlib import Path

_ROOT = Path(__file__).parents[2]


def test_runtime_image_upgrade_base_packages_before_install() -> None:
    content = (_ROOT / "docker/Dockerfile").read_text(encoding="utf-8")
    runtime_stage = content.rsplit("FROM python:3.12-slim", maxsplit=1)[1]

    assert runtime_stage.index("apt-get update") < runtime_stage.index("apt-get upgrade -y")
    assert runtime_stage.index("apt-get upgrade -y") < runtime_stage.index("apt-get install")


def test_release_publishes_single_container_image_to_docker_hub() -> None:
    content = (_ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert "needs: container-smoke" in content
    assert "profile: [standalone-lo, gateway-gotenberg]" in content
    assert "--docx tests/fixtures/docx/cjk/a4-portrait.docx" in content
    assert "gordon-doc-converter-${{ matrix.profile }}" not in content
    assert "images: ${{ vars.DOCKERHUB_NAMESPACE }}/gordon-doc-converter" in content
    assert "DOCKERHUB_USERNAME: ${{ secrets.DOCKERHUB_USERNAME }}" in content
    assert "DOCKERHUB_TOKEN: ${{ secrets.DOCKERHUB_TOKEN }}" in content
    assert "uses: docker/build-push-action@v" in content
    assert "platforms: linux/amd64" in content
    assert "push: true" in content


def test_compose_connects_gateway_and_gotenberg_on_shared_network() -> None:
    content = (_ROOT / "docker/compose.yaml").read_text(encoding="utf-8")

    assert "GORDON_DOC_GOTENBERG_URL: http://gotenberg:3000" in content
    assert content.count('networks: ["gordon-doc"]') == 4
    assert "name: gordon-doc" in content


def test_compose_does_not_require_api_key_for_cli_profile() -> None:
    content = (_ROOT / "docker/compose.yaml").read_text(encoding="utf-8")

    assert "${GORDON_DOC_API_KEY:?" not in content
    assert content.count("GORDON_DOC_API_KEY: ${GORDON_DOC_API_KEY:-}") == 2


def test_container_entrypoint_requires_api_key_only_for_api() -> None:
    content = (_ROOT / "docker/entrypoint.sh").read_text(encoding="utf-8")

    api_branch = content.split('if [ "${1:-}" = "api" ]; then', maxsplit=1)[1]
    assert '[ -z "${GORDON_DOC_API_KEY:-}" ]' in api_branch
    assert "exit 64" in api_branch
    assert 'exec gordon-doc "$@"' in content
