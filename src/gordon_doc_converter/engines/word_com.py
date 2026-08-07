"""Microsoft Word COM adapter with isolated, bounded worker execution."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

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
from gordon_doc_converter.models import (
    CommentMode,
    EngineName,
    EngineProbeResult,
    RevisionMode,
)
from gordon_doc_converter.models_types import JsonValue
from gordon_doc_converter.process.runner import (
    ProcessResult,
    ProcessStartError,
    ProcessTimeoutError,
    run_process,
)
from gordon_doc_converter.validation import validate_pdf

_ENGINE = EngineName.WORD_COM
_DEFAULT_PROBE_TIMEOUT_SECONDS = 20.0
_WORKER_MODULE = "gordon_doc_converter.engines._word_worker"
_SUPPORTED_REVISIONS = (RevisionMode.FINAL, RevisionMode.ORIGINAL, RevisionMode.MARKUP)
_SUPPORTED_COMMENTS = (CommentMode.OMIT, CommentMode.MARKUP)


def _worker_payload(result: ProcessResult) -> dict[str, JsonValue] | None:
    try:
        payload = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    return {str(key): value for key, value in payload.items()}


def _publish_pdf(generated_path: Path, output_path: Path) -> None:
    output_created = False
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with (
            generated_path.open("rb") as source_stream,
            output_path.open("xb") as output_stream,
        ):
            output_created = True
            shutil.copyfileobj(source_stream, output_stream)
    except FileExistsError as exc:
        raise OutputExistsError("PDF output already exists") from exc
    except OSError as exc:
        if output_created:
            output_path.unlink(missing_ok=True)
        raise EngineFailedError(
            "Word PDF could not be written to the requested output",
            engine=_ENGINE.value,
        ) from exc


class WordComEngine:
    """Render DOCX files through a dedicated Microsoft Word COM worker on Windows."""

    def __init__(
        self,
        python_executable: Path | None = None,
        *,
        probe_timeout_seconds: float = _DEFAULT_PROBE_TIMEOUT_SECONDS,
    ) -> None:
        if probe_timeout_seconds <= 0:
            raise InvalidInputError("probe_timeout_seconds must be greater than zero")
        self._python_executable = (python_executable or Path(sys.executable)).resolve()
        self._probe_timeout_seconds = probe_timeout_seconds

    @property
    def name(self) -> EngineName:
        """Return Microsoft Word COM's stable public engine name."""
        return _ENGINE

    def _command(self, *arguments: str) -> tuple[str, ...]:
        return (str(self._python_executable), "-m", _WORKER_MODULE, *arguments)

    def probe(self) -> EngineProbeResult:
        """Attempt real COM activation and report supported annotation modes."""
        if sys.platform != "win32":
            return EngineProbeResult(
                engine=self.name,
                available=False,
                reason="Microsoft Word COM is available only on Windows",
            )
        try:
            result = run_process(self._command("--probe"), self._probe_timeout_seconds)
        except ProcessStartError:
            return EngineProbeResult(
                engine=self.name,
                available=False,
                reason="Word COM probe worker could not be started",
            )
        except ProcessTimeoutError:
            return EngineProbeResult(
                engine=self.name,
                available=False,
                reason="Word COM activation timed out",
            )
        payload = _worker_payload(result)
        if result.returncode != 0 or payload is None or payload.get("status") != "ok":
            return EngineProbeResult(
                engine=self.name,
                available=False,
                reason="Microsoft Word COM activation failed",
            )
        version = payload.get("version")
        return EngineProbeResult(
            engine=self.name,
            available=True,
            version=version if isinstance(version, str) else None,
            revision_modes=_SUPPORTED_REVISIONS,
            comment_modes=_SUPPORTED_COMMENTS,
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
        """Render one DOCX through Word and return a validated engine-neutral result."""
        if sys.platform != "win32":
            raise EngineUnavailableError(
                "Microsoft Word COM is available only on Windows",
                engine=self.name.value,
            )
        if timeout_seconds <= 0:
            raise InvalidInputError("timeout_seconds must be greater than zero")
        if source_path.suffix.casefold() != ".docx" or not source_path.is_file():
            raise InvalidInputError("Word source must be an existing DOCX file")
        if output_path.suffix.casefold() != ".pdf":
            raise InvalidInputError("Word output must use the .pdf extension")
        if output_path.exists():
            raise OutputExistsError("PDF output already exists")
        if revision_mode not in _SUPPORTED_REVISIONS or comment_mode not in _SUPPORTED_COMMENTS:
            raise UnsupportedAnnotationModeError(
                "Word cannot honor the requested revision and comment modes",
                engine=self.name.value,
            )

        started = perf_counter()
        with TemporaryDirectory(prefix="gordon-doc-word-") as temporary:
            workspace = Path(temporary)
            generated_path = workspace / "output.pdf"
            request_path = workspace / "request.json"
            request_payload = {
                "source": str(source_path.resolve()),
                "output": str(generated_path),
                "revision_mode": revision_mode.value,
                "comment_mode": comment_mode.value,
            }
            request_path.write_text(
                json.dumps(request_payload, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
                newline="\n",
            )
            try:
                result = run_process(
                    self._command("--request", str(request_path)),
                    timeout_seconds,
                )
            except ProcessStartError as exc:
                raise EngineUnavailableError(
                    "Word COM worker could not be started",
                    engine=self.name.value,
                ) from exc
            except ProcessTimeoutError as exc:
                raise ConversionTimeoutError(
                    "Word conversion exceeded its timeout",
                    engine=self.name.value,
                ) from exc
            payload = _worker_payload(result)
            if result.returncode == 2:
                raise EngineUnavailableError(
                    "Microsoft Word COM is unavailable",
                    engine=self.name.value,
                )
            if result.returncode != 0 or payload is None or payload.get("status") != "ok":
                raise EngineFailedError(
                    "Microsoft Word failed to convert the document",
                    engine=self.name.value,
                )

            validation = validate_pdf(generated_path)
            if not validation.valid:
                if (
                    validation.error is not None
                    and validation.error.code is ErrorCode.PDF_NOT_CREATED
                ):
                    raise PdfNotCreatedError(
                        "Microsoft Word did not create a non-empty PDF",
                        engine=self.name.value,
                    )
                raise PdfValidationError(
                    "Microsoft Word created an invalid PDF",
                    engine=self.name.value,
                )
            _publish_pdf(generated_path, output_path)

        return EngineExecutionResult(
            engine=self.name,
            output_path=output_path,
            duration_seconds=perf_counter() - started,
        )
