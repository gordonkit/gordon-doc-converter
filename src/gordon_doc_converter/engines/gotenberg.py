"""Optional Gotenberg DOCX-to-PDF adapter."""

from __future__ import annotations

from collections.abc import Mapping
from importlib import import_module
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter
from typing import Protocol, cast

from gordon_doc_converter.engines.base import EngineExecutionResult
from gordon_doc_converter.exceptions import (
    ConversionTimeoutError,
    EngineFailedError,
    EngineUnavailableError,
    ErrorCode,
    InvalidInputError,
    OutputExistsError,
    PdfNotCreatedError,
    PdfValidationError,
    UnsupportedAnnotationModeError,
)
from gordon_doc_converter.models import CommentMode, EngineName, EngineProbeResult, RevisionMode
from gordon_doc_converter.validation import validate_pdf

_ENGINE = EngineName.GOTENBERG


class _Response(Protocol):
    status_code: int
    content: bytes


class _HttpClient(Protocol):
    def get(self, url: str, **kwargs: object) -> _Response: ...

    def post(self, url: str, **kwargs: object) -> _Response: ...


class _ManagedHttpClient(_HttpClient, Protocol):
    def __enter__(self) -> _ManagedHttpClient: ...

    def __exit__(self, *args: object) -> None: ...


class _ClientFactory(Protocol):
    def __call__(self, **kwargs: object) -> _ManagedHttpClient: ...


