"""Unit tests for bounded subprocess execution."""

from __future__ import annotations

import pytest

import gordon_doc_converter.process.runner as runner_module
from gordon_doc_converter.process.runner import ProcessTimeoutError, run_process


def test_process_timeout_terminates_tree_and_preserves_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeout_type = runner_module.subprocess.TimeoutExpired

    class FakeProcess:
        returncode = 0
        calls = 0

        def communicate(self, timeout: float) -> tuple[str, str]:
            self.calls += 1
            if self.calls == 1:
                raise timeout_type(("soffice",), timeout)
            return ("partial output", "")

    process = FakeProcess()
    terminated: list[object] = []
    monkeypatch.setattr(runner_module.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(
        runner_module,
        "_terminate_process_tree",
        lambda running_process: terminated.append(running_process),
    )

    with pytest.raises(ProcessTimeoutError) as raised:
        run_process(("soffice", "--version"), 1)

    assert isinstance(raised.value.__cause__, timeout_type)
    assert terminated == [process]
    assert process.calls == 2
