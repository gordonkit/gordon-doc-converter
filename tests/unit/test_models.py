"""Tests for public request and result contracts."""

from pathlib import Path
from typing import Any, cast

import pytest

from gordon_doc_converter.exceptions import ErrorCode, InvalidInputError
from gordon_doc_converter.models import (
    AnnotationAnchor,
    AnnotationKind,
    ArtifactResult,
    ArtifactStatus,
    ArtifactType,
    CommentMode,
    ConversionFailure,
    ConversionOptions,
    ConversionRequest,
    ConversionResult,
    EngineName,
    NormalizedAnnotation,
    RevisionMode,
    SourceFormat,
)


def test_docx_request_defaults_to_pdf() -> None:
    request = ConversionRequest.from_source(Path("臺灣 文件.docx"))

    assert request.source_format is SourceFormat.DOCX
    assert request.artifacts == (ArtifactType.PDF,)


def test_odt_request_defaults_to_pdf() -> None:
    request = ConversionRequest.from_source(Path("臺灣 文件.odt"))

    assert request.source_format is SourceFormat.ODT
    assert request.artifacts == (ArtifactType.PDF,)


def test_pdf_request_requires_explicit_target() -> None:
    with pytest.raises(InvalidInputError, match="explicit artifact"):
        ConversionRequest.from_source(Path("input.pdf"))


@pytest.mark.parametrize("source", [Path("input.txt"), Path("input"), Path("input.doc")])
def test_request_rejects_unknown_source_format(source: Path) -> None:
    with pytest.raises(InvalidInputError, match=".docx, .odt, .pdf"):
        ConversionRequest.from_source(source)


def test_request_rejects_duplicate_artifacts() -> None:
    with pytest.raises(InvalidInputError, match="duplicates"):
        ConversionRequest(
            Path("input.docx"),
            SourceFormat.DOCX,
            (ArtifactType.PDF, ArtifactType.PDF),
        )


def test_options_reject_invalid_timeout_and_word_container_profile() -> None:
    with pytest.raises(InvalidInputError, match="greater than zero"):
        ConversionOptions(timeout_seconds=0)
    with pytest.raises(InvalidInputError, match="container_engine"):
        ConversionOptions(container_engine=EngineName.WORD_COM)


def test_result_serializes_to_stable_json_primitives() -> None:
    failure = ConversionFailure(ErrorCode.ENGINE_FAILED, "conversion failed", EngineName.WORD_COM)
    result = ConversionResult(
        success=False,
        source_format=SourceFormat.DOCX,
        artifacts=(
            ArtifactResult(
                artifact_type=ArtifactType.PDF,
                status=ArtifactStatus.FAILED,
                path=Path("out.pdf"),
                error=failure,
            ),
        ),
        attempted_engines=(EngineName.WORD_COM,),
        error=failure,
        requested_revision_mode=RevisionMode.MARKUP,
        requested_comment_mode=CommentMode.OMIT,
        annotations=(
            NormalizedAnnotation(
                "revision-0001",
                AnnotationKind.INSERTION,
                0,
                AnnotationAnchor(4, 8),
            ),
        ),
    )

    payload = cast("dict[str, Any]", result.to_dict())

    assert payload["source_format"] == "docx"
    assert payload["attempted_engines"] == ["word-com"]
    assert payload["artifacts"][0]["path"] == "out.pdf"
    assert payload["artifacts"][0]["error"]["code"] == "ENGINE_FAILED"
    assert payload["requested_revision_mode"] == "markup"
    assert payload["annotations"][0]["anchor"] == {"start": 4, "end": 8, "exact": True}


def test_annotation_anchor_rejects_invalid_ranges() -> None:
    with pytest.raises(InvalidInputError, match="precede"):
        AnnotationAnchor(8, 4)
