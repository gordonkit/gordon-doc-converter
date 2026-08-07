"""Isolated Microsoft Word COM worker invoked by the Word engine adapter."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

_EXIT_SUCCESS = 0
_EXIT_UNAVAILABLE = 2
_EXIT_FAILED = 3


def _load_com_modules() -> tuple[Any, Any]:
    """Load Windows-only COM modules without affecting cross-platform imports."""
    pythoncom = importlib.import_module("pythoncom")
    win32_client = importlib.import_module("win32com.client")
    return pythoncom, win32_client


def _configure_application(application: Any) -> None:
    application.Visible = False
    application.DisplayAlerts = 0
    application.ScreenUpdating = False
    application.AutomationSecurity = 3


def _configure_document(document: Any, revision_mode: str, comment_mode: str) -> None:
    view = document.ActiveWindow.View
    view.RevisionsView = 1 if revision_mode == "original" else 0
    revision_markup = revision_mode == "markup"
    comment_markup = comment_mode == "markup"
    show_markup = revision_markup or comment_markup
    view.ShowRevisionsAndComments = show_markup
    view.ShowInsertionsAndDeletions = revision_markup
    view.ShowFormatChanges = revision_markup
    view.ShowComments = comment_markup
    document.PrintRevisions = show_markup


def _close_document(document: Any) -> bool:
    try:
        document.Close(SaveChanges=0)
    except Exception:
        return False
    return True


def _quit_application(application: Any) -> bool:
    try:
        application.Quit(SaveChanges=0)
    except Exception:
        return False
    return True


def _uninitialize_com(pythoncom: Any) -> bool:
    try:
        pythoncom.CoUninitialize()
    except Exception:
        return False
    return True


def _probe_word() -> tuple[int, dict[str, str]]:
    pythoncom: Any | None = None
    application: Any | None = None
    initialized = False
    status = _EXIT_SUCCESS
    payload = {"status": "ok"}
    try:
        pythoncom_module, win32_client = _load_com_modules()
        pythoncom = pythoncom_module
        pythoncom_module.CoInitialize()
        initialized = True
        word_application = win32_client.DispatchEx("Word.Application")
        application = word_application
        _configure_application(word_application)
        payload["version"] = str(word_application.Version)
    except (ImportError, ModuleNotFoundError):
        status = _EXIT_UNAVAILABLE
        payload = {"status": "unavailable"}
    except Exception:
        status = _EXIT_UNAVAILABLE
        payload = {"status": "unavailable"}
    finally:
        if application is not None and not _quit_application(application):
            status = _EXIT_FAILED
            payload = {"status": "cleanup-failed"}
        if initialized and pythoncom is not None and not _uninitialize_com(pythoncom):
            status = _EXIT_FAILED
            payload = {"status": "cleanup-failed"}
    return status, payload


def _read_request(request_path: Path) -> tuple[Path, Path, str, str]:
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("worker request must be an object")
    source = payload.get("source")
    output = payload.get("output")
    revision_mode = payload.get("revision_mode")
    comment_mode = payload.get("comment_mode")
    if (
        not isinstance(source, str)
        or not isinstance(output, str)
        or not isinstance(revision_mode, str)
        or not isinstance(comment_mode, str)
    ):
        raise ValueError("worker request fields must be strings")
    if revision_mode not in {"final", "original", "markup"}:
        raise ValueError("unsupported revision mode")
    if comment_mode not in {"omit", "markup"}:
        raise ValueError("unsupported comment mode")
    return Path(source), Path(output), revision_mode, comment_mode


def _convert_word(request_path: Path) -> tuple[int, dict[str, str]]:
    pythoncom: Any | None = None
    application: Any | None = None
    document: Any | None = None
    initialized = False
    status = _EXIT_SUCCESS
    payload = {"status": "ok"}
    try:
        source, output, revision_mode, comment_mode = _read_request(request_path)
        pythoncom_module, win32_client = _load_com_modules()
        pythoncom = pythoncom_module
        pythoncom_module.CoInitialize()
        initialized = True
        word_application = win32_client.DispatchEx("Word.Application")
        application = word_application
        _configure_application(word_application)
        word_document = word_application.Documents.Open(
            FileName=str(source),
            ConfirmConversions=False,
            ReadOnly=True,
            AddToRecentFiles=False,
            Visible=False,
            OpenAndRepair=False,
            NoEncodingDialog=True,
        )
        document = word_document
        _configure_document(word_document, revision_mode, comment_mode)
        word_document.ExportAsFixedFormat(
            OutputFileName=str(output),
            ExportFormat=17,
            OpenAfterExport=False,
            OptimizeFor=0,
            Range=0,
            Item=0,
            IncludeDocProps=True,
            KeepIRM=False,
            CreateBookmarks=1,
            DocStructureTags=True,
            BitmapMissingFonts=True,
            UseISO19005_1=False,
        )
    except (ImportError, ModuleNotFoundError):
        status = _EXIT_UNAVAILABLE
        payload = {"status": "unavailable"}
    except Exception:
        status = _EXIT_FAILED
        payload = {"status": "failed"}
    finally:
        if document is not None and not _close_document(document):
            status = _EXIT_FAILED
            payload = {"status": "cleanup-failed"}
        if application is not None and not _quit_application(application):
            status = _EXIT_FAILED
            payload = {"status": "cleanup-failed"}
        if initialized and pythoncom is not None and not _uninitialize_com(pythoncom):
            status = _EXIT_FAILED
            payload = {"status": "cleanup-failed"}
    return status, payload


def main(arguments: list[str] | None = None) -> int:
    """Run a probe or conversion request and emit a path-safe JSON status."""
    arguments = sys.argv[1:] if arguments is None else arguments
    if arguments == ["--probe"]:
        status, payload = _probe_word()
    elif len(arguments) == 2 and arguments[0] == "--request":
        status, payload = _convert_word(Path(arguments[1]))
    else:
        status, payload = _EXIT_FAILED, {"status": "invalid-request"}
    sys.stdout.write(json.dumps(payload, ensure_ascii=True, sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
