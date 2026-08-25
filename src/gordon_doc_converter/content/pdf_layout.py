"""Coordinate-aware text line reconstruction from PDF content streams."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

_BOLD_HINTS = ("bold", "black", "heavy", "semib", "demib")
_LINE_TOLERANCE = 2.0
_CJK_RANGES = (
    (0x3000, 0x303F),
    (0x3040, 0x30FF),
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0xFF00, 0xFFEF),
    (0x20000, 0x2FA1F),
)


def _is_cjk(character: str) -> bool:
    code = ord(character)
    return any(start <= code <= end for start, end in _CJK_RANGES)


def collapse_cjk_spaces(text: str) -> str:
    """Drop spacing that glyph positioning inserts between adjacent CJK characters."""
    kept: list[str] = []
    for index, character in enumerate(text):
        if (
            character == " "
            and kept
            and index + 1 < len(text)
            and _is_cjk(kept[-1])
            and _is_cjk(text[index + 1])
        ):
            continue
        kept.append(character)
    return "".join(kept)


def join_wrapped(previous: str, following: str) -> str:
    """Rejoin a wrapped line, keeping the space only where Latin text needs one."""
    if not previous:
        return following
    if not following:
        return previous
    left, right = previous[-1], following[0]
    if left == "-" or _is_cjk(left) or _is_cjk(right):
        return previous + following
    return f"{previous} {following}"


@dataclass(frozen=True, slots=True)
class TextFragment:
    """One positioned text run reported by the pypdf text visitor."""

    text: str
    x: float
    y: float
    size: float
    font: str


@dataclass(frozen=True, slots=True)
class TextLine:
    """One reconstructed visual line with its dominant typographic traits."""

    text: str
    page_number: int
    x: float
    y: float
    size: float
    bold: bool

    @property
    def is_blank(self) -> bool:
        """Return whether the line carries no visible characters."""
        return not self.text.strip()


def _is_bold(font: str) -> bool:
    lowered = font.casefold()
    return any(hint in lowered for hint in _BOLD_HINTS)


def collect_fragments(page: Any) -> tuple[list[TextFragment], str]:
    """Extract positioned fragments and the plain text fallback for one page."""
    fragments: list[TextFragment] = []
    state = {"x": 0.0, "y": 0.0}

    def visitor(text: str, _cm: Sequence[float], tm: Sequence[float], font: Any, size: Any) -> None:
        if not text or not text.strip():
            return
        try:
            x = float(tm[4])
            y = float(tm[5])
            font_size = float(size)
        except (IndexError, TypeError, ValueError):
            return
        # Some operators report an unset matrix; reuse the last known baseline.
        if x == 0.0 and y == 0.0:
            x, y = state["x"], state["y"]
        else:
            state["x"], state["y"] = x, y
        base_font = ""
        if isinstance(font, dict):
            base_font = str(font.get("/BaseFont", ""))
        fragments.append(TextFragment(text, x, y, font_size, base_font))

    text = page.extract_text(visitor_text=visitor) or ""
    return fragments, text


def build_lines(fragments: Sequence[TextFragment], page_number: int) -> list[TextLine]:
    """Group fragments sharing a baseline into ordered top-to-bottom lines."""
    groups: list[list[TextFragment]] = []
    for fragment in sorted(fragments, key=lambda item: (-item.y, item.x)):
        if groups and abs(groups[-1][0].y - fragment.y) <= _LINE_TOLERANCE:
            groups[-1].append(fragment)
            continue
        groups.append([fragment])

    lines: list[TextLine] = []
    for group in groups:
        ordered = sorted(group, key=lambda item: item.x)
        text = "".join(item.text for item in ordered)
        if not text.strip():
            continue
        weights: dict[float, int] = {}
        bold_weight = 0
        total_weight = 0
        for item in ordered:
            length = max(len(item.text.strip()), 1)
            weights[round(item.size, 1)] = weights.get(round(item.size, 1), 0) + length
            total_weight += length
            if _is_bold(item.font):
                bold_weight += length
        size = max(weights.items(), key=lambda entry: (entry[1], entry[0]))[0]
        lines.append(
            TextLine(
                text=collapse_cjk_spaces(" ".join(text.split())),
                page_number=page_number,
                x=ordered[0].x,
                y=ordered[0].y,
                size=size,
                bold=total_weight > 0 and bold_weight * 2 >= total_weight,
            )
        )
    return lines
