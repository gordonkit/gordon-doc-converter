# Container profiles

The Compose file provides three explicitly selected profiles:

- `standalone-lo`: private HTTP API with LibreOffice in the same image.
- `gateway-gotenberg`: private HTTP API plus a separate Gotenberg renderer.
- `cli`: command-line image with LibreOffice and `/work` as its document volume.

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

The images run as a non-root user with a read-only root filesystem and bounded `/tmp` tmpfs.
Uploaded and generated documents are deleted before each request returns. No Microsoft Office
components or fonts are included.

Project license and third-party notice files are installed under
`/usr/share/licenses/gordon-doc-converter/`. Container CI also publishes a CycloneDX SBOM for
each profile as a workflow artifact.

After startup, `python docker/smoke.py --token replace-me --docx sample.docx` checks the
health, authenticated engine inventory, and an optional end-to-end conversion.
