"""Operating-system and interactive-session detection."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EnvironmentInfo:
    """Platform facts used by policy without invoking an engine."""

    platform: str
    interactive: bool

    @property
    def is_windows(self) -> bool:
        """Return whether the detected operating system is Windows."""
        return self.platform == "win32"


def detect_environment() -> EnvironmentInfo:
    """Detect the current platform and whether it has an interactive user session."""
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if sys.platform == "win32":
        interactive = interactive and os.environ.get("SESSIONNAME", "").casefold() != "services"
    return EnvironmentInfo(platform=sys.platform, interactive=interactive)
