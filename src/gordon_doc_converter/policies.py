"""Engine selection and annotation-capability policy."""

from __future__ import annotations

from dataclasses import dataclass

from gordon_doc_converter.environment import EnvironmentInfo
from gordon_doc_converter.exceptions import (
    EngineUnavailableError,
    ErrorCode,
    InvalidInputError,
    UnsupportedAnnotationModeError,
)
from gordon_doc_converter.models import (
    ConversionOptions,
    DeploymentMode,
    EngineName,
    EngineProbeResult,
    JsonModel,
)


@dataclass(frozen=True, slots=True)
class EngineRejection(JsonModel):
    """Reason a candidate was excluded from an engine selection plan."""

    engine: EngineName
    code: ErrorCode
    reason: str


@dataclass(frozen=True, slots=True)
class EngineSelection(JsonModel):
    """Ordered capable engines plus disclosed candidate rejections."""

    engines: tuple[EngineName, ...]
    rejected: tuple[EngineRejection, ...]
    allow_fallback: bool


def engine_order(
    options: ConversionOptions, environment: EnvironmentInfo
) -> tuple[EngineName, ...]:
    """Return the policy order before availability and capability probing."""
    if options.engine is not None:
        if (
            options.deployment_mode is DeploymentMode.CONTAINER
            and options.engine is EngineName.WORD_COM
        ):
            raise InvalidInputError("word-com cannot run in container mode")
        return (options.engine,)
    if options.deployment_mode is DeploymentMode.STRICT_WORD:
        return (EngineName.WORD_COM,)
    if options.deployment_mode is DeploymentMode.STRICT_LIBREOFFICE:
        return (EngineName.LIBREOFFICE,)
    if options.deployment_mode is DeploymentMode.SERVER:
        return (EngineName.GOTENBERG, EngineName.LIBREOFFICE)
    if options.deployment_mode is DeploymentMode.CONTAINER:
        alternative = (
            EngineName.GOTENBERG
            if options.container_engine is EngineName.LIBREOFFICE
            else EngineName.LIBREOFFICE
        )
        return (options.container_engine, alternative)
    if environment.is_windows and environment.interactive:
        return (EngineName.WORD_COM, EngineName.LIBREOFFICE, EngineName.GOTENBERG)
    return (EngineName.LIBREOFFICE, EngineName.GOTENBERG)


def select_engines(
    options: ConversionOptions,
    environment: EnvironmentInfo,
    probes: tuple[EngineProbeResult, ...],
) -> EngineSelection:
    """Filter the policy order by probe availability and annotation capabilities."""
    order = engine_order(options, environment)
    probes_by_name = {probe.engine: probe for probe in probes}
    selected: list[EngineName] = []
    rejected: list[EngineRejection] = []
    strict = options.engine is not None or options.deployment_mode in {
        DeploymentMode.STRICT_WORD,
        DeploymentMode.STRICT_LIBREOFFICE,
    }
    for name in order:
        probe = probes_by_name.get(name)
        if probe is None or not probe.available:
            reason = probe.reason if probe is not None else "engine was not probed"
            rejected.append(
                EngineRejection(name, ErrorCode.ENGINE_UNAVAILABLE, reason or "unavailable")
            )
            continue
        if not probe.supports(options.revision_mode, options.comment_mode):
            rejected.append(
                EngineRejection(
                    name,
                    ErrorCode.UNSUPPORTED_ANNOTATION_MODE,
                    "engine cannot honor the requested revision and comment modes",
                )
            )
            continue
        selected.append(name)
    if not selected:
        first = rejected[0] if rejected else None
        if strict and first is not None and first.code is ErrorCode.UNSUPPORTED_ANNOTATION_MODE:
            raise UnsupportedAnnotationModeError(first.reason, engine=first.engine.value)
        engine = order[0].value if strict and order else None
        raise EngineUnavailableError("no capable conversion engine is available", engine=engine)
    return EngineSelection(tuple(selected), tuple(rejected), allow_fallback=not strict)
