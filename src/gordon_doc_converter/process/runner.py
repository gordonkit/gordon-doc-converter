"""Cross-platform bounded subprocess execution and process-tree cleanup."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProcessResult:
    """Captured result from a completed external process."""

    returncode: int
    stdout: str
    stderr: str


class ProcessStartError(Exception):
    """Raised when the operating system cannot start an external process."""


class ProcessTimeoutError(Exception):
    """Raised after an external process exceeds its deadline and is terminated."""


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    command: tuple[str, ...]
    try:
        if os.name == "nt":
            command = ("taskkill", "/PID", str(process.pid), "/T", "/F")
        else:
            # A negative PID targets the isolated process group created below.
            command = ("kill", "-KILL", f"-{process.pid}")
        subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=10.0,
        )
    except (OSError, subprocess.SubprocessError):
        try:
            process.kill()
        except OSError:
            return


def run_process(arguments: Sequence[str], timeout_seconds: float) -> ProcessResult:
    """Run a command without a shell, capture output, and enforce a process-tree timeout."""
    try:
        process = subprocess.Popen(
            tuple(arguments),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            start_new_session=os.name != "nt",
        )
    except OSError as exc:
        raise ProcessStartError from exc
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        _terminate_process_tree(process)
        try:
            process.communicate(timeout=10.0)
        except subprocess.TimeoutExpired as cleanup_exc:
            process.kill()
            try:
                process.communicate(timeout=10.0)
            except subprocess.TimeoutExpired as final_exc:
                raise ProcessTimeoutError from final_exc
            raise ProcessTimeoutError from cleanup_exc
        raise ProcessTimeoutError from exc
    return ProcessResult(process.returncode, stdout, stderr)
