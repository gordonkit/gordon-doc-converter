from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from pypdf import PdfWriter

from gordon_doc_converter.engines.gotenberg import GotenbergEngine
from gordon_doc_converter.exceptions import (
    ConversionTimeoutError,
    EngineFailedError,
    PdfValidationError,
    UnsupportedAnnotationModeError,
)
from gordon_doc_converter.models import CommentMode, RevisionMode


@dataclass
class Response:
    status_code: int
    content: bytes = b""


class Client:
    def __init__(self, response: Response, *, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    def get(self, url: str, **kwargs: object) -> Response:
        self.calls.append(("GET", url, kwargs))
        if self.error is not None:
            raise self.error
        return self.response

    def post(self, url: str, **kwargs: object) -> Response:
        self.calls.append(("POST", url, kwargs))
        if self.error is not None:
            raise self.error
        return self.response


class TimeoutException(Exception):
    pass


def pdf_bytes(tmp_path: Path) -> bytes:
    path = tmp_path / "response.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as stream:
        writer.write(stream)
    return path.read_bytes()


def test_probe_reports_conservative_capabilities() -> None:
    client = Client(Response(200))
    result = GotenbergEngine(
        "https://example.invalid/", headers={"Authorization": "Bearer secret"}, client=client
    ).probe()

    assert result.available
    assert result.revision_modes == (RevisionMode.FINAL,)
    assert result.comment_modes == (CommentMode.OMIT,)
    assert client.calls[0][1] == "https://example.invalid/health"
    assert client.calls[0][2]["headers"] == {"Authorization": "Bearer secret"}


def test_probe_maps_outage_without_exposing_url() -> None:
    result = GotenbergEngine(
        "https://secret.example.invalid", client=Client(Response(0), error=OSError("secret"))
    ).probe()

    assert not result.available
    assert result.reason == "Gotenberg health probe failed"


def test_convert_posts_docx_and_validates_pdf(tmp_path: Path) -> None:
    source = tmp_path / "含 空格.docx"
    source.write_bytes(b"docx")
    output = tmp_path / "輸出.pdf"
    client = Client(Response(200, pdf_bytes(tmp_path)))

    result = GotenbergEngine("https://example.invalid", verify_tls=False, client=client).convert(
        source,
        output,
        timeout_seconds=15,
        revision_mode=RevisionMode.FINAL,
        comment_mode=CommentMode.OMIT,
    )

    assert result.output_path == output
    assert output.read_bytes() == client.response.content
    method, url, kwargs = client.calls[0]
    assert method == "POST"
    assert url.endswith("/forms/libreoffice/convert")
    assert kwargs["timeout"] == 15
    assert kwargs["verify"] is False


def test_convert_rejects_unsupported_annotations(tmp_path: Path) -> None:
    source = tmp_path / "source.docx"
    source.write_bytes(b"docx")

    with pytest.raises(UnsupportedAnnotationModeError):
        GotenbergEngine("https://example.invalid", client=Client(Response(200))).convert(
            source,
            tmp_path / "out.pdf",
            timeout_seconds=10,
            revision_mode=RevisionMode.MARKUP,
            comment_mode=CommentMode.OMIT,
        )


def test_convert_maps_timeout(tmp_path: Path) -> None:
    source = tmp_path / "source.docx"
    source.write_bytes(b"docx")
    engine = GotenbergEngine(
        "https://example.invalid", client=Client(Response(0), error=TimeoutException())
    )

    with pytest.raises(ConversionTimeoutError):
        engine.convert(
            source,
            tmp_path / "out.pdf",
            timeout_seconds=1,
            revision_mode=RevisionMode.FINAL,
            comment_mode=CommentMode.OMIT,
        )


def test_convert_maps_http_and_invalid_pdf(tmp_path: Path) -> None:
    source = tmp_path / "source.docx"
    source.write_bytes(b"docx")
    output = tmp_path / "out.pdf"

    def convert(response: Response) -> None:
        GotenbergEngine("https://example.invalid", client=Client(response)).convert(
            source_path=source,
            output_path=output,
            timeout_seconds=10,
            revision_mode=RevisionMode.FINAL,
            comment_mode=CommentMode.OMIT,
        )

    with pytest.raises(EngineFailedError) as http_error:
        convert(Response(503))
    assert http_error.value.retryable

    with pytest.raises(PdfValidationError):
        convert(Response(200, b"not pdf"))
