# Compatibility Policy

> **Draft.** This policy takes effect with `1.0.0`. Until then, any `0.x` minor release may
> still change the surfaces listed here, as Semantic Versioning permits, and every such change
> is recorded in `CHANGELOG.md`. Items marked **Open decision** must be settled before `1.0.0`.

GordonKit Document Converter follows [Semantic Versioning](https://semver.org/). From `1.0.0`
on, a release that breaks a public contract below increments the major version. Minor
releases add behavior without breaking it; patch releases fix bugs and security issues.

## Public contracts

### Python library

The public Python API is exactly the set of names exported by `gordon_doc_converter.__all__`,
together with their documented parameters, fields, methods, and return types:

- conversion entry points: `convert`, `convert_batch`, `probe_engines`, and
  `DocumentConversionService`;
- request and result models: `ConversionRequest`, `ConversionOptions`, `ConversionResult`,
  `ArtifactResult`, `ArtifactItem`, `EngineProbeResult`, `PdfValidationResult`,
  `NormalizedAnnotation`, `AnnotationAnchor`, and `PageImageArtifact`;
- enumerations: `SourceFormat`, `ArtifactType`, `ArtifactStatus`, `EngineName`,
  `DeploymentMode`, `RevisionMode`, `CommentMode`, `AnnotationKind`, `PageImageFormat`, and
  `ErrorCode`;
- errors: `ConversionError`;
- page images and comparison: `PdfRasterizer`, `PdfiumPageRenderer`, `RasterOptions`,
  `PdfComparisonService`, `PdfComparisonReport`, and `PillowImageDiffer`.

Every other module, including `gordon_doc_converter.engines`, `content`, `process`, `api`, and
`cli`, is internal, as is any name beginning with an underscore. Internal code may change in
any release.

Compatible changes include adding a name to `__all__`, adding a keyword parameter with a
default, adding an optional field to a model, and adding a member to an enumeration. Callers
that match on an enumeration should handle unknown members.

### Command-line interface

- The commands `doctor`, `engines`, `template`, `convert`, `compare`, `batch`, and `version`,
  with their documented options and arguments.
- Exit codes: `0` success, `2` invalid input or an existing output, `3` engine or capability
  unavailable, `4` conversion failure, timeout, or missing output, and `5` PDF validation
  failure. A new failure category receives a new code; an existing code never changes meaning.
- The document emitted by `--json`. Fields may be added; existing fields are not removed,
  renamed, or retyped.

Human-readable text output, progress output on stderr, and help text are not contracts.

### Error and warning codes

- `ErrorCode` values are stable. New codes may be added in a minor release.
- Warning `code` values, such as `ENGINE_FALLBACK` and `LAYOUT_NOT_PRESERVED`, are stable
  once released. New warnings may be added in a minor release, so callers should ignore codes
  they do not recognize.
- `message` text, in errors and warnings alike, is for people and may change in any release.

### Structured YAML, JSON, and JSON Lines artifacts

The structured schema carries its own `schema_version`, independent of the package version.

- A minor schema version (`1.5` to `1.6`) only adds optional fields, block kinds, locator
  kinds, or record types. A document that uses none of them serializes exactly as before.
- A major schema version (`1.x` to `2.0`) is required to remove, rename, or retype a field,
  or to change its meaning, and ships only in a major package release.
- Optional fields are omitted rather than serialized as `null`. Readers should ignore unknown
  fields and block kinds.
- Byte offsets are not part of the locator contract. See the README for the reasons.

### Rendered artifacts

PDF, DOCX, ODT, HTML, Markdown, and page-image output are not byte-for-byte contracts. Engine
versions, fonts, and fixes to the writers change their exact bytes and layout. Their file
names and directory layout (`<stem>.pages/0001.png`, `<stem>.assets/`, and the annotation
sidecar) are contracts.

### HTTP API

**Open decision:** choose one before `1.0.0`.

1. Move every route under `/v1/` (keeping `/live` and `/ready` unversioned for probes) and
   cover it by this policy, so a later breaking change can ship as `/v2/` alongside `/v1/`.
2. Keep the current routes and declare the HTTP API experimental and outside this policy
   until it reaches parity with the CLI.

Either way, the request headers, status codes, and error body documented in the exported
OpenAPI contract (`docs/openapi.json`) are what the policy covers, and `GORDON_DOC_API_KEY`
and `GORDON_DOC_GOTENBERG_URL` are stable configuration names.

### Container image

- Image names, the tag scheme (`X.Y.Z`, `X.Y`, `latest`), the default CLI entrypoint, the
  `api` argument, and the Compose profile names are contracts.
- The installed engine set may grow in a minor release. Removing an engine, or a route that
  the image serves, is a breaking change.
- The base image and the versions of LibreOffice and other system packages are not contracts.

## Supported platforms

**Open decision:** the list below must match the CI matrix before `1.0.0`.

- Python: 3.12 is tested today. Each supported Python version is tested in CI. Support for
  a Python version is dropped only in a minor release, and only after it reaches end of life.
- Operating systems: Linux and Windows are tested today; macOS is not yet.
- Engines: support for an engine version is best effort. The project never promises identical
  rendering between Microsoft Word and LibreOffice.

## Deprecation

1. A public contract is deprecated in a minor release, with a `Deprecated` entry in
   `CHANGELOG.md` and, for Python APIs, a `DeprecationWarning` that names the replacement.
2. A deprecated contract keeps working for at least one further minor release, and is removed
   only in the next major release.
3. Security fixes are the only exception. When keeping a contract would leave users exposed,
   it may change in a minor or patch release, and the change is called out under `Security`.
