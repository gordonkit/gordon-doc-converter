"""Mock COM tests for the isolated Microsoft Word worker."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pypdf import PdfWriter

import gordon_doc_converter.engines._word_worker as worker


class FakePythonCom:
    """Record COM apartment initialization and cleanup."""

    def __init__(self) -> None:
        self.initialized = 0
        self.uninitialized = 0

    def CoInitialize(self) -> None:
        self.initialized += 1

    def CoUninitialize(self) -> None:
        self.uninitialized += 1


class FakeView:
    """Mutable Word view properties configured by the worker."""

    RevisionsView = 0
    ShowRevisionsAndComments = False
    ShowInsertionsAndDeletions = False
    ShowFormatChanges = False
    ShowComments = False


class FakeWindow:
    """Expose a typed view from a fake Word document window."""

    def __init__(self) -> None:
        self.View = FakeView()


class FakeDocument:
    """Record export and cleanup behavior for a fake Word document."""

    def __init__(self, *, export_fails: bool = False) -> None:
        self.ActiveWindow = FakeWindow()
        self.PrintRevisions = False
        self.export_fails = export_fails
        self.export_arguments: dict[str, object] = {}
        self.close_arguments: dict[str, object] = {}

    def ExportAsFixedFormat(self, **arguments: object) -> None:
        self.export_arguments = arguments
        if self.export_fails:
            raise RuntimeError("simulated private COM failure")
        output = Path(str(arguments["OutputFileName"]))
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        with output.open("wb") as stream:
            writer.write(stream)

    def Close(self, **arguments: object) -> None:
        self.close_arguments = arguments


class FakeDocuments:
    """Return a configured fake document from Word's Documents collection."""

    def __init__(self, document: FakeDocument) -> None:
        self.document = document
        self.open_arguments: dict[str, object] = {}

    def Open(self, **arguments: object) -> FakeDocument:
        self.open_arguments = arguments
        return self.document


class FakeApplication:
    """Represent the dedicated hidden Word instance."""

    Version = "16.0"

    def __init__(self, document: FakeDocument) -> None:
        self.Documents = FakeDocuments(document)
        self.Visible = True
        self.DisplayAlerts = -1
        self.ScreenUpdating = True
        self.AutomationSecurity = 0
        self.quit_arguments: dict[str, object] = {}

    def Quit(self, **arguments: object) -> None:
        self.quit_arguments = arguments


class FakeClient:
    """Return one dedicated fake Word application."""

    def __init__(self, application: FakeApplication) -> None:
        self.application = application
        self.prog_id: str | None = None

    def DispatchEx(self, prog_id: str) -> FakeApplication:
        self.prog_id = prog_id
        return self.application


def _request(
    tmp_path: Path,
    *,
    revision_mode: str = "markup",
    comment_mode: str = "omit",
) -> tuple[Path, Path, Path]:
    source = tmp_path / "來源 文件.docx"
    output = tmp_path / "輸出 文件.pdf"
    request = tmp_path / "request.json"
    source.write_bytes(b"generated")
    request.write_text(
        json.dumps(
            {
                "source": str(source),
                "output": str(output),
                "revision_mode": revision_mode,
                "comment_mode": comment_mode,
            }
        ),
        encoding="utf-8",
    )
    return request, source, output


def test_probe_activates_dedicated_word_and_always_quits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pythoncom = FakePythonCom()
    document = FakeDocument()
    application = FakeApplication(document)
    client = FakeClient(application)
    monkeypatch.setattr(worker, "_load_com_modules", lambda: (pythoncom, client))

    status, payload = worker._probe_word()

    assert status == 0
    assert payload == {"status": "ok", "version": "16.0"}
    assert client.prog_id == "Word.Application"
    assert application.Visible is False
    assert application.DisplayAlerts == 0
    assert application.ScreenUpdating is False
    assert application.AutomationSecurity == 3
    assert application.quit_arguments == {"SaveChanges": 0}
    assert pythoncom.initialized == pythoncom.uninitialized == 1


@pytest.mark.parametrize(
    ("revision_mode", "comment_mode", "expected"),
    [
        ("final", "omit", (0, False, False, False, False)),
        ("original", "markup", (1, True, False, False, True)),
        ("markup", "omit", (0, True, True, True, False)),
    ],
)
def test_conversion_applies_explicit_modes_and_cleans_com_objects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    revision_mode: str,
    comment_mode: str,
    expected: tuple[int, bool, bool, bool, bool],
) -> None:
    request, source, output = _request(
        tmp_path,
        revision_mode=revision_mode,
        comment_mode=comment_mode,
    )
    pythoncom = FakePythonCom()
    document = FakeDocument()
    application = FakeApplication(document)
    client = FakeClient(application)
    monkeypatch.setattr(worker, "_load_com_modules", lambda: (pythoncom, client))

    status, payload = worker._convert_word(request)

    assert status == 0
    assert payload == {"status": "ok"}
    assert output.is_file()
    assert application.Documents.open_arguments["FileName"] == str(source)
    assert application.Documents.open_arguments["ReadOnly"] is True
    assert application.Documents.open_arguments["Visible"] is False
    view = document.ActiveWindow.View
    actual = (
        view.RevisionsView,
        document.PrintRevisions,
        view.ShowInsertionsAndDeletions,
        view.ShowFormatChanges,
        view.ShowComments,
    )
    assert actual == expected
    assert document.close_arguments == {"SaveChanges": 0}
    assert application.quit_arguments == {"SaveChanges": 0}
    assert pythoncom.initialized == pythoncom.uninitialized == 1


def test_conversion_failure_still_closes_document_and_application(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, _, output = _request(tmp_path)
    pythoncom = FakePythonCom()
    document = FakeDocument(export_fails=True)
    application = FakeApplication(document)
    monkeypatch.setattr(
        worker,
        "_load_com_modules",
        lambda: (pythoncom, FakeClient(application)),
    )

    status, payload = worker._convert_word(request)

    assert status == 3
    assert payload == {"status": "failed"}
    assert not output.exists()
    assert document.close_arguments == {"SaveChanges": 0}
    assert application.quit_arguments == {"SaveChanges": 0}
    assert pythoncom.initialized == pythoncom.uninitialized == 1
