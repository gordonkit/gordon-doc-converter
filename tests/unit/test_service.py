"""End-to-end unit coverage for the public document conversion service."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfWriter

from gordon_doc_converter.engines.base import EngineExecutionResult
from gordon_doc_converter.environment import EnvironmentInfo
from gordon_doc_converter.exceptions import EngineFailedError, ErrorCode
from gordon_doc_converter.models import (
    ArtifactStatus,
    ArtifactType,
    CommentMode,
    ConversionOptions,
    ConversionRequest,
    DeploymentMode,
    EngineName,
    EngineProbeResult,
    RevisionMode,
    SourceFormat,
)
from gordon_doc_converter.service import DocumentConversionService

WINDOWS_DESKTOP = EnvironmentInfo("win32", True)
LINUX_DESKTOP = EnvironmentInfo("linux", True)


def _write_pdf(path: Path, label: str = "") -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72 + len(label), height=72)
    with path.open("wb") as stream:
        writer.write(stream)


def _write_invalid_pdf(source_path: Path, output_path: Path) -> None:
    del source_path
    output_path.write_bytes(b"invalid")


def _write_office_document(
    source_path: Path,
    output_path: Path,
    artifact_type: ArtifactType,
) -> None:
    del source_path, artifact_type
    output_path.write_bytes(b"converted office document")


def _probe(
    name: EngineName,
    *,
    available: bool = True,
    revisions: tuple[RevisionMode, ...] = (RevisionMode.FINAL,),
    comments: tuple[CommentMode, ...] = (CommentMode.OMIT,),
) -> EngineProbeResult:
    return EngineProbeResult(
        engine=name,
        available=available,
        reason=None if available else "not installed",
        revision_modes=revisions,
        comment_modes=comments,
    )


@dataclass
class StubEngine:
    """Configurable rendering engine used at the complete service boundary."""

    name: EngineName
    probe_result: EngineProbeResult
    render: Callable[[Path, Path], None]
    calls: list[tuple[Path, Path]] = field(default_factory=list)
    option_calls: list[tuple[float, RevisionMode, CommentMode]] = field(default_factory=list)
    probe_error: Exception | None = None
    file_render: Callable[[Path, Path, ArtifactType], None] | None = None

    def probe(self) -> EngineProbeResult:
        if self.probe_error is not None:
            raise self.probe_error
        return self.probe_result

    def convert(
        self,
        source_path: Path,
        output_path: Path,
        *,
        timeout_seconds: float,
        revision_mode: RevisionMode,
        comment_mode: CommentMode,
    ) -> EngineExecutionResult:
        self.calls.append((source_path, output_path))
        self.option_calls.append((timeout_seconds, revision_mode, comment_mode))
        self.render(source_path, output_path)
        return EngineExecutionResult(self.name, output_path, 0.01)

    def convert_file(
        self,
        source_path: Path,
        output_path: Path,
        *,
        source_format: SourceFormat,
        artifact_type: ArtifactType,
        timeout_seconds: float,
    ) -> EngineExecutionResult:
        del source_format, timeout_seconds
        if self.file_render is None:
            raise AssertionError("file renderer was not configured")
        self.file_render(source_path, output_path, artifact_type)
        return EngineExecutionResult(self.name, output_path, 0.01)


def _source(tmp_path: Path, name: str = "臺灣 文件.docx") -> Path:
    source = tmp_path / name
    source.write_bytes(b"generated public content")
    return source


def _request(
    source: Path,
    *,
    overwrite: bool = False,
    engine: EngineName | None = None,
    deployment_mode: DeploymentMode = DeploymentMode.DESKTOP,
    timeout_seconds: float = 120.0,
    revision_mode: RevisionMode = RevisionMode.FINAL,
    comment_mode: CommentMode = CommentMode.OMIT,
) -> ConversionRequest:
    return ConversionRequest.from_source(
        source,
        options=ConversionOptions(
            overwrite=overwrite,
            engine=engine,
            deployment_mode=deployment_mode,
            timeout_seconds=timeout_seconds,
            revision_mode=revision_mode,
            comment_mode=comment_mode,
        ),
    )


def test_successful_conversion_returns_valid_stable_result(tmp_path: Path) -> None:
    source = _source(tmp_path)
    engine = StubEngine(
        EngineName.LIBREOFFICE,
        _probe(EngineName.LIBREOFFICE),
        lambda source_path, output_path: _write_pdf(output_path, source_path.name),
    )
    service = DocumentConversionService((engine,), LINUX_DESKTOP)

    result = service.convert(_request(source))

    assert result.success is True
    assert result.selected_engine is EngineName.LIBREOFFICE
    assert result.attempted_engines == (EngineName.LIBREOFFICE,)
    assert result.effective_revision_mode is RevisionMode.FINAL
    assert result.effective_comment_mode is CommentMode.OMIT
    assert result.artifacts[0].status is ArtifactStatus.SUCCESS
    assert result.artifacts[0].path == source.with_suffix(".pdf")
    assert result.artifacts[0].size_bytes == source.with_suffix(".pdf").stat().st_size
    assert result.to_dict()["selected_engine"] == "libreoffice"


def test_odt_source_uses_libreoffice_file_conversion_route(tmp_path: Path) -> None:
    source = _source(tmp_path, "臺灣 文件.odt")

    def render_file(
        source_path: Path,
        output_path: Path,
        artifact_type: ArtifactType,
    ) -> None:
        assert source_path == source
        assert artifact_type is ArtifactType.PDF
        _write_pdf(output_path, source_path.name)

    engine = StubEngine(
        EngineName.LIBREOFFICE,
        _probe(EngineName.LIBREOFFICE),
        lambda source_path, output_path: _write_pdf(output_path),
        file_render=render_file,
    )
    request = ConversionRequest(
        source,
        SourceFormat.ODT,
        (ArtifactType.PDF,),
        ConversionOptions(),
    )

    result = DocumentConversionService((engine,), LINUX_DESKTOP).convert(request)

    assert result.success is True
    assert result.selected_engine is EngineName.LIBREOFFICE
    assert result.artifacts[0].path == source.with_suffix(".pdf")


def test_service_passes_timeout_and_annotation_modes_to_selected_engine(tmp_path: Path) -> None:
    source = _source(tmp_path)
    engine = StubEngine(
        EngineName.LIBREOFFICE,
        _probe(
            EngineName.LIBREOFFICE,
            revisions=(RevisionMode.FINAL, RevisionMode.MARKUP),
            comments=(CommentMode.OMIT, CommentMode.MARKUP),
        ),
        lambda source_path, output_path: _write_pdf(output_path),
    )
    request = _request(
        source,
        timeout_seconds=7,
        revision_mode=RevisionMode.MARKUP,
        comment_mode=CommentMode.MARKUP,
    )

    result = DocumentConversionService((engine,), LINUX_DESKTOP).convert(request)

    assert result.success is True
    assert engine.option_calls == [(7, RevisionMode.MARKUP, CommentMode.MARKUP)]
    assert result.effective_revision_mode is RevisionMode.MARKUP
    assert result.effective_comment_mode is CommentMode.MARKUP


def test_unavailable_preferred_engine_is_reported_before_fallback(tmp_path: Path) -> None:
    source = _source(tmp_path)
    word = StubEngine(
        EngineName.WORD_COM,
        _probe(EngineName.WORD_COM, available=False),
        lambda source_path, output_path: None,
    )
    libreoffice = StubEngine(
        EngineName.LIBREOFFICE,
        _probe(EngineName.LIBREOFFICE),
        lambda source_path, output_path: _write_pdf(output_path),
    )
    service = DocumentConversionService((word, libreoffice), WINDOWS_DESKTOP)

    result = service.convert(_request(source))

    assert result.success is True
    assert result.selected_engine is EngineName.LIBREOFFICE
    assert result.attempted_engines == (EngineName.WORD_COM, EngineName.LIBREOFFICE)
    assert result.fallback_reason == "word-com: not installed"
    assert result.warnings[0].code == "ENGINE_FALLBACK"
    assert word.calls == []


def test_engine_failure_falls_back_and_records_reason(tmp_path: Path) -> None:
    source = _source(tmp_path)

    def fail(source_path: Path, output_path: Path) -> None:
        del source_path, output_path
        raise EngineFailedError("Word export failed", engine="word-com")

    word = StubEngine(EngineName.WORD_COM, _probe(EngineName.WORD_COM), fail)
    libreoffice = StubEngine(
        EngineName.LIBREOFFICE,
        _probe(EngineName.LIBREOFFICE),
        lambda source_path, output_path: _write_pdf(output_path),
    )
    service = DocumentConversionService((word, libreoffice), WINDOWS_DESKTOP)

    result = service.convert(_request(source))

    assert result.success is True
    assert result.attempted_engines == (EngineName.WORD_COM, EngineName.LIBREOFFICE)
    assert result.fallback_reason == "word-com: Word export failed"
    assert result.warnings[0].engine is EngineName.WORD_COM


def test_explicit_engine_failure_never_falls_back(tmp_path: Path) -> None:
    source = _source(tmp_path)

    def fail(source_path: Path, output_path: Path) -> None:
        del source_path, output_path
        raise EngineFailedError("Word export failed", engine="word-com")

    word = StubEngine(EngineName.WORD_COM, _probe(EngineName.WORD_COM), fail)
    libreoffice = StubEngine(
        EngineName.LIBREOFFICE,
        _probe(EngineName.LIBREOFFICE),
        lambda source_path, output_path: _write_pdf(output_path),
    )
    service = DocumentConversionService((word, libreoffice), WINDOWS_DESKTOP)

    result = service.convert(_request(source, engine=EngineName.WORD_COM))

    assert result.success is False
    assert result.error is not None
    assert result.error.code is ErrorCode.ENGINE_FAILED
    assert result.attempted_engines == (EngineName.WORD_COM,)
    assert result.fallback_reason is None
    assert libreoffice.calls == []


def test_strict_unsupported_annotation_mode_returns_capability_error(tmp_path: Path) -> None:
    source = _source(tmp_path)
    word = StubEngine(
        EngineName.WORD_COM,
        _probe(EngineName.WORD_COM),
        lambda source_path, output_path: _write_pdf(output_path),
    )
    service = DocumentConversionService((word,), WINDOWS_DESKTOP)

    result = service.convert(
        _request(
            source,
            deployment_mode=DeploymentMode.STRICT_WORD,
            revision_mode=RevisionMode.MARKUP,
        )
    )

    assert result.success is False
    assert result.error is not None
    assert result.error.code is ErrorCode.UNSUPPORTED_ANNOTATION_MODE
    assert result.attempted_engines == (EngineName.WORD_COM,)
    assert word.calls == []


def test_overwrite_is_rejected_without_running_engine(tmp_path: Path) -> None:
    source = _source(tmp_path)
    output = source.with_suffix(".pdf")
    output.write_bytes(b"preserve")
    engine = StubEngine(
        EngineName.LIBREOFFICE,
        _probe(EngineName.LIBREOFFICE),
        lambda source_path, output_path: _write_pdf(output_path),
    )

    result = DocumentConversionService((engine,), LINUX_DESKTOP).convert(_request(source))

    assert result.success is False
    assert result.error is not None
    assert result.error.code is ErrorCode.OUTPUT_EXISTS
    assert output.read_bytes() == b"preserve"
    assert engine.calls == []


def test_overwrite_replaces_only_after_valid_conversion(tmp_path: Path) -> None:
    source = _source(tmp_path)
    output = source.with_suffix(".pdf")
    output.write_bytes(b"old")
    engine = StubEngine(
        EngineName.LIBREOFFICE,
        _probe(EngineName.LIBREOFFICE),
        lambda source_path, output_path: _write_pdf(output_path, "new"),
    )

    result = DocumentConversionService((engine,), LINUX_DESKTOP).convert(
        _request(source, overwrite=True)
    )

    assert result.success is True
    assert output.read_bytes() != b"old"


def test_failed_overwrite_preserves_existing_output(tmp_path: Path) -> None:
    source = _source(tmp_path)
    output = source.with_suffix(".pdf")
    output.write_bytes(b"old")

    def fail(source_path: Path, output_path: Path) -> None:
        del source_path, output_path
        raise EngineFailedError("conversion failed", engine="libreoffice")

    engine = StubEngine(EngineName.LIBREOFFICE, _probe(EngineName.LIBREOFFICE), fail)

    result = DocumentConversionService((engine,), LINUX_DESKTOP).convert(
        _request(source, overwrite=True, engine=EngineName.LIBREOFFICE)
    )

    assert result.success is False
    assert output.read_bytes() == b"old"


def test_invalid_pdf_falls_back_to_next_capable_engine(tmp_path: Path) -> None:
    source = _source(tmp_path)
    word = StubEngine(
        EngineName.WORD_COM,
        _probe(EngineName.WORD_COM),
        _write_invalid_pdf,
    )
    libreoffice = StubEngine(
        EngineName.LIBREOFFICE,
        _probe(EngineName.LIBREOFFICE),
        lambda source_path, output_path: _write_pdf(output_path),
    )

    result = DocumentConversionService((word, libreoffice), WINDOWS_DESKTOP).convert(
        _request(source)
    )

    assert result.success is True
    assert result.selected_engine is EngineName.LIBREOFFICE
    assert result.attempted_engines == (EngineName.WORD_COM, EngineName.LIBREOFFICE)
    assert "invalid PDF" in (result.fallback_reason or "")


def test_unimplemented_artifact_route_returns_stable_input_failure(tmp_path: Path) -> None:
    source = _source(tmp_path)
    request = ConversionRequest.from_source(source, artifacts=(ArtifactType.MARKDOWN,))

    result = DocumentConversionService((), LINUX_DESKTOP).convert(request)

    assert result.success is False
    assert result.error is not None
    assert result.error.code is ErrorCode.INVALID_INPUT
    assert result.artifacts[0].artifact_type is ArtifactType.MARKDOWN
    assert result.artifacts[0].path is None


def test_batch_failure_does_not_stop_other_items(tmp_path: Path) -> None:
    bad_source = _source(tmp_path, "bad.docx")
    good_source = _source(tmp_path, "good.docx")

    def render(source_path: Path, output_path: Path) -> None:
        if source_path.name == "bad.docx":
            raise EngineFailedError("bad item", engine="libreoffice")
        _write_pdf(output_path)

    engine = StubEngine(EngineName.LIBREOFFICE, _probe(EngineName.LIBREOFFICE), render)
    service = DocumentConversionService((engine,), LINUX_DESKTOP)

    results = service.convert_batch((_request(bad_source), _request(good_source)))

    assert tuple(result.success for result in results) == (False, True)
    assert good_source.with_suffix(".pdf").is_file()


def test_probe_exception_is_returned_as_safe_unavailable_result() -> None:
    engine = StubEngine(
        EngineName.LIBREOFFICE,
        _probe(EngineName.LIBREOFFICE),
        lambda source_path, output_path: None,
        probe_error=RuntimeError("private path"),
    )

    result = DocumentConversionService((engine,), LINUX_DESKTOP).probe_engines(
        (EngineName.LIBREOFFICE, EngineName.GOTENBERG)
    )

    assert result[0].available is False
    assert result[0].reason == "engine probe failed"
    assert result[1].reason == "engine adapter is not configured"


_ODT_BODY = """<text:h text:outline-level="1">總則</text:h>
<text:p>正文內容</text:p>"""


def test_odt_source_produces_semantic_artifacts_without_a_rendering_engine(
    tmp_path: Path, write_odt: Callable[..., Path]
) -> None:
    source = write_odt(tmp_path / "臺灣 文件.odt", _ODT_BODY)
    request = ConversionRequest(
        source,
        SourceFormat.ODT,
        (ArtifactType.MARKDOWN, ArtifactType.JSON, ArtifactType.YAML),
        ConversionOptions(),
    )

    result = DocumentConversionService((), LINUX_DESKTOP).convert(request)

    assert result.success is True
    assert [item.status for item in result.artifacts] == [ArtifactStatus.SUCCESS] * 3
    assert (tmp_path / "臺灣 文件.md").read_text(encoding="utf-8") == "# 總則\n\n正文內容\n"
    assert (tmp_path / "臺灣 文件.json").is_file()
    assert (tmp_path / "臺灣 文件.yaml").is_file()


def test_odt_page_images_render_through_the_libreoffice_file_route(
    tmp_path: Path, write_odt: Callable[..., Path]
) -> None:
    source = write_odt(tmp_path / "頁面.odt", _ODT_BODY)
    engine = StubEngine(
        EngineName.LIBREOFFICE,
        _probe(EngineName.LIBREOFFICE),
        lambda source_path, output_path: _write_pdf(output_path),
        file_render=lambda source_path, output_path, artifact_type: _write_pdf(output_path),
    )
    request = ConversionRequest(
        source,
        SourceFormat.ODT,
        (ArtifactType.PAGE_IMAGES,),
        ConversionOptions(image_dpi=72),
    )

    result = DocumentConversionService((engine,), LINUX_DESKTOP).convert(request)

    assert result.success is True
    artifact = result.artifacts[0]
    assert [item.path.name for item in artifact.items] == ["0001.png"]
    assert (tmp_path / "頁面.pages" / "0001.png").is_file()


def test_odt_mixed_office_and_semantic_artifacts_share_one_output_stem(
    tmp_path: Path, write_odt: Callable[..., Path]
) -> None:
    source = write_odt(tmp_path / "混合.odt", _ODT_BODY)
    engine = StubEngine(
        EngineName.LIBREOFFICE,
        _probe(EngineName.LIBREOFFICE),
        lambda source_path, output_path: _write_pdf(output_path),
        file_render=_write_office_document,
    )
    request = ConversionRequest(
        source,
        SourceFormat.ODT,
        (ArtifactType.DOCX, ArtifactType.MARKDOWN),
        ConversionOptions(output_path=tmp_path / "輸出"),
    )

    result = DocumentConversionService((engine,), LINUX_DESKTOP).convert(request)

    assert result.success is True
    assert [item.artifact_type for item in result.artifacts] == [
        ArtifactType.DOCX,
        ArtifactType.MARKDOWN,
    ]
    assert (tmp_path / "輸出.docx").read_bytes() == b"converted office document"
    assert (tmp_path / "輸出.md").is_file()


def test_odt_office_artifacts_still_fail_cleanly_without_libreoffice(
    tmp_path: Path, write_odt: Callable[..., Path]
) -> None:
    source = write_odt(tmp_path / "缺引擎.odt", _ODT_BODY)
    request = ConversionRequest(
        source,
        SourceFormat.ODT,
        (ArtifactType.DOCX, ArtifactType.MARKDOWN),
        ConversionOptions(),
    )

    result = DocumentConversionService((), LINUX_DESKTOP).convert(request)

    assert result.success is False
    statuses = {item.artifact_type: item.status for item in result.artifacts}
    assert statuses[ArtifactType.DOCX] is ArtifactStatus.FAILED
    assert statuses[ArtifactType.MARKDOWN] is ArtifactStatus.SUCCESS
    assert (tmp_path / "缺引擎.md").is_file()
