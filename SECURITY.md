# Security Policy

## Supported versions

| Version | Security fixes |
| --- | --- |
| Latest `0.x` release | Yes, until `1.0.0` is released |
| Earlier `0.x` releases | No; upgrade to the latest release |
| Release candidates (`1.0.0rcN`) | No; upgrade to the next candidate or to `1.0.0` |

From `1.0.0` on, security fixes are released for the latest minor version of the current
major version. When a new major version is released, the latest minor version of the
previous major version keeps receiving security fixes, and no other changes, for six months
from that release date.

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

## Response targets

Maintainers aim to:

1. acknowledge a report within 7 days;
2. complete an initial assessment, including whether it is a vulnerability and how severe it
   is, within 14 days of the report;
3. release a fix and publish an advisory within 90 days of the report.

These are targets, not guarantees. If a fix needs longer, maintainers tell the reporter and
agree on a new disclosure date with them. A fix that is ready earlier is released earlier.
Please keep the report private until the advisory is published or the 90 days have passed.
