"""Tests for every v0.1 engine-selection policy branch."""

import pytest

from gordon_doc_converter.environment import EnvironmentInfo
from gordon_doc_converter.exceptions import (
    EngineUnavailableError,
    InvalidInputError,
    UnsupportedAnnotationModeError,
)
from gordon_doc_converter.models import (
    CommentMode,
    ConversionOptions,
    DeploymentMode,
    EngineName,
    EngineProbeResult,
    RevisionMode,
)
from gordon_doc_converter.policies import engine_order, select_engines

WINDOWS_DESKTOP = EnvironmentInfo("win32", True)
LINUX_DESKTOP = EnvironmentInfo("linux", True)


@pytest.mark.parametrize(
    ("options", "environment", "expected"),
    [
        (
            ConversionOptions(),
            WINDOWS_DESKTOP,
            (EngineName.WORD_COM, EngineName.LIBREOFFICE, EngineName.GOTENBERG),
        ),
        (
            ConversionOptions(),
            LINUX_DESKTOP,
            (EngineName.LIBREOFFICE, EngineName.GOTENBERG),
        ),
        (
            ConversionOptions(deployment_mode=DeploymentMode.SERVER),
            WINDOWS_DESKTOP,
            (EngineName.GOTENBERG, EngineName.LIBREOFFICE),
        ),
        (
            ConversionOptions(deployment_mode=DeploymentMode.CONTAINER),
            WINDOWS_DESKTOP,
            (EngineName.LIBREOFFICE, EngineName.GOTENBERG),
        ),
        (
            ConversionOptions(
                deployment_mode=DeploymentMode.CONTAINER,
                container_engine=EngineName.GOTENBERG,
            ),
            WINDOWS_DESKTOP,
            (EngineName.GOTENBERG, EngineName.LIBREOFFICE),
        ),
        (
            ConversionOptions(deployment_mode=DeploymentMode.STRICT_WORD),
            LINUX_DESKTOP,
            (EngineName.WORD_COM,),
        ),
        (
            ConversionOptions(deployment_mode=DeploymentMode.STRICT_LIBREOFFICE),
            WINDOWS_DESKTOP,
            (EngineName.LIBREOFFICE,),
        ),
        (
            ConversionOptions(engine=EngineName.GOTENBERG),
            WINDOWS_DESKTOP,
            (EngineName.GOTENBERG,),
        ),
    ],
)
def test_engine_order(
    options: ConversionOptions,
    environment: EnvironmentInfo,
    expected: tuple[EngineName, ...],
) -> None:
    assert engine_order(options, environment) == expected


def test_container_rejects_explicit_word() -> None:
    options = ConversionOptions(
        deployment_mode=DeploymentMode.CONTAINER,
        engine=EngineName.WORD_COM,
    )
    with pytest.raises(InvalidInputError, match="container"):
        engine_order(options, WINDOWS_DESKTOP)


def _probe(
    engine: EngineName,
    *,
    available: bool = True,
    revisions: tuple[RevisionMode, ...] = (RevisionMode.FINAL,),
    comments: tuple[CommentMode, ...] = (CommentMode.OMIT,),
) -> EngineProbeResult:
    return EngineProbeResult(
        engine=engine,
        available=available,
        reason=None if available else "not installed",
        revision_modes=revisions,
        comment_modes=comments,
    )


def test_auto_selection_filters_unavailable_and_retains_fallbacks() -> None:
    selection = select_engines(
        ConversionOptions(),
        WINDOWS_DESKTOP,
        (
            _probe(EngineName.WORD_COM, available=False),
            _probe(EngineName.LIBREOFFICE),
            _probe(EngineName.GOTENBERG),
        ),
    )

    assert selection.engines == (EngineName.LIBREOFFICE, EngineName.GOTENBERG)
    assert selection.allow_fallback is True
    assert selection.rejected[0].engine is EngineName.WORD_COM


def test_explicit_engine_never_enables_fallback() -> None:
    selection = select_engines(
        ConversionOptions(engine=EngineName.LIBREOFFICE),
        WINDOWS_DESKTOP,
        (_probe(EngineName.LIBREOFFICE), _probe(EngineName.GOTENBERG)),
    )

    assert selection.engines == (EngineName.LIBREOFFICE,)
    assert selection.allow_fallback is False


def test_strict_unavailable_engine_has_stable_error() -> None:
    with pytest.raises(EngineUnavailableError) as raised:
        select_engines(
            ConversionOptions(deployment_mode=DeploymentMode.STRICT_WORD),
            WINDOWS_DESKTOP,
            (_probe(EngineName.WORD_COM, available=False),),
        )

    assert raised.value.engine == "word-com"


def test_strict_unsupported_annotation_mode_has_stable_error() -> None:
    with pytest.raises(UnsupportedAnnotationModeError) as raised:
        select_engines(
            ConversionOptions(
                engine=EngineName.LIBREOFFICE,
                revision_mode=RevisionMode.MARKUP,
            ),
            WINDOWS_DESKTOP,
            (_probe(EngineName.LIBREOFFICE),),
        )

    assert raised.value.code.value == "UNSUPPORTED_ANNOTATION_MODE"


def test_auto_mode_skips_incapable_engine() -> None:
    options = ConversionOptions(revision_mode=RevisionMode.MARKUP)
    selection = select_engines(
        options,
        WINDOWS_DESKTOP,
        (
            _probe(EngineName.WORD_COM),
            _probe(
                EngineName.LIBREOFFICE,
                revisions=(RevisionMode.FINAL, RevisionMode.MARKUP),
            ),
        ),
    )

    assert selection.engines == (EngineName.LIBREOFFICE,)
    assert selection.rejected[0].engine is EngineName.WORD_COM


def test_no_auto_engine_available_has_stable_error() -> None:
    with pytest.raises(EngineUnavailableError, match="no capable"):
        select_engines(ConversionOptions(), LINUX_DESKTOP, ())
