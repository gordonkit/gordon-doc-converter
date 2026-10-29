# Security Policy

## Supported versions

| Version | Security fixes |
| --- | --- |
| Latest `0.x` release | Yes, until `1.0.0` is released |
| Earlier `0.x` releases | No; upgrade to the latest release |

From `1.0.0` on, security fixes are released for the latest minor version of the current
major version.

Fixes ship as patch releases and are listed under `Security` in `CHANGELOG.md`. A fix that
cannot keep a public contract may change it in a minor or patch release, as described in
[COMPATIBILITY.md](COMPATIBILITY.md).

The supported versions cover the Python package and the container image built from the same
tag. The engines the project drives, such as LibreOffice, Microsoft Word, Pandoc,
wkhtmltopdf, and Gotenberg, are maintained by their own projects; report vulnerabilities in
them upstream.

## Reporting a vulnerability

Do not open a public issue. Report vulnerabilities privately to the repository maintainers
through the hosting provider's private security-advisory feature. Include the affected
version, reproducible steps, impact, and any suggested mitigation. Do not include customer
documents, credentials, or personal data.

Maintainers will acknowledge a report, investigate it, and coordinate disclosure. No
response-time guarantee is made before a formal security response process is published.
