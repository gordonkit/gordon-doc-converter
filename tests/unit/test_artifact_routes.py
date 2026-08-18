"""Regression coverage for semantic and page-image service routes."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter

from gordon_doc_converter.environment import EnvironmentInfo
from gordon_doc_converter.models import (
    ArtifactStatus,
    ArtifactType,
    ConversionOptions,
    ConversionRequest,
)
from gordon_doc_converter.service import DocumentConversionService

DOCX_FIXTURE = Path("tests/fixtures/docx/cjk/a4-portrait.docx")


def _pdf(path: Path, pages: int = 2) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=144)
    with path.open("wb") as stream:
        writer.write(stream)


def test_docx_semantic_formats_share_deterministic_assets(tmp_path: Path) -> None:
    request = ConversionRequest.from_source(
        DOCX_FIXTURE,
        artifacts=(
            ArtifactType.MARKDOWN,
            ArtifactType.HTML,
            ArtifactType.YAML,
            ArtifactType.JSON,
        ),
        options=ConversionOptions(output_path=tmp_path / "繁中輸出"),
    )

    result = DocumentConversionService((), EnvironmentInfo("linux", False)).convert(request)

    assert result.success is True
    assert [item.status for item in result.artifacts] == [
        ArtifactStatus.SUCCESS,
        ArtifactStatus.SUCCESS,
        ArtifactStatus.SUCCESS,
        ArtifactStatus.SUCCESS,
    ]
    assert (tmp_path / "繁中輸出.md").is_file()
    assert (tmp_path / "繁中輸出.html").is_file()
    assert (tmp_path / "繁中輸出.yaml").is_file()
    assert (tmp_path / "繁中輸出.json").is_file()
    assert "GordonKit" in (tmp_path / "繁中輸出.md").read_text(encoding="utf-8")


def test_pdf_page_images_use_one_based_zero_padded_names_and_metadata(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.pdf"
    _pdf(source)
    output = tmp_path / "source.pages"
    request = ConversionRequest.from_source(
        source,
        artifacts=(ArtifactType.PAGE_IMAGES,),
        options=ConversionOptions(output_path=output, image_dpi=72),
    )

    result = DocumentConversionService((), EnvironmentInfo("linux", False)).convert(request)

    assert result.success is True
    artifact = result.artifacts[0]
    assert [item.path.name for item in artifact.items] == ["0001.png", "0002.png"]
    assert [(item.width_pixels, item.height_pixels) for item in artifact.items] == [
        (72, 144),
        (72, 144),
    ]
    assert all(item.sha256 is not None and len(item.sha256) == 64 for item in artifact.items)
    assert all(item.path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") for item in artifact.items)


def test_multiple_artifacts_treat_output_as_a_shared_stem(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    _pdf(source, pages=1)
    request = ConversionRequest.from_source(
        source,
        artifacts=(ArtifactType.MARKDOWN, ArtifactType.PAGE_IMAGES),
        options=ConversionOptions(output_path=tmp_path / "bundle", image_dpi=72),
    )

    result = DocumentConversionService((), EnvironmentInfo("linux", False)).convert(request)

    assert result.success is True
    assert (tmp_path / "bundle.md").is_file()
    assert (tmp_path / "bundle.pages" / "0001.png").is_file()


def test_semantic_conversion_reports_observable_progress_phases(tmp_path: Path) -> None:
    request = ConversionRequest.from_source(
        DOCX_FIXTURE,
        artifacts=(ArtifactType.JSON,),
        options=ConversionOptions(output_path=tmp_path / "progress.json"),
    )
    events = []

    result = DocumentConversionService((), EnvironmentInfo("linux", False)).convert(
        request,
        progress_callback=events.append,
    )

    assert result.success is True
    assert [event.phase for event in events] == [
        "validation",
        "content-extraction",
        "serialization",
        "conversion",
    ]
    assert events[-1].state.value == "completed"
