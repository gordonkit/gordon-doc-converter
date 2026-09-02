"""Direct wkhtmltopdf adapter for print-ready HTML documents."""

from __future__ import annotations

import shutil
from pathlib import Path

from gordon_doc_converter.exceptions import (
    ConversionTimeoutError,
    EngineFailedError,
    EngineUnavailableError,
)
from gordon_doc_converter.models import ConversionOptions, PageOrientation
from gordon_doc_converter.process import ProcessStartError, ProcessTimeoutError, run_process

_ENGINE = "wkhtmltopdf"
# wkhtmltopdf ignores @page, so the stylesheet's own A4 margins are passed as arguments.
_MARGIN = "20mm"
# Released in 0.12.6; older builds reject it and reach local files without asking.
_LOCAL_FILE_ACCESS = "--enable-local-file-access"
_UNKNOWN_ARGUMENT = "unknown long argument"


class WkhtmltopdfConverter:
    """Render a standalone HTML document to an A4 PDF with its own stylesheet intact.

    Pandoc's HTML reader keeps only the body and document metadata, so routing print
    HTML through it would discard the page setup and fonts the document carries. The
    PDF engine therefore reads the document directly.
    """

    def __init__(self, executable: str | None = None) -> None:
        self._executable = executable or shutil.which(_ENGINE)

    def convert(
        self,
        source_path: Path,
        output_path: Path,
        *,
        options: ConversionOptions,
    ) -> None:
        """Render one HTML document, honouring the requested A4 orientation."""
        if self._executable is None:
            raise EngineUnavailableError("wkhtmltopdf is required for markup PDF conversion")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        orientation = (
            "Landscape" if options.page_orientation is PageOrientation.LANDSCAPE else "Portrait"
        )
        arguments = [
            self._executable,
            "--quiet",
            "--encoding",
            "utf-8",
            "--print-media-type",
            "--page-size",
            "A4",
            "--orientation",
            orientation,
            "--margin-top",
            _MARGIN,
            "--margin-right",
            _MARGIN,
            "--margin-bottom",
            _MARGIN,
            "--margin-left",
            _MARGIN,
            _LOCAL_FILE_ACCESS,
            str(source_path),
            str(output_path),
        ]
        result = self._run(arguments, options.timeout_seconds)
        if result is not None and _UNKNOWN_ARGUMENT in result.casefold():
            # An older build reads neighbouring files without the flag it does not know.
            arguments.remove(_LOCAL_FILE_ACCESS)
            result = self._run(arguments, options.timeout_seconds)
        if result is not None:
            message = "wkhtmltopdf conversion failed"
            detail = result.strip()
            if detail:
                message += f": {detail.splitlines()[-1][:240]}"
            raise EngineFailedError(message, engine=_ENGINE)
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise EngineFailedError(
                "wkhtmltopdf did not create the requested output",
                engine=_ENGINE,
            )

    def _run(self, arguments: list[str], timeout_seconds: float) -> str | None:
        """Run one bounded invocation, returning its error output or None on success."""
        try:
            result = run_process(arguments, timeout_seconds)
        except ProcessStartError as exc:
            raise EngineUnavailableError("wkhtmltopdf could not be started") from exc
        except ProcessTimeoutError as exc:
            raise ConversionTimeoutError(
                "wkhtmltopdf conversion timed out",
                engine=_ENGINE,
            ) from exc
        return None if result.returncode == 0 else result.stderr
