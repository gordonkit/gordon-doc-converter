"""Unit tests for locale-aware ordinal marker parsing."""

from __future__ import annotations

import pytest

from gordon_doc_converter.content.numbering import (
    ends_with_sentence_terminator,
    has_dot_leader,
    parse_marker,
)


@pytest.mark.parametrize(
    ("text", "system", "style", "ordinal"),
    [
        ("壹、 基金概況", "cjk-formal", "ideographic-comma", 1),
        ("一、 基金簡介", "cjk-lower", "ideographic-comma", 1),
        ("二十一、 受益人名簿", "cjk-lower", "ideographic-comma", 21),
        ("（一）投資方針", "cjk-lower", "full-paren", 1),
        ("(1) 不得為放款", "arabic", "paren", 1),
        ("1. 本基金之成立條件", "arabic", "dot", 1),
        ("１．全形數字", "arabic", "dot", 1),
        ("①第一點", "circled", "bare", 1),
        ("A. Latin item", "latin", "dot", 1),
        ("IV. Roman item", "roman", "dot", 4),
        ("甲、 天干項目", "stem", "ideographic-comma", 1),
    ],
)
def test_marker_systems_are_parsed_without_enumerating_full_strings(
    text: str, system: str, style: str, ordinal: int
) -> None:
    token = parse_marker(text)

    assert token is not None
    assert (token.system, token.style, token.ordinal) == (system, style, ordinal)


def test_section_unit_and_inserted_article_suffix_are_preserved() -> None:
    token = parse_marker("第十四條之一 規定")

    assert token is not None
    assert token.unit == "條"
    assert token.ordinal == 14
    assert token.sub_ordinal == 1
    assert token.remainder == "規定"


def test_multi_level_arabic_marker_reports_its_depth() -> None:
    token = parse_marker("1.2.3 說明")

    assert token is not None
    assert token.depth == 3
    assert token.remainder == "說明"


def test_same_level_markers_share_one_numbering_class() -> None:
    first = parse_marker("一、 基金簡介")
    second = parse_marker("二、 基金性質")
    other = parse_marker("（一）投資方針")

    assert first is not None
    assert second is not None
    assert other is not None
    assert first.numbering_class == second.numbering_class
    assert first.numbering_class != other.numbering_class


@pytest.mark.parametrize(
    "text",
    [
        "本基金不受存款保險、保險安定基金之保障。",
        "一致性說明",
        "十分重要的說明",
        "Chapter without marker",
        "7288、財團法人金融消費評議中心電話： 0800-789-885",
        "0800-789-885，網址 https://www.foi.org.tw/",
    ],
)
def test_prose_beginning_with_numeral_characters_is_not_a_marker(text: str) -> None:
    assert parse_marker(text) is None


def test_table_of_contents_and_sentence_signals_are_detected() -> None:
    assert has_dot_leader("一、 基金簡介 ......... 1")
    assert not has_dot_leader("一、 基金簡介")
    assert ends_with_sentence_terminator("投資人應詳閱公開說明書。")
    assert not ends_with_sentence_terminator("壹、 基金概況")
