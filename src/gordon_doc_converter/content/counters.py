"""Shared ordinal marker rendering for source-specific list and outline numbering."""

from __future__ import annotations

from enum import StrEnum

_CJK_PLAIN_DIGITS = "零一二三四五六七八九"
_CJK_PLAIN_UNITS = ("", "十", "百", "千")
_CJK_FINANCIAL_DIGITS = "零壹貳參肆伍陸柒捌玖"
_CJK_FINANCIAL_UNITS = ("", "拾", "佰", "仟")
_HEAVENLY_STEMS = "甲乙丙丁戊己庚辛壬癸"
_EARTHLY_BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
_ROMAN_TOKENS = (
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
)


class OrdinalSystem(StrEnum):
    """Engine-neutral numbering systems shared by OOXML and ODF list definitions."""

    DECIMAL = "decimal"
    LOWER_LETTER = "lower-letter"
    UPPER_LETTER = "upper-letter"
    LOWER_ROMAN = "lower-roman"
    UPPER_ROMAN = "upper-roman"
    CJK_DECIMAL = "cjk-decimal"
    CJK_FINANCIAL = "cjk-financial"
    HEAVENLY_STEM = "heavenly-stem"
    EARTHLY_BRANCH = "earthly-branch"


def cjk_number(value: int, *, financial: bool = False) -> str:
    """Render a positive integer below 10000 with Traditional Chinese numerals."""
    digits = _CJK_FINANCIAL_DIGITS if financial else _CJK_PLAIN_DIGITS
    units = _CJK_FINANCIAL_UNITS if financial else _CJK_PLAIN_UNITS
    if value <= 0 or value >= 10000:
        return str(value)
    result = ""
    pending_zero = False
    for position in range(3, -1, -1):
        divisor = 10**position
        digit, value = divmod(value, divisor)
        if digit:
            if pending_zero and result:
                result += digits[0]
            if not (digit == 1 and position == 1 and not result and not financial):
                result += digits[digit]
            result += units[position]
            pending_zero = False
        elif result and value:
            pending_zero = True
    return result


def _roman(value: int) -> str:
    if value <= 0:
        return str(value)
    parts: list[str] = []
    remainder = value
    for amount, token in _ROMAN_TOKENS:
        while remainder >= amount:
            parts.append(token)
            remainder -= amount
    return "".join(parts)


def _cycled(value: int, alphabet: str) -> str:
    return alphabet[(value - 1) % len(alphabet)] if value > 0 else str(value)


def format_ordinal(value: int, system: OrdinalSystem) -> str:
    """Render one counter value in the requested numbering system."""
    if system is OrdinalSystem.LOWER_LETTER:
        return _cycled(value, "abcdefghijklmnopqrstuvwxyz")
    if system is OrdinalSystem.UPPER_LETTER:
        return _cycled(value, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    if system is OrdinalSystem.LOWER_ROMAN:
        return _roman(value).lower()
    if system is OrdinalSystem.UPPER_ROMAN:
        return _roman(value)
    if system is OrdinalSystem.CJK_DECIMAL:
        return cjk_number(value)
    if system is OrdinalSystem.CJK_FINANCIAL:
        return cjk_number(value, financial=True)
    if system is OrdinalSystem.HEAVENLY_STEM:
        return _cycled(value, _HEAVENLY_STEMS)
    if system is OrdinalSystem.EARTHLY_BRANCH:
        return _cycled(value, _EARTHLY_BRANCHES)
    return str(value)
