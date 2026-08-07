"""Bounded subprocess execution shared by external engine adapters."""

from gordon_doc_converter.process.runner import (
    ProcessResult,
    ProcessStartError,
    ProcessTimeoutError,
    run_process,
)

__all__ = ["ProcessResult", "ProcessStartError", "ProcessTimeoutError", "run_process"]
