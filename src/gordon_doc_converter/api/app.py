"""Resource-bounded FastAPI application built solely on the core service."""

from __future__ import annotations

import hmac
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from time import monotonic
from typing import Any, Protocol, cast
from urllib.parse import unquote

from gordon_doc_converter import __version__
from gordon_doc_converter.engines.gotenberg import GotenbergEngine
from gordon_doc_converter.engines.libreoffice import LibreOfficeEngine
from gordon_doc_converter.environment import EnvironmentInfo
from gordon_doc_converter.exceptions import ConversionError, InvalidInputError
from gordon_doc_converter.models import (
    ArtifactType,
    ConversionOptions,
    ConversionRequest,
    ConversionResult,
    DeploymentMode,
    EngineName,
    EngineProbeResult,
    SourceFormat,
)
from gordon_doc_converter.security import InputValidationLimits, validate_source_document
from gordon_doc_converter.service import DocumentConversionService

AuthHook = Callable[[str | None], bool]
MalwareScanHook = Callable[[Path], bool]
TelemetryHook = Callable[[str, Mapping[str, str | int | float | bool | None]], None]


class ConversionService(Protocol):
    """Subset of the core application service consumed by the HTTP adapter."""

    def convert(self, request: ConversionRequest) -> ConversionResult: ...

    def probe_engines(
        self, names: Sequence[EngineName] = tuple(EngineName)
    ) -> tuple[EngineProbeResult, ...]: ...


@dataclass(frozen=True, slots=True)
class ApiSettings:
    """Security and resource limits for one API process."""

    api_key: str | None = None
    gotenberg_url: str | None = None
    default_engine: EngineName = EngineName.LIBREOFFICE
    timeout_seconds: float = 120.0
    max_concurrent_conversions: int = 2
    rate_limit_requests: int = 30
    rate_limit_window_seconds: float = 60.0
    input_limits: InputValidationLimits = InputValidationLimits()

    def __post_init__(self) -> None:
        if self.default_engine is EngineName.WORD_COM:
            raise InvalidInputError("the API cannot use Word COM")
        if self.timeout_seconds <= 0:
            raise InvalidInputError("API timeout must be greater than zero")
        if self.max_concurrent_conversions <= 0:
            raise InvalidInputError("API concurrency limit must be greater than zero")
        if self.rate_limit_requests <= 0 or self.rate_limit_window_seconds <= 0:
            raise InvalidInputError("API rate limits must be greater than zero")


class _FixedWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._clients: dict[str, tuple[float, int]] = {}
        self._lock = Lock()

    def allow(self, identity: str) -> bool:
        """Consume one request from a bounded, process-local fixed window."""
        now = monotonic()
        with self._lock:
            started, count = self._clients.get(identity, (now, 0))
            if now - started >= self._window_seconds:
                started, count = now, 0
            if count >= self._limit:
                return False
            self._clients[identity] = (started, count + 1)
            return True


class _ConcurrencyLimiter:
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._active = 0
        self._lock = Lock()

    def acquire(self) -> bool:
        """Acquire capacity without queueing unbounded request bodies."""
        with self._lock:
            if self._active >= self._limit:
                return False
            self._active += 1
            return True

    def release(self) -> None:
        """Release previously acquired conversion capacity."""
        with self._lock:
            self._active -= 1


def _default_auth_hook(api_key: str | None) -> AuthHook:
    def authenticate(authorization: str | None) -> bool:
        if api_key is None:
            return True
        expected = f"Bearer {api_key}"
        return authorization is not None and hmac.compare_digest(authorization, expected)

    return authenticate


def _default_service(settings: ApiSettings) -> DocumentConversionService:
    engines: list[Any] = [LibreOfficeEngine()]
    if settings.gotenberg_url is not None:
        engines.append(GotenbergEngine(settings.gotenberg_url))
    return DocumentConversionService(
        engines=engines,
        environment=EnvironmentInfo(platform="linux", interactive=False),
    )


def _safe_engine_payload(probe: EngineProbeResult) -> dict[str, object]:
    return {
        "engine": probe.engine.value,
        "available": probe.available,
        "version": probe.version,
        "reason": probe.reason,
        "revision_modes": [mode.value for mode in probe.revision_modes],
        "comment_modes": [mode.value for mode in probe.comment_modes],
    }


