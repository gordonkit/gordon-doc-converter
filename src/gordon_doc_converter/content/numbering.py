"""Locale-aware ordinal marker parsing for inferred document structure.

Markers are described by system, style, and unit instead of enumerating every
concrete string, so new locales only add data rather than new branches.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_CIRCLED_DIGITS = {
    **{chr(0x2460 + index): index + 1 for index in range(20)},
    **{chr(0x2474 + index): index + 1 for index in range(20)},
    **{chr(0x2488 + index): index + 1 for index in range(20)},
    **{chr(0x3220 + index): index + 1 for index in range(10)},
    **{chr(0x3251 + index): index + 21 for index in range(15)},
}

_PARENTHESIZED_IDEOGRAPHS = {chr(0x3220 + index): index + 1 for index in range(10)}

_CJK_LOWER_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "兩": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
_CJK_LOWER_UNITS = {"十": 10, "百": 100, "千": 1000}

_CJK_FORMAL_DIGITS = {
    "零": 0,
    "壹": 1,
    "貳": 2,
    "贰": 2,
    "參": 3,
    "叁": 3,
    "参": 3,
    "肆": 4,
    "伍": 5,
    "陸": 6,
    "陆": 6,
    "柒": 7,
    "捌": 8,
    "玖": 9,
}
_CJK_FORMAL_UNITS = {"拾": 10, "佰": 100, "仟": 1000}

_HEAVENLY_STEMS = "甲乙丙丁戊己庚辛壬癸"
_EARTHLY_BRANCHES = "子丑寅卯辰巳午未申酉戌亥"

_ROMAN_VALUES = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}

_SECTION_UNITS = (
    "篇",
    "部",
    "編",
    "编",
    "章",
    "節",
    "节",
    "條",
    "条",
    "項",
    "项",
    "款",
    "目",
    "點",
    "点",
)

_OPENING_BRACKETS = "（(〔[【〖"
_CLOSING_BRACKETS = "）)〕]】〗"
_TRAILING_SEPARATORS = "、,.．。:：)）]〕】>》"

_SENTENCE_TERMINATORS = "。！？!?；;"

# Section counters stay small; larger runs are phone numbers, years, or amounts.
_MAX_ORDINAL = 199

_BULLET_SYMBOLS = "※•‧・▪▫■□◆◇▲△★☆→☞–—※＊*·"


def starts_with_bullet(text: str) -> bool:
    """Return whether the line opens with a typographic bullet rather than prose."""
    stripped = text.lstrip()
    return bool(stripped) and stripped[0] in _BULLET_SYMBOLS


_DOT_LEADER = re.compile(r"[.．·。]{4,}|[…]{2,}")


@dataclass(frozen=True, slots=True)
class NumberToken:
    """One parsed ordinal marker found at the start of a line."""

    system: str
    style: str
    ordinal: int
    marker: str
    remainder: str
    unit: str | None = None
    sub_ordinal: int | None = None
    depth: int = 1

    @property
    def numbering_class(self) -> str:
        """Return the stable identity shared by markers of the same level."""
        unit = self.unit or "-"
        return f"{self.system}:{self.style}:{unit}:{self.depth}"


def has_dot_leader(text: str) -> bool:
    """Return whether the text contains a table-of-contents dot leader run."""
    return _DOT_LEADER.search(text) is not None


def ends_with_sentence_terminator(text: str) -> bool:
    """Return whether the text ends with a sentence-final punctuation mark."""
    stripped = text.rstrip()
    return bool(stripped) and stripped[-1] in _SENTENCE_TERMINATORS


def _parse_cjk_numeral(text: str, digits: dict[str, int], units: dict[str, int]) -> int | None:
    total = 0
    section = 0
    seen = False
    for character in text:
        if character in digits:
            section = digits[character]
            seen = True
            continue
        if character in units:
            unit = units[character]
            section = section or 1
            total += section * unit
            section = 0
            seen = True
            continue
        return None
    if not seen:
        return None
    return total + section


def _parse_roman(text: str) -> int | None:
    lowered = text.lower()
    if not lowered or any(character not in _ROMAN_VALUES for character in lowered):
        return None
    total = 0
    previous = 0
    for character in reversed(lowered):
        value = _ROMAN_VALUES[character]
        total += -value if value < previous else value
        previous = max(previous, value)
    return total or None


def _numeral_body(text: str) -> tuple[str, int, str] | None:
    """Return system, ordinal, and consumed text for a leading numeral run."""
    if not text:
        return None
    if text[0] in _CIRCLED_DIGITS:
        return "circled", _CIRCLED_DIGITS[text[0]], text[0]

    digits = ""
    for character in text:
        if unicodedata.category(character) == "Nd":
            digits += unicodedata.normalize("NFKC", character)
            continue
        break
    if digits:
        return "arabic", int(digits), text[: len(digits)]

    cjk = ""
    for character in text:
        if character in _CJK_LOWER_DIGITS or character in _CJK_LOWER_UNITS:
            cjk += character
            continue
        break
    if cjk:
        value = _parse_cjk_numeral(cjk, _CJK_LOWER_DIGITS, _CJK_LOWER_UNITS)
        if value is not None:
            return "cjk-lower", value, cjk
    formal = ""
    for character in text:
        if character in _CJK_FORMAL_DIGITS or character in _CJK_FORMAL_UNITS:
            formal += character
            continue
        break
    if formal:
        value = _parse_cjk_numeral(formal, _CJK_FORMAL_DIGITS, _CJK_FORMAL_UNITS)
        if value is not None:
            return "cjk-formal", value, formal

    if text[0] in _HEAVENLY_STEMS:
        return "stem", _HEAVENLY_STEMS.index(text[0]) + 1, text[0]
    if text[0] in _EARTHLY_BRANCHES:
        return "branch", _EARTHLY_BRANCHES.index(text[0]) + 1, text[0]

    roman = ""
    for character in text:
        if character.lower() in _ROMAN_VALUES:
            roman += character
            continue
        break
    if len(roman) > 1 or (roman and text[len(roman) :][:1] in {".", ")", "、"}):
        value = _parse_roman(roman)
        if value is not None:
            return "roman", value, roman
    if text[0].isalpha() and text[0].isascii():
        return "latin", ord(text[0].lower()) - 96, text[0]
    return None


def _sub_ordinal(text: str) -> tuple[int | None, str]:
    """Consume a Taiwanese inserted-article suffix such as `之一`."""
    if not text.startswith("之"):
        return None, text
    parsed = _numeral_body(text[1:])
    if parsed is None:
        return None, text
    _, ordinal, consumed = parsed
    return ordinal, text[1 + len(consumed) :]


def parse_marker(text: str) -> NumberToken | None:
    """Parse a leading ordinal marker and return its structured description."""
    stripped = text.strip()
    if not stripped:
        return None

    if stripped[0] in _PARENTHESIZED_IDEOGRAPHS:
        ordinal = _PARENTHESIZED_IDEOGRAPHS[stripped[0]]
        return NumberToken(
            "cjk-lower", "full-paren", ordinal, stripped[0], stripped[1:].strip(), depth=1
        )

    cursor = 0
    unit: str | None = None
    style = "bare"

    if stripped.startswith("第"):
        cursor = 1
    elif stripped[:2] in {"附錄", "附件", "附表", "附圖"}:
        unit = stripped[:2]
        cursor = 2

    opening = ""
    if cursor < len(stripped) and stripped[cursor] in _OPENING_BRACKETS:
        opening = stripped[cursor]
        style = "full-paren" if opening == "（" else "paren"
        cursor += 1

    parsed = _numeral_body(stripped[cursor:])
    if parsed is None:
        return None
    system, ordinal, consumed = parsed
    cursor += len(consumed)

    sub_ordinal, remainder_after_sub = _sub_ordinal(stripped[cursor:])
    cursor = len(stripped) - len(remainder_after_sub)

    depth = 1
    if system == "arabic":
        while cursor < len(stripped) and stripped[cursor] in ".．":
            nested = _numeral_body(stripped[cursor + 1 :])
            if nested is None or nested[0] != "arabic":
                break
            depth += 1
            ordinal = nested[1]
            cursor += 1 + len(nested[2])

    if opening:
        if cursor >= len(stripped) or stripped[cursor] not in _CLOSING_BRACKETS:
            return None
        cursor += 1
    elif cursor < len(stripped) and stripped[cursor] in _CLOSING_BRACKETS:
        style = "half-paren"
        cursor += 1
    elif stripped[cursor : cursor + 1] in _SECTION_UNITS:
        unit = stripped[cursor]
        cursor += 1
        sub_ordinal, remainder_after_unit = _sub_ordinal(stripped[cursor:])
        cursor = len(stripped) - len(remainder_after_unit)
    elif cursor < len(stripped) and stripped[cursor] in "、.．":
        style = "ideographic-comma" if stripped[cursor] == "、" else "dot"
        cursor += 1
    elif unit is None and system != "circled" and depth == 1 and not opening:
        return None

    marker = stripped[:cursor]
    if ordinal > _MAX_ORDINAL or (sub_ordinal is not None and sub_ordinal > _MAX_ORDINAL):
        return None
    remainder = stripped[cursor:].lstrip(_TRAILING_SEPARATORS + " \t　")
    return NumberToken(
        system,
        style,
        ordinal,
        marker,
        remainder,
        unit=unit,
        sub_ordinal=sub_ordinal,
        depth=depth,
    )
