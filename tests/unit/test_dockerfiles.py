"""Container build policy tests."""

from pathlib import Path

_ROOT = Path(__file__).parents[2]


def test_runtime_image_upgrade_base_packages_before_install() -> None:
    content = (_ROOT / "docker/Dockerfile").read_text(encoding="utf-8")
    runtime_stage = content.rsplit("FROM python:3.12-slim", maxsplit=1)[1]

    assert runtime_stage.index("apt-get update") < runtime_stage.index("apt-get upgrade -y")
    assert runtime_stage.index("apt-get upgrade -y") < runtime_stage.index("apt-get install")


def test_release_publishes_one_container_image_to_docker_hub_and_ghcr() -> None:
    content = (_ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert "needs: container-smoke" in content
    assert "profile: [standalone-lo, gateway-gotenberg]" in content
    assert "--docx tests/fixtures/docx/cjk/a4-portrait.docx" in content
    assert "gordon-doc-converter-${{ matrix.profile }}" not in content
    assert "${{ vars.DOCKERHUB_NAMESPACE }}/gordon-doc-converter\n" in content
    assert "ghcr.io/${{ github.repository }}\n" in content
    assert "registry: ghcr.io" in content
    assert "packages: write" in content
    assert "DOCKERHUB_USERNAME: ${{ secrets.DOCKERHUB_USERNAME }}" in content
    assert "DOCKERHUB_TOKEN: ${{ secrets.DOCKERHUB_TOKEN }}" in content
    assert "uses: docker/build-push-action@v" in content
    assert "uses: docker/setup-qemu-action@v" in content
    assert "platforms: linux/amd64,linux/arm64" in content
    assert "push: true" in content


def test_release_candidates_publish_without_moving_stable_tags() -> None:
    content = (_ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    # A PEP 440 candidate tag (v1.0.0rc1) must trigger the release at all.
    assert '"v[0-9]+.[0-9]+.[0-9]+rc[0-9]+"' in content
    # type=semver cannot read 1.0.0rc1; pep440 publishes it as PyPI spells it.
    assert "type=semver" not in content
    assert "type=pep440,pattern={{version}}" in content
    # The X.Y pattern skips pre-releases by itself, but latest has to be switched off.
    assert "flavor: latest=false" in content
    assert "type=raw,value=latest,enable=${{ !contains(github.ref_name, 'rc') }}" in content
    assert "PRERELEASE: ${{ contains(github.ref_name, 'rc') }}" in content
    assert "flags+=(--prerelease)" in content


def test_runtime_image_installs_the_page_image_extra() -> None:
    content = (_ROOT / "docker/Dockerfile").read_text(encoding="utf-8")

    # Without the images extra the container could not render a single page image.
    assert '".[api,gotenberg,images]"' in content


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


def test_ci_runs_on_pull_requests_with_a_usable_change_range() -> None:
    content = (_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    # Without this trigger a pull request only ever ran CodeQL, so dependency and
    # workflow breakage reached main before anything checked it.
    assert "pull_request:" in content
    # The path filter reads push-event fields, which a pull request does not carry.
    assert "github.event.pull_request.base.sha" in content
    assert "github.event.pull_request.head.sha" in content
    # A pull request must never publish the documentation site.
    assert "if: github.event_name == 'push' && github.ref == 'refs/heads/main'" in content


def test_release_rehearsal_exercises_the_container_publish_path() -> None:
    content = (_ROOT / ".github/workflows/test-release.yml").read_text(encoding="utf-8")
    release = (_ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    # release.yml runs only on a tag, so without this job a bump to either Docker
    # action would first execute during a real release.
    for action in (
        "docker/setup-qemu-action@",
        "docker/login-action@",
        "docker/build-push-action@",
        "docker/metadata-action@",
    ):
        assert action in content
        version = release.split(action, maxsplit=1)[1].splitlines()[0]
        assert f"{action}{version}" in content, f"{action} drifted from release.yml"
    # The rehearsal builds every platform the release publishes.
    assert "platforms: linux/amd64,linux/arm64" in content
    # The rehearsal must never publish an image.
    assert "push: false" in content
    assert "push: true" not in content