def create_app(
    *,
    settings: ApiSettings | None = None,
    service: ConversionService | None = None,
    auth_hook: AuthHook | None = None,
    malware_scan_hook: MalwareScanHook | None = None,
    telemetry_hook: TelemetryHook | None = None,
) -> Any:
    """Create a private-deployment API with injectable security integration hooks."""
    try:
        fastapi = import_module("fastapi")
        responses = import_module("fastapi.responses")
    except ImportError as exc:
        raise RuntimeError(
            "API support requires installation with the 'api' optional dependency"
        ) from exc

    gotenberg_url = os.environ.get("GORDON_DOC_GOTENBERG_URL")
    configured = settings or ApiSettings(
        api_key=os.environ.get("GORDON_DOC_API_KEY"),
        gotenberg_url=gotenberg_url,
        default_engine=EngineName.GOTENBERG
        if gotenberg_url is not None
        else EngineName.LIBREOFFICE,
    )
    conversion_service = service or _default_service(configured)
    authenticate = auth_hook or _default_auth_hook(configured.api_key)
    scan = malware_scan_hook or (lambda _path: True)
    telemetry = telemetry_hook or (lambda _event, _fields: None)
    rate_limiter = _FixedWindowRateLimiter(
        configured.rate_limit_requests, configured.rate_limit_window_seconds
    )
    concurrency = _ConcurrencyLimiter(configured.max_concurrent_conversions)

    app = fastapi.FastAPI(title="GordonKit Document Converter", version=__version__)
    Body = fastapi.Body
    Header = fastapi.Header
    Query = fastapi.Query
    HTTPException = fastapi.HTTPException
    Response = responses.Response

    def authorize(authorization: str | None) -> None:
        try:
            authenticated = authenticate(authorization)
        except Exception as exc:
            raise HTTPException(
                status_code=503, detail="authentication service unavailable"
            ) from exc
        if not authenticated:
            raise HTTPException(status_code=401, detail="authentication failed")
        if not rate_limiter.allow("authenticated-client"):
            raise HTTPException(status_code=429, detail="rate limit exceeded")

    def record_telemetry(event: str, fields: Mapping[str, str | int | float | bool | None]) -> None:
        try:
            telemetry(event, fields)
        except Exception:
            return

    def convert_document(
        body: bytes = Body(..., media_type="application/octet-stream"),
        x_filename: str = Header(..., alias="X-Filename"),
        content_type: str | None = Header(None, alias="Content-Type"),
        authorization: str | None = Header(None, alias="Authorization", include_in_schema=False),
        engine: str | None = Query(None),
    ) -> Any:
        authorize(authorization)
        if not concurrency.acquire():
            raise HTTPException(status_code=429, detail="conversion capacity exhausted")
        started = monotonic()
        try:
            try:
                requested_engine = (
                    configured.default_engine if engine is None else EngineName(engine)
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=400, detail="unsupported conversion engine"
                ) from exc
            if requested_engine is EngineName.WORD_COM:
                raise HTTPException(
                    status_code=400, detail="Word COM is not available through the API"
                )
            if requested_engine is EngineName.GOTENBERG and configured.gotenberg_url is None:
                raise HTTPException(status_code=400, detail="Gotenberg is not configured")
            if len(body) > configured.input_limits.max_file_size:
                raise HTTPException(
                    status_code=413, detail="source document exceeds the size limit"
                )
            safe_name = Path(unquote(x_filename)).name
            if not safe_name or safe_name.casefold().endswith(".docx") is False:
                raise HTTPException(status_code=400, detail="source must have a .docx filename")
            with TemporaryDirectory(prefix="gordon-doc-api-") as temporary:
                workspace = Path(temporary)
                source_path = workspace / safe_name
                output_path = workspace / "converted.pdf"
                try:
                    source_path.write_bytes(body)
                    validate_source_document(
                        source_path,
                        SourceFormat.DOCX,
                        declared_mime_type=content_type,
                        limits=configured.input_limits,
                    )
                    try:
                        clean = scan(source_path)
                    except Exception as exc:
                        raise HTTPException(
                            status_code=503, detail="malware scanning is unavailable"
                        ) from exc
                    if not clean:
                        raise InvalidInputError("source document failed malware scanning")
                except ConversionError as exc:
                    raise HTTPException(status_code=400, detail=exc.message) from exc
                except OSError as exc:
                    raise HTTPException(
                        status_code=500, detail="source could not be staged"
                    ) from exc
                request = ConversionRequest(
                    source_path=source_path,
                    source_format=SourceFormat.DOCX,
                    artifacts=(ArtifactType.PDF,),
                    options=ConversionOptions(
                        output_path=output_path,
                        timeout_seconds=configured.timeout_seconds,
                        deployment_mode=DeploymentMode.CONTAINER,
                        engine=requested_engine,
                        container_engine=requested_engine,
                    ),
                )
                try:
                    result = conversion_service.convert(request)
                except Exception as exc:
                    record_telemetry(
                        "conversion", {"success": False, "duration": monotonic() - started}
                    )
                    raise HTTPException(
                        status_code=500, detail="conversion service failed"
                    ) from exc
                if not result.success or result.error is not None:
                    detail = (
                        result.error.message if result.error is not None else "conversion failed"
                    )
                    record_telemetry(
                        "conversion", {"success": False, "duration": monotonic() - started}
                    )
                    raise HTTPException(status_code=422, detail=detail)
                try:
                    pdf = output_path.read_bytes()
                except OSError as exc:
                    raise HTTPException(
                        status_code=500, detail="conversion output is unavailable"
                    ) from exc
                record_telemetry(
                    "conversion",
                    {
                        "success": True,
                        "engine": result.selected_engine.value
                        if result.selected_engine is not None
                        else None,
                        "input_bytes": len(body),
                        "output_bytes": len(pdf),
                        "duration": monotonic() - started,
                    },
                )
                return Response(
                    content=pdf,
                    media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="converted.pdf"'},
                )
        finally:
            concurrency.release()

    def engines_endpoint(
        authorization: str | None = Header(None, alias="Authorization", include_in_schema=False),
    ) -> list[dict[str, object]]:
        authorize(authorization)
        names = [EngineName.LIBREOFFICE]
        if configured.gotenberg_url is not None:
            names.append(EngineName.GOTENBERG)
        return [_safe_engine_payload(item) for item in conversion_service.probe_engines(names)]

    def live() -> dict[str, str]:
        return {"status": "ok"}

    def ready() -> Any:
        names = [configured.default_engine]
        probes = conversion_service.probe_engines(names)
        if probes and probes[0].available:
            return {"status": "ready"}
        return fastapi.responses.JSONResponse(
            status_code=503,
            content={"status": "not-ready"},
        )

    def version() -> dict[str, str]:
        return {"version": __version__}

    bearer_security: dict[str, Any] = {"security": [{"BearerAuth": []}]}
    app.add_api_route(
        "/conversions",
        convert_document,
        methods=["POST"],
        response_class=Response,
        responses={
            200: {
                "description": "Converted PDF document",
                "content": {"application/pdf": {"schema": {"type": "string", "format": "binary"}}},
            },
            400: {"description": "Invalid document or conversion options"},
            401: {"description": "Authentication failed"},
            413: {"description": "Source document exceeds the size limit"},
            422: {"description": "Conversion failed"},
            429: {"description": "Rate or concurrency limit exceeded"},
            500: {"description": "Conversion service failed"},
            503: {"description": "Authentication or malware scanning unavailable"},
        },
        tags=["conversion"],
        summary="Convert a DOCX document to PDF",
        openapi_extra=bearer_security,
    )
    app.add_api_route(
        "/engines",
        engines_endpoint,
        methods=["GET"],
        tags=["engines"],
        summary="List available conversion engines",
        openapi_extra=bearer_security,
    )
    app.add_api_route("/live", live, methods=["GET"], tags=["health"])
    app.add_api_route("/ready", ready, methods=["GET"], tags=["health"])
    app.add_api_route("/version", version, methods=["GET"], tags=["metadata"])

    default_openapi = app.openapi

    def openapi() -> dict[str, Any]:
        schema = cast("dict[str, Any]", default_openapi())
        components = schema.setdefault("components", {})
        security_schemes = components.setdefault("securitySchemes", {})
        security_schemes["BearerAuth"] = {"type": "http", "scheme": "bearer"}
        return schema

    app.openapi = openapi
    return cast("Any", app)


__all__ = ["ApiSettings", "AuthHook", "MalwareScanHook", "TelemetryHook", "create_app"]
