"""Regression coverage for semantic and page-image service routes."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from pypdf import PdfWriter

from gordon_doc_converter.environment import EnvironmentInfo
from gordon_doc_converter.exceptions import ErrorCode
from gordon_doc_converter.models import (
    ArtifactStatus,
    ArtifactType,
    ConversionOptions,
    ConversionRequest,
)
from gordon_doc_converter.progress import ProgressEvent
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


HTML_SOURCE = """<!doctype html>
<html lang="zh-TW">
<head><meta charset="utf-8"><title>季度報告</title></head>
<body>
<h1>季度報告</h1>
<p>本季營收成長 12%。</p>
<ul><li>市場拓展</li><li>成本控制</li></ul>
<table><tr><th>區域</th><th>營收</th></tr><tr><td>亞太</td><td>1200</td></tr></table>
</body>
</html>
"""


def _html(path: Path) -> Path:
    path.write_text(HTML_SOURCE, encoding="utf-8")
    return path


def test_html_source_writes_markdown_yaml_and_json_from_one_extraction(
    tmp_path: Path,
) -> None:
    request = ConversionRequest.from_source(
        _html(tmp_path / "報告.html"),
        artifacts=(ArtifactType.MARKDOWN, ArtifactType.YAML, ArtifactType.JSON),
        options=ConversionOptions(output_path=tmp_path / "語意輸出"),
    )

    result = DocumentConversionService((), EnvironmentInfo("linux", False)).convert(request)

    assert result.success is True
    assert [item.artifact_type for item in result.artifacts] == [
        ArtifactType.MARKDOWN,
        ArtifactType.YAML,
        ArtifactType.JSON,
    ]
    assert all(item.status is ArtifactStatus.SUCCESS for item in result.artifacts)
    markdown = (tmp_path / "語意輸出.md").read_text(encoding="utf-8")
    assert "# 季度報告" in markdown
    assert "- 市場拓展" in markdown
    assert "| 區域 | 營收 |" in markdown
    payload = json.loads((tmp_path / "語意輸出.json").read_text(encoding="utf-8"))
    assert payload["source"]["format"] == "html"
    assert payload["sections"][0]["title"] == "季度報告"
    document = yaml.safe_load((tmp_path / "語意輸出.yaml").read_text(encoding="utf-8"))
    assert document["source"]["format"] == "html"
    assert document["sections"][0]["title"] == "季度報告"


def test_html_semantic_conversion_reports_extraction_progress_phases(tmp_path: Path) -> None:
    request = ConversionRequest.from_source(
        _html(tmp_path / "source.html"),
        artifacts=(ArtifactType.MARKDOWN,),
        options=ConversionOptions(output_path=tmp_path / "out.md"),
    )
    events: list[ProgressEvent] = []

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


def test_html_source_rejects_artifacts_outside_the_supported_set(tmp_path: Path) -> None:
    request = ConversionRequest.from_source(
        _html(tmp_path / "source.html"),
        artifacts=(ArtifactType.HTML,),
    )

    result = DocumentConversionService((), EnvironmentInfo("linux", False)).convert(request)

    assert result.success is False
    assert result.error is not None
    assert result.error.code is ErrorCode.INVALID_INPUT
    assert "Markdown, YAML, and JSON" in result.error.message


def test_markdown_source_produces_semantic_artifacts_without_a_rendering_engine(
    tmp_path: Path,
) -> None:
    source = tmp_path / "note.md"
    source.write_text("# 標題\n", encoding="utf-8")
    request = ConversionRequest.from_source(source, artifacts=(ArtifactType.JSON,))

    result = DocumentConversionService((), EnvironmentInfo("linux", False)).convert(request)

    assert result.success is True
    assert (tmp_path / "note.json").is_file()


def test_markdown_source_rejects_artifacts_outside_the_supported_set(tmp_path: Path) -> None:
    source = tmp_path / "note.md"
    source.write_text("# 標題\n", encoding="utf-8")
    request = ConversionRequest.from_source(source, artifacts=(ArtifactType.MARKDOWN,))

    result = DocumentConversionService((), EnvironmentInfo("linux", False)).convert(request)

    assert result.success is False
    assert result.error is not None
    assert result.error.code is ErrorCode.INVALID_INPUT
    assert result.error.message == (
        "Markdown sources support only PDF, DOCX, HTML, YAML, and JSON outputs"
    )


def test_html_semantic_outputs_are_not_overwritten_without_permission(tmp_path: Path) -> None:
    source = _html(tmp_path / "source.html")
    existing = tmp_path / "out.md"
    existing.write_text("keep me", encoding="utf-8")
    request = ConversionRequest.from_source(
        source,
        artifacts=(ArtifactType.MARKDOWN,),
        options=ConversionOptions(output_path=existing),
    )

    result = DocumentConversionService((), EnvironmentInfo("linux", False)).convert(request)

    assert result.success is False
    assert result.error is not None
    assert result.error.code is ErrorCode.OUTPUT_EXISTS
    assert existing.read_text(encoding="utf-8") == "keep me"


def _jsonl_request(source: Path, output_stem: Path) -> ConversionRequest:
    return ConversionRequest.from_source(
        source,
        artifacts=(ArtifactType.JSON,),
        options=ConversionOptions(output_path=output_stem, json_lines=True),
    )


def test_json_lines_writes_one_record_per_line_for_every_semantic_source(
    tmp_path: Path,
) -> None:
    pdf_source = tmp_path / "source.pdf"
    _pdf(pdf_source, pages=1)
    sources = {
        "docx": DOCX_FIXTURE,
        "pdf": pdf_source,
        "html": _html(tmp_path / "source.html"),
    }
    service = DocumentConversionService((), EnvironmentInfo("linux", False))

    for name, source in sources.items():
        result = service.convert(_jsonl_request(source, tmp_path / name))

        assert result.success is True, name
        artifact = result.artifacts[0]
        assert artifact.path == tmp_path / f"{name}.jsonl"
        assert not (tmp_path / f"{name}.json").exists()
        assert artifact.items[0].media_type == "application/jsonl; charset=utf-8"
        lines = (tmp_path / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in lines]
        assert records[0]["type"] == "document"
        assert records[0]["source"]["format"] == name
        assert {record["type"] for record in records} <= {
            "document",
            "block",
            "asset",
            "annotation",
            "warning",
        }


def test_json_lines_leaves_the_default_json_artifact_unchanged(tmp_path: Path) -> None:
    source = _html(tmp_path / "source.html")
    service = DocumentConversionService((), EnvironmentInfo("linux", False))

    nested = service.convert(
        ConversionRequest.from_source(
            source,
            artifacts=(ArtifactType.JSON,),
            options=ConversionOptions(output_path=tmp_path / "nested"),
        )
    )

    assert nested.success is True
    assert nested.artifacts[0].path == tmp_path / "nested.json"
    assert nested.artifacts[0].items[0].media_type == "application/json; charset=utf-8"
    document = json.loads((tmp_path / "nested.json").read_text(encoding="utf-8"))
    assert set(document) >= {"schema_version", "source", "sections", "root_blocks"}


def test_json_lines_applies_only_to_the_json_artifact_in_a_shared_extraction(
    tmp_path: Path,
) -> None:
    request = ConversionRequest.from_source(
        _html(tmp_path / "source.html"),
        artifacts=(ArtifactType.MARKDOWN, ArtifactType.YAML, ArtifactType.JSON),
        options=ConversionOptions(output_path=tmp_path / "bundle", json_lines=True),
    )

    result = DocumentConversionService((), EnvironmentInfo("linux", False)).convert(request)

    assert result.success is True
    assert [item.path for item in result.artifacts] == [
        tmp_path / "bundle.md",
        tmp_path / "bundle.yaml",
        tmp_path / "bundle.jsonl",
    ]
    assert (
        yaml.safe_load((tmp_path / "bundle.yaml").read_text(encoding="utf-8"))["source"]["format"]
        == "html"
    )


def test_json_lines_output_path_with_a_jsonl_suffix_is_used_as_the_stem(
    tmp_path: Path,
) -> None:
    request = ConversionRequest.from_source(
        _html(tmp_path / "source.html"),
        artifacts=(ArtifactType.JSON,),
        options=ConversionOptions(output_path=tmp_path / "報告.jsonl", json_lines=True),
    )

    result = DocumentConversionService((), EnvironmentInfo("linux", False)).convert(request)

    assert result.success is True
    assert result.artifacts[0].path == tmp_path / "報告.jsonl"
