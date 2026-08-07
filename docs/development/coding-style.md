# Python Coding Standards

Python source targets 3.12 or newer and must pass Ruff formatting/linting and strict mypy.
Public APIs use complete type annotations and English docstrings. Prefer typed immutable
dataclasses, enums, protocols, `pathlib.Path`, small focused functions, dependency injection,
and composition.

Core modules remain independent of presentation frameworks and engine-specific response
types. Platform-specific dependencies are loaded lazily. Subprocesses belong only in engine
adapters or a dedicated process utility; arguments are sequences, `shell=True` is forbidden,
timeouts and captured output are mandatory, and conversion-owned temporary data is cleaned on
every outcome.

Do not overwrite output without explicit permission. Treat paths and document data as
untrusted. Never log document contents, credentials, sensitive metadata, or sensitive full
paths. Translate failures to project errors while retaining exception chaining where an
exception boundary is used.

Every public behavior and regression requires a test. Unit tests mock external renderers and
must run without Word, LibreOffice, or Gotenberg. Integration and platform-specific tests use
explicit pytest markers.
