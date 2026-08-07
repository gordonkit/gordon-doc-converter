"""Tests for the optional FastAPI adapter and its security boundaries."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfWriter

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from gordon_doc_converter.api.app import ApiSettings, create_app
from gordon_doc_converter.exceptions import ErrorCode, InvalidInputError
from gordon_doc_converter.models import (
    ArtifactResult,
    ArtifactStatus,
    ArtifactType,
    ConversionFailure,
    ConversionRequest,
    ConversionResult,
    EngineName,
    EngineProbeResult,
    SourceFormat,
)
from gordon_doc_converter.security import InputValidationLimits

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
FIXTURE = Path("tests/fixtures/docx/cjk/a4-portrait.docx")


class StubService:
    """Core-service test double which creates a valid PDF."""

    def __init__(self, *, available: bool = True, fail: bool = False) -> None:
        self.available = available
        self.fail = fail
        self.source_paths: list[Path] = []
        self.output_paths: list[Path] = []
        self.requests: list[ConversionRequest] = []

    def convert(self, request: ConversionRequest) -> ConversionResult:
        self.requests.append(request)
        self.source_paths.append(request.source_path)
        output = request.options.output_path
        assert output is not None
        self.output_paths.append(output)
        if self.fail:
            failure = ConversionFailure(ErrorCode.ENGINE_FAILED, "safe conversion failure")
            return ConversionResult(
                success=False,
                source_format=SourceFormat.DOCX,
                artifacts=(
                    ArtifactResult(
                        ArtifactType.PDF,
                        ArtifactStatus.FAILED,
                        error=failure,
                    ),
                ),
                error=failure,
            )
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with output.open("wb") as stream:
            writer.write(stream)
        return ConversionResult(
            success=True,
            source_format=SourceFormat.DOCX,
            artifacts=(
                ArtifactResult(
                    ArtifactType.PDF,
                    ArtifactStatus.SUCCESS,
                    path=output,
                    size_bytes=output.stat().st_size,
                ),
            ),
            selected_engine=request.options.engine,
        )

    def probe_engines(
        self, names: Sequence[EngineName] = tuple(EngineName)
    ) -> tuple[EngineProbeResult, ...]:
        return tuple(
            EngineProbeResult(engine=name, available=self.available, reason=None) for name in names
        )


def _client(
    service: StubService,
    *,
    input_limits: InputValidationLimits | None = None,
    rate_limit_requests: int = 30,
) -> TestClient:
    settings = ApiSettings(
        api_key="secret",
        input_limits=input_limits or InputValidationLimits(),
        rate_limit_requests=rate_limit_requests,
    )
    return TestClient(create_app(settings=settings, service=service))


def _convert(client: TestClient, **headers: str) -> Any:
    request_headers = {
        "Authorization": "Bearer secret",
        "X-Filename": "%E7%B9%81%E4%B8%AD%20%E6%96%87%E4%BB%B6.docx",
        "Content-Type": DOCX_MIME,
    }
    request_headers.update(headers)
    return client.post("/conversions", content=FIXTURE.read_bytes(), headers=request_headers)


def test_health_and_version_do_not_require_document_access() -> None:
    service = StubService()
    client = _client(service)

    assert client.get("/live").json() == {"status": "ok"}
    assert client.get("/ready").status_code == 200
    assert "version" in client.get("/version").json()


def test_ready_reports_unavailable_default_engine() -> None:
    response = _client(StubService(available=False)).get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not-ready"}


def test_conversion_uses_core_service_and_removes_temporary_files() -> None:
    service = StubService()
    events: list[tuple[str, object]] = []
    app = create_app(
        settings=ApiSettings(api_key="secret"),
        service=service,
        telemetry_hook=lambda event, fields: events.append((event, fields)),
    )

    response = _convert(TestClient(app))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert service.source_paths and not service.source_paths[0].exists()
    assert service.output_paths and not service.output_paths[0].exists()
    assert service.requests[0].options.deployment_mode.value == "container"
    assert service.requests[0].options.engine is EngineName.LIBREOFFICE
    assert events[0][0] == "conversion"
    assert str(service.source_paths[0]) not in str(events)


def test_conversion_cleans_up_after_core_failure_without_exposing_paths() -> None:
    service = StubService(fail=True)

    response = _convert(_client(service))

    assert response.status_code == 422
    assert response.json() == {"detail": "safe conversion failure"}
    assert not service.source_paths[0].exists()
    assert str(service.source_paths[0]) not in response.text


def test_authentication_and_engine_allowlist_are_enforced() -> None:
    service = StubService()
    client = _client(service)

    unauthorized = client.post(
        "/conversions",
        content=FIXTURE.read_bytes(),
        headers={"X-Filename": "sample.docx", "Content-Type": DOCX_MIME},
    )
    word = client.post(
        "/conversions?engine=word-com",
        content=FIXTURE.read_bytes(),
        headers={
            "Authorization": "Bearer secret",
            "X-Filename": "sample.docx",
            "Content-Type": DOCX_MIME,
            "X-Client-ID": "word",
        },
    )

    assert unauthorized.status_code == 401
    assert word.status_code == 400
    assert service.source_paths == []


def test_mime_size_malware_and_rate_limits_are_enforced() -> None:
    service = StubService()
    limits = InputValidationLimits(max_file_size=16)
    size_client = _client(service, input_limits=limits)
    oversized = _convert(size_client)

    wrong_mime = _client(StubService()).post(
        "/conversions",
        content=FIXTURE.read_bytes(),
        headers={
            "Authorization": "Bearer secret",
            "X-Filename": "sample.docx",
            "Content-Type": "text/plain",
        },
    )

    scanned: list[Path] = []

    def reject_malware(path: Path) -> bool:
        scanned.append(path)
        return False

    malware_app = create_app(
        settings=ApiSettings(api_key="secret"),
        service=service,
        malware_scan_hook=reject_malware,
    )
    malware = _convert(TestClient(malware_app), **{"X-Client-ID": "malware"})

    rate_client = _client(StubService(), rate_limit_requests=1)
    first = rate_client.get("/engines", headers={"Authorization": "Bearer secret"})
    second = rate_client.get("/engines", headers={"Authorization": "Bearer secret"})

    assert oversized.status_code == 413
    assert wrong_mime.status_code == 400
    assert malware.status_code == 400
    assert scanned and not scanned[0].exists()
    assert first.status_code == 200
    assert second.status_code == 429


def test_engines_never_advertise_word_com() -> None:
    response = _client(StubService()).get("/engines", headers={"Authorization": "Bearer secret"})

    assert response.status_code == 200
    assert [item["engine"] for item in response.json()] == ["libreoffice"]


def test_api_settings_reject_word_com() -> None:
    with pytest.raises(InvalidInputError, match="cannot use Word COM"):
        ApiSettings(default_engine=EngineName.WORD_COM)


def test_injected_auth_and_scanner_failures_are_mapped_safely() -> None:
    service = StubService()

    def unavailable_auth_hook(_authorization: str | None) -> bool:
        raise RuntimeError("secret")

    unavailable_auth = TestClient(
        create_app(
            settings=ApiSettings(),
            service=service,
            auth_hook=unavailable_auth_hook,
        )
    ).get("/engines")

    def unavailable_scanner(_path: Path) -> bool:
        raise RuntimeError("sensitive scanner detail")

    scanner_client = TestClient(
        create_app(
            settings=ApiSettings(api_key="secret"),
            service=service,
            malware_scan_hook=unavailable_scanner,
        )
    )
    unavailable_scanner_response = _convert(scanner_client)

    assert unavailable_auth.status_code == 503
    assert "secret" not in unavailable_auth.text
    assert unavailable_scanner_response.status_code == 503
    assert "sensitive" not in unavailable_scanner_response.text
