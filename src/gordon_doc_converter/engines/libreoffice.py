"""LibreOffice DOCX-to-PDF adapter with isolated process execution."""

from __future__ import annotations

import os
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
    ArtifactType,
    CommentMode,
    EngineName,
    EngineProbeResult,
    RevisionMode,
    SourceFormat,
)
from gordon_doc_converter.process.runner import (
    ProcessStartError,
    ProcessTimeoutError,
    run_process,
)
from gordon_doc_converter.security import validate_source_document
from gordon_doc_converter.validation import validate_pdf

_ENGINE = EngineName.LIBREOFFICE
_DEFAULT_PROBE_TIMEOUT_SECONDS = 10.0
_EXECUTABLE_NAMES = ("soffice", "libreoffice")
_SOURCE_SUFFIXES = {
    SourceFormat.DOCX: frozenset({".docx"}),
    SourceFormat.ODT: frozenset({".odt"}),
    SourceFormat.HTML: frozenset({".html", ".htm"}),
}
# Without an explicit filter pair, LibreOffice loads HTML into Writer/Web and saves a web
# document, which carries neither page setup nor Writer paragraph styles.
_HTML_IMPORT_FILTER = "HTML (StarWriter)"
_HTML_EXPORT_FILTERS = {
    ArtifactType.PDF: "pdf:writer_pdf_Export",
    ArtifactType.DOCX: "docx:MS Word 2007 XML",
    ArtifactType.ODT: "odt:writer8",
}


def _import_arguments(source_format: SourceFormat) -> tuple[str, ...]:
    """Return the input-filter arguments one source format needs, if any."""
    if source_format is SourceFormat.HTML:
        return (f"--infilter={_HTML_IMPORT_FILTER}",)
    return ()


def _convert_to(source_format: SourceFormat, artifact_type: ArtifactType) -> str:
    """Return the --convert-to value, naming the output filter where the default is wrong."""
    if source_format is SourceFormat.HTML:
        return _HTML_EXPORT_FILTERS[artifact_type]
    return artifact_type.value