class GotenbergEngine:
    """Render DOCX files using Gotenberg's LibreOffice HTTP route.

    ``httpx`` is imported only when no client is injected, preserving the optional
    dependency boundary for core installations.
    """

    def __init__(
        self,
        base_url: str,
        *,
        headers: Mapping[str, str] | None = None,
        verify_tls: bool = True,
        probe_timeout_seconds: float = 10.0,
        max_pdf_bytes: int = 512 * 1024 * 1024,
        client: _HttpClient | None = None,
    ) -> None:
        if not base_url.strip():
            raise InvalidInputError("Gotenberg base_url cannot be empty")
        if probe_timeout_seconds <= 0:
            raise InvalidInputError("probe_timeout_seconds must be greater than zero")
        if max_pdf_bytes < 1:
            raise InvalidInputError("max_pdf_bytes must be greater than zero")
        self._base_url = base_url.rstrip("/")
        self._headers = dict(headers or {})
        self._verify_tls = verify_tls
        self._probe_timeout_seconds = probe_timeout_seconds
        self._max_pdf_bytes = max_pdf_bytes
        self._client = client

    @property
    def name(self) -> EngineName:
        """Return Gotenberg's stable public engine name."""
        return _ENGINE

    @staticmethod
    def _client_factory() -> _ClientFactory:
        try:
            httpx = import_module("httpx")
        except ImportError as exc:
            raise EngineUnavailableError(
                "Gotenberg support requires the optional 'gotenberg' dependency",
                engine=_ENGINE.value,
            ) from exc
        return cast("_ClientFactory", vars(httpx)["Client"])

    def _get(self, url: str, *, timeout: float) -> _Response:
        if self._client is not None:
            return self._client.get(
                url,
                headers=self._headers,
                timeout=timeout,
                verify=self._verify_tls,
            )
        with self._client_factory()(
            headers=self._headers,
            timeout=timeout,
            verify=self._verify_tls,
        ) as client:
            return client.get(url)

    def _post(self, url: str, *, timeout: float, files: object) -> _Response:
        if self._client is not None:
            return self._client.post(
                url,
                headers=self._headers,
                files=files,
                timeout=timeout,
                verify=self._verify_tls,
            )
        with self._client_factory()(
            headers=self._headers,
            timeout=timeout,
            verify=self._verify_tls,
        ) as client:
            return client.post(url, files=files)

    @staticmethod
    def _is_timeout(exc: Exception) -> bool:
        return exc.__class__.__name__ in {"TimeoutException", "ConnectTimeout", "ReadTimeout"}

    def probe(self) -> EngineProbeResult:
        """Check the Gotenberg health endpoint without exposing connection details."""
        try:
            response = self._get(
                f"{self._base_url}/health",
                timeout=self._probe_timeout_seconds,
            )
        except Exception as exc:
            return EngineProbeResult(
                engine=self.name,
                available=False,
                reason=(
                    "Gotenberg health probe timed out"
                    if self._is_timeout(exc)
                    else "Gotenberg health probe failed"
                ),
            )
        if response.status_code < 200 or response.status_code >= 300:
            return EngineProbeResult(
                engine=self.name,
                available=False,
                reason=f"Gotenberg health probe returned HTTP {response.status_code}",
            )
        return EngineProbeResult(
            engine=self.name,
            available=True,
            revision_modes=(RevisionMode.FINAL,),
            comment_modes=(CommentMode.OMIT,),
        )

    def convert(
        self,
        source_path: Path,
        output_path: Path,
        *,
        timeout_seconds: float,
        revision_mode: RevisionMode,
        comment_mode: CommentMode,
    ) -> EngineExecutionResult:
        """Render one DOCX into a validated PDF using a bounded HTTP request."""
        if timeout_seconds <= 0:
            raise InvalidInputError("timeout_seconds must be greater than zero")
        if source_path.suffix.casefold() != ".docx" or not source_path.is_file():
            raise InvalidInputError("Gotenberg source must be an existing DOCX file")
        if output_path.suffix.casefold() != ".pdf":
            raise InvalidInputError("Gotenberg output must use the .pdf extension")
        if output_path.exists():
            raise OutputExistsError("PDF output already exists")
        if revision_mode is not RevisionMode.FINAL or comment_mode is not CommentMode.OMIT:
            raise UnsupportedAnnotationModeError(
                "Gotenberg cannot honor the requested revision and comment modes",
                engine=self.name.value,
            )

        started = perf_counter()
        try:
            with source_path.open("rb") as source_stream:
                response = self._post(
                    f"{self._base_url}/forms/libreoffice/convert",
                    files={
                        "files": (
                            source_path.name,
                            source_stream,
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )
                    },
                    timeout=timeout_seconds,
                )
        except EngineUnavailableError:
            raise
        except Exception as exc:
            if self._is_timeout(exc):
                raise ConversionTimeoutError(
                    "Gotenberg conversion exceeded its timeout", engine=self.name.value
                ) from exc
            raise EngineUnavailableError(
                "Gotenberg conversion request failed", engine=self.name.value
            ) from exc
        if response.status_code < 200 or response.status_code >= 300:
            raise EngineFailedError(
                f"Gotenberg conversion returned HTTP {response.status_code}",
                engine=self.name.value,
                retryable=response.status_code >= 500,
            )
        if len(response.content) > self._max_pdf_bytes:
            raise EngineFailedError(
                "Gotenberg PDF exceeds the configured size limit",
                engine=self.name.value,
            )

        with NamedTemporaryFile(
            prefix="gordon-doc-gotenberg-", suffix=".pdf", delete=False
        ) as temp:
            temporary_path = Path(temp.name)
            temp.write(response.content)
        try:
            validation = validate_pdf(temporary_path)
            if not validation.valid:
                if (
                    validation.error is not None
                    and validation.error.code is ErrorCode.PDF_NOT_CREATED
                ):
                    raise PdfNotCreatedError(
                        "Gotenberg did not create a non-empty PDF", engine=self.name.value
                    )
                raise PdfValidationError("Gotenberg created an invalid PDF", engine=self.name.value)
            output_created = False
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with output_path.open("xb") as output_stream:
                    output_created = True
                    output_stream.write(response.content)
            except FileExistsError as exc:
                raise OutputExistsError("PDF output already exists") from exc
            except OSError as exc:
                if output_created:
                    output_path.unlink(missing_ok=True)
                raise EngineFailedError(
                    "Gotenberg PDF could not be written to the requested output",
                    engine=self.name.value,
                ) from exc
        finally:
            temporary_path.unlink(missing_ok=True)
        return EngineExecutionResult(
            engine=self.name,
            output_path=output_path,
            duration_seconds=perf_counter() - started,
        )
