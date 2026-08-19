# Container image and profiles

[繁體中文](README.zh-TW.md)

One `gordonkit/gordon-doc-converter` image provides both the CLI and HTTP API. The Compose
file provides three explicitly selected profiles:

- `standalone-lo`: private HTTP API using LibreOffice included in the image.
- `gateway-gotenberg`: the same HTTP API image plus a separate Gotenberg renderer.
- `cli`: command-line mode using included LibreOffice and `/work` as its document volume.

Tagged releases publish one Docker Hub repository:

- `<namespace>/gordon-doc-converter`

A release tag such as `v0.6.0` publishes the image tags `0.6.0`, `0.6`, and `latest` for
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

## CLI profile

The CLI profile does not require an API key. Run this command from the repository root in
Bash or PowerShell; the current directory is mounted at `/work`:

```console
docker compose -f docker/compose.yaml --profile cli run --rm --build cli convert /work/report.docx --output /work/report.pdf --engine libreoffice --overwrite
```

## API profiles

Set a strong `GORDON_DOC_API_KEY` before starting an API profile. Create an untracked `.env`
file in the repository root so the same Compose commands work in Bash and PowerShell:

```dotenv
GORDON_DOC_API_KEY=replace-with-a-strong-random-value
```

The key is created and managed by the deployer; it is not issued by an external service. Do
not commit `.env`. Conversion requests use
the DOCX bytes as the request body, the OOXML MIME type as `Content-Type`, and the original
basename in `X-Filename`. The API performs bounded OOXML validation and accepts injectable
authentication, malware-scanning, and content-free telemetry hooks. Production ingress must
also cap request bodies and provide distributed rate limiting when multiple replicas are used.

### Standalone LibreOffice API

```console
docker compose -f docker/compose.yaml --env-file .env --profile standalone-lo up --detach --build
```

Bash:

```bash
set -a; . ./.env; set +a
curl --fail http://127.0.0.1:8000/live
curl --fail-with-body -H "Authorization: Bearer $GORDON_DOC_API_KEY" -H "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document" -H "X-Filename: report.docx" --data-binary @report.docx "http://127.0.0.1:8000/conversions?engine=libreoffice" --output report-api.pdf
```

PowerShell:

```powershell
$env:GORDON_DOC_API_KEY = ((Get-Content .env | Where-Object { $_ -match '^GORDON_DOC_API_KEY=' }) -replace '^GORDON_DOC_API_KEY=', '')
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/live'
$headers = @{ Authorization = "Bearer $env:GORDON_DOC_API_KEY"; 'X-Filename' = 'report.docx' }
Invoke-WebRequest -Uri 'http://127.0.0.1:8000/conversions?engine=libreoffice' -Method Post -Headers $headers -ContentType 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' -InFile .\report.docx -OutFile .\report-api.pdf
```

### Gotenberg gateway API

Compose attaches the API and Gotenberg services
to the same `gordon-doc` network, waits for Gotenberg to become healthy, and configures the API
to call `http://gotenberg:3000`:

```console
docker compose -f docker/compose.yaml --env-file .env --profile gateway-gotenberg up --detach --build
```

Bash:

```bash
set -a; . ./.env; set +a
curl --fail-with-body -H "Authorization: Bearer $GORDON_DOC_API_KEY" -H "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document" -H "X-Filename: report.docx" --data-binary @report.docx "http://127.0.0.1:8000/conversions?engine=gotenberg" --output report-gb.pdf
```

PowerShell:

```powershell
$env:GORDON_DOC_API_KEY = ((Get-Content .env | Where-Object { $_ -match '^GORDON_DOC_API_KEY=' }) -replace '^GORDON_DOC_API_KEY=', '')
$headers = @{ Authorization = "Bearer $env:GORDON_DOC_API_KEY"; 'X-Filename' = 'report.docx' }
Invoke-WebRequest -Uri 'http://127.0.0.1:8000/conversions?engine=gotenberg' -Method Post -Headers $headers -ContentType 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' -InFile .\report.docx -OutFile .\report-gb.pdf
```

When `GORDON_DOC_GOTENBERG_URL` is configured, the API explicitly defaults to Gotenberg.
Connection or conversion failure is returned to the caller and does not silently fall back to
the included LibreOffice engine. Use the `standalone-lo` profile when local rendering is the
intended policy.

Stop either API profile after testing:

```console
docker compose -f docker/compose.yaml --profile standalone-lo down
docker compose -f docker/compose.yaml --profile gateway-gotenberg down
```

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
git tag -s v0.6.0 -m "Release v0.6.0"
git push origin v0.6.0
```

The tag must match the version in `pyproject.toml`. PyPI and Docker Hub are independent
registries, so a late Docker Hub failure can occur after the Python distribution is published.
Inspect every release job before announcing the release. Re-running a failed Docker job for the
same source tag updates the Docker tags to the same content.