def _find_executable() -> Path | None:
    for name in _EXECUTABLE_NAMES:
        discovered = shutil.which(name)
        if discovered is not None:
            return Path(discovered).resolve()
    candidates: list[Path] = []
    if sys.platform == "win32":
        for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
            program_files = os.environ.get(variable)
            if program_files:
                program_path = Path(program_files) / "LibreOffice" / "program"
                candidates.extend((program_path / "soffice.com", program_path / "soffice.exe"))
    elif sys.platform == "darwin":
        candidates.append(Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def _parse_version(output: str) -> str | None:
    first_line = output.strip().splitlines()
    if not first_line:
        return None
    version = first_line[0].strip()
    return version or None


class LibreOfficeEngine:
    """Render DOCX files through a local headless LibreOffice executable.

    The adapter uses a fresh user profile and output workspace for every conversion.
    It supports LibreOffice's deterministic final-document rendering only; tracked
    revision and comment markup modes are deliberately not advertised.
    """

    def __init__(
        self,
        executable: Path | None = None,
        *,
        probe_timeout_seconds: float = _DEFAULT_PROBE_TIMEOUT_SECONDS,
    ) -> None:
        if probe_timeout_seconds <= 0:
            raise InvalidInputError("probe_timeout_seconds must be greater than zero")
        self._configured_executable = executable
        self._probe_timeout_seconds = probe_timeout_seconds

    @property
    def name(self) -> EngineName:
        """Return LibreOffice's stable public engine name."""
        return _ENGINE

    def _executable(self) -> Path | None:
        if self._configured_executable is not None:
            return self._configured_executable.resolve()
        return _find_executable()

    def probe(self) -> EngineProbeResult:
        """Probe the executable and report conservative annotation capabilities."""
        executable = self._executable()
        if executable is None:
            return EngineProbeResult(
                engine=self.name,
                available=False,
                reason="LibreOffice executable was not found",
            )
        try:
            result = run_process(
                (str(executable), "--headless", "--version"),
                self._probe_timeout_seconds,
            )
        except ProcessTimeoutError:
            return EngineProbeResult(
                engine=self.name,
                available=False,
                executable=executable,
                reason="LibreOffice version probe timed out",
            )
        except ProcessStartError:
            return EngineProbeResult(
                engine=self.name,
                available=False,
                executable=executable,
                reason="LibreOffice could not be started",
            )
        if result.returncode != 0:
            return EngineProbeResult(
                engine=self.name,
                available=False,
                executable=executable,
                reason=f"LibreOffice version probe exited with code {result.returncode}",
            )
        return EngineProbeResult(
            engine=self.name,
            available=True,
            version=_parse_version(result.stdout or result.stderr),
            executable=executable,
            revision_modes=(RevisionMode.FINAL,),
            comment_modes=(CommentMode.OMIT,),
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
        """Render one DOCX into a validated PDF or raise a stable project error."""
        if timeout_seconds <= 0:
            raise InvalidInputError("timeout_seconds must be greater than zero")
        if source_path.suffix.casefold() != ".docx" or not source_path.is_file():
            raise InvalidInputError("LibreOffice source must be an existing DOCX file")
        if output_path.suffix.casefold() != ".pdf":
            raise InvalidInputError("LibreOffice output must use the .pdf extension")
        if output_path.exists():
            raise OutputExistsError("PDF output already exists")
        if revision_mode is not RevisionMode.FINAL or comment_mode is not CommentMode.OMIT:
            raise UnsupportedAnnotationModeError(
                "LibreOffice cannot honor the requested revision and comment modes",
                engine=self.name.value,
            )
        executable = self._executable()
        if executable is None:
            raise EngineUnavailableError(
                "LibreOffice executable was not found",
                engine=self.name.value,
            )

        started = perf_counter()
        with TemporaryDirectory(prefix="gordon-doc-libreoffice-") as temporary:
            workspace = Path(temporary)
            profile_path = workspace / "profile"
            generated_path = workspace / "output" / f"{source_path.stem}.pdf"
            profile_path.mkdir()
            generated_path.parent.mkdir()
            arguments = (
                str(executable),
                "--headless",
                "--nologo",
                "--nodefault",
                "--nofirststartwizard",
                "--nolockcheck",
                f"-env:UserInstallation={profile_path.as_uri()}",
                "--convert-to",
                "pdf",
                "--outdir",
                str(generated_path.parent),
                str(source_path.resolve()),
            )
            try:
                result = run_process(arguments, timeout_seconds)
            except ProcessStartError as exc:
                raise EngineUnavailableError(
                    "LibreOffice could not be started",
                    engine=self.name.value,
                ) from exc
            except ProcessTimeoutError as exc:
                raise ConversionTimeoutError(
                    "LibreOffice conversion exceeded its timeout",
                    engine=self.name.value,
                ) from exc
            if result.returncode != 0:
                raise EngineFailedError(
                    f"LibreOffice conversion exited with code {result.returncode}",
                    engine=self.name.value,
                )

            validation = validate_pdf(generated_path)
            if not validation.valid:
                if (
                    validation.error is not None
                    and validation.error.code is ErrorCode.PDF_NOT_CREATED
                ):
                    raise PdfNotCreatedError(
                        "LibreOffice did not create a non-empty PDF",
                        engine=self.name.value,
                    )
                raise PdfValidationError(
                    "LibreOffice created an invalid PDF",
                    engine=self.name.value,
                )
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
                    "LibreOffice PDF could not be written to the requested output",
                    engine=self.name.value,
                ) from exc

        return EngineExecutionResult(
            engine=self.name,
            output_path=output_path,
            duration_seconds=perf_counter() - started,
        )

    def convert_file(
        self,
        source_path: Path,
        output_path: Path,
        *,
        source_format: SourceFormat,
        artifact_type: ArtifactType,
        timeout_seconds: float,
    ) -> EngineExecutionResult:
        """Convert a DOCX, ODT, or HTML source to a PDF, DOCX, or ODT file."""
        supported_sources = {SourceFormat.DOCX, SourceFormat.ODT, SourceFormat.HTML}
        supported_artifacts = {ArtifactType.PDF, ArtifactType.DOCX, ArtifactType.ODT}
        if source_format not in supported_sources:
            raise InvalidInputError(
                "LibreOffice file conversion requires a DOCX, ODT, or HTML source"
            )
        if artifact_type not in supported_artifacts:
            raise InvalidInputError("LibreOffice file conversion supports PDF, DOCX, and ODT")
        if timeout_seconds <= 0:
            raise InvalidInputError("timeout_seconds must be greater than zero")
        if source_path.suffix.casefold() not in _SOURCE_SUFFIXES[source_format] or (
            not source_path.is_file()
        ):
            raise InvalidInputError("LibreOffice source format does not match an existing file")
        expected_suffix = ".pdf" if artifact_type is ArtifactType.PDF else f".{artifact_type.value}"
        if output_path.suffix.casefold() != expected_suffix:
            raise InvalidInputError(f"LibreOffice output must use the {expected_suffix} extension")
        if output_path.exists():
            raise OutputExistsError("conversion output already exists")
        executable = self._executable()
        if executable is None:
            raise EngineUnavailableError(
                "LibreOffice executable was not found",
                engine=self.name.value,
            )

        started = perf_counter()
        with TemporaryDirectory(prefix="gordon-doc-libreoffice-") as temporary:
            workspace = Path(temporary)
            profile_path = workspace / "profile"
            generated_path = workspace / "output" / f"{source_path.stem}{expected_suffix}"
            profile_path.mkdir()
            generated_path.parent.mkdir()
            arguments = (
                str(executable),
                "--headless",
                "--nologo",
                "--nodefault",
                "--nofirststartwizard",
                "--nolockcheck",
                f"-env:UserInstallation={profile_path.as_uri()}",
                *_import_arguments(source_format),
                "--convert-to",
                _convert_to(source_format, artifact_type),
                "--outdir",
                str(generated_path.parent),
                str(source_path.resolve()),
            )
            try:
                result = run_process(arguments, timeout_seconds)
            except ProcessStartError as exc:
                raise EngineUnavailableError(
                    "LibreOffice could not be started",
                    engine=self.name.value,
                ) from exc
            except ProcessTimeoutError as exc:
                raise ConversionTimeoutError(
                    "LibreOffice conversion exceeded its timeout",
                    engine=self.name.value,
                ) from exc
            if result.returncode != 0:
                raise EngineFailedError(
                    f"LibreOffice conversion exited with code {result.returncode}",
                    engine=self.name.value,
                )

            if artifact_type is ArtifactType.PDF:
                validation = validate_pdf(generated_path)
                if not validation.valid:
                    if (
                        validation.error is not None
                        and validation.error.code is ErrorCode.PDF_NOT_CREATED
                    ):
                        raise PdfNotCreatedError(
                            "LibreOffice did not create a non-empty PDF",
                            engine=self.name.value,
                        )
                    raise PdfValidationError(
                        "LibreOffice created an invalid PDF",
                        engine=self.name.value,
                    )
            else:
                validate_source_document(generated_path, SourceFormat(artifact_type.value))
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with (
                    generated_path.open("rb") as source_stream,
                    output_path.open("xb") as output_stream,
                ):
                    shutil.copyfileobj(source_stream, output_stream)
            except FileExistsError as exc:
                raise OutputExistsError("conversion output already exists") from exc
            except OSError as exc:
                output_path.unlink(missing_ok=True)
                raise EngineFailedError(
                    "LibreOffice output could not be written to the requested path",
                    engine=self.name.value,
                ) from exc

        return EngineExecutionResult(
            engine=self.name,
            output_path=output_path,
            duration_seconds=perf_counter() - started,
        )
