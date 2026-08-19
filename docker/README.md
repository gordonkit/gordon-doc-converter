# Container image and profiles

[繁體中文](README.zh-TW.md)

One `gordonkit/gordon-doc-converter` image provides both the CLI and HTTP API. The Compose
file provides three explicitly selected profiles:

- `standalone-lo`: private HTTP API using LibreOffice included in the image.
- `gateway-gotenberg`: the same HTTP API image plus a separate Gotenberg renderer.
- `cli`: command-line mode using included LibreOffice and `/work` as its document volume.

Tagged releases publish one Docker Hub repository:

- `<namespace>/gordon-doc-converter`

A release tag such as `v0.5.1` publishes the image tags `0.5.1`, `0.5`, and `latest` for
that repository. The image currently targets `linux/amd64`.

The image entrypoint runs the CLI by default. Pass `api` as the first argument to start the
HTTP API instead:

```console
docker run --rm gordonkit/gordon-doc-converter:latest version
docker run --rm --publish 8000:8000 \
  --env GORDON_DOC_API_KEY=replace-me \
  gordonkit/gordon-doc-converter:latest api
```

The Compose file builds `gordonkit/gordon-doc-converter:local` from the current source tree.
Use it for development and validation; use a versioned Docker Hub tag for deployments that
must be reproducible.

Set a strong `GORDON_DOC_API_KEY` before starting an API profile. Conversion requests use
the DOCX bytes as the request body, the OOXML MIME type as `Content-Type`, and the original
basename in `X-Filename`. The API performs bounded OOXML validation and accepts injectable
authentication, malware-scanning, and content-free telemetry hooks. Production ingress must
also cap request bodies and provide distributed rate limiting when multiple replicas are used.

```sh
GORDON_DOC_API_KEY=replace-me docker compose -f docker/compose.yaml \
  --profile standalone-lo up --build
curl --fail http://localhost:8000/live
curl --fail -H "Authorization: Bearer replace-me" \
  -H "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document" \
  -H "X-Filename: sample.docx" --data-binary @sample.docx \
  http://localhost:8000/conversions --output converted.pdf
```

To use Gotenberg, start the gateway profile. Compose attaches the API and Gotenberg services
to the same `gordon-doc` network, waits for Gotenberg to become healthy, and configures the API
to call `http://gotenberg:3000`:

```sh
GORDON_DOC_API_KEY=replace-me docker compose -f docker/compose.yaml \
  --profile gateway-gotenberg up --build
```

When `GORDON_DOC_GOTENBERG_URL` is configured, the API explicitly defaults to Gotenberg.
Connection or conversion failure is returned to the caller and does not silently fall back to
the included LibreOffice engine. Use the `standalone-lo` profile when local rendering is the
intended policy.

The image runs as a non-root user with a read-only root filesystem and bounded `/tmp` tmpfs.
Uploaded and generated documents are deleted before each request returns. No Microsoft Office
components or Microsoft fonts are included; the image installs Noto CJK fonts.

Project license and third-party notice files are installed under
`/usr/share/licenses/gordon-doc-converter/`. Container CI also publishes a CycloneDX SBOM.

After startup, `python docker/smoke.py --token replace-me --docx sample.docx` checks the
health, authenticated engine inventory, and an optional end-to-end conversion.

## Docker Hub release setup

Create the repository listed above in the intended Docker Hub user or organization.
Create a Docker Hub access token with read and write permission, then configure these GitHub
repository settings under **Settings > Secrets and variables > Actions**:

| Kind | Name | Value |
| --- | --- | --- |
| Variable | `DOCKERHUB_NAMESPACE` | Docker Hub user or organization that owns the repositories |
| Secret | `DOCKERHUB_USERNAME` | Docker Hub user that can push to the namespace |
| Secret | `DOCKERHUB_TOKEN` | Docker Hub access token; do not use the account password |

Pushing a matching release tag runs `.github/workflows/release.yml`. Before publishing, the
workflow runs the CLI and performs real DOCX-to-PDF conversions through both the standalone
LibreOffice and gateway-plus-Gotenberg Compose profiles. It then publishes the Python
distribution and pushes the image with Buildx, SBOM attestations, and build provenance:

```console
git tag -s v0.5.1 -m "Release v0.5.1"
git push origin v0.5.1
```

The tag must match the version in `pyproject.toml`. PyPI and Docker Hub are independent
registries, so a late Docker Hub failure can occur after the Python distribution is published.
Inspect every release job before announcing the release. Re-running a failed Docker job for the
same source tag updates the Docker tags to the same content.
