"""Unit tests for heuristic PDF block and heading inference."""

from __future__ import annotations

import itertools

from gordon_doc_converter.content.models import BlockKind
from gordon_doc_converter.content.pdf_layout import TextFragment, TextLine, build_lines
from gordon_doc_converter.content.pdf_structure import infer_blocks


def _line(
    text: str, *, page: int = 1, y: float = 700.0, size: float = 10.0, bold: bool = False
) -> TextLine:
    return TextLine(text=text, page_number=page, x=50.0, y=y, size=size, bold=bold)


def test_fragments_sharing_a_baseline_are_merged_into_one_ordered_line() -> None:
    fragments = [
        TextFragment("界", 120.0, 700.0, 10.0, "/AAA+Regular"),
        TextFragment("世", 100.0, 700.0, 10.0, "/AAA+Regular"),
        TextFragment("下一行", 100.0, 680.0, 10.0, "/AAA+Bold"),
    ]

    lines = build_lines(fragments, 1)

    assert [line.text for line in lines] == ["世界", "下一行"]
    assert lines[0].bold is False
    assert lines[1].bold is True


def test_glyph_spacing_between_adjacent_cjk_characters_is_removed() -> None:
    fragments = [
        TextFragment("財團法人金融消 費評議中心電話：", 100.0, 700.0, 10.0, "/AAA+Regular"),
        TextFragment("第 1~2 頁 Annual Report", 100.0, 680.0, 10.0, "/AAA+Regular"),
    ]

    lines = build_lines(fragments, 1)

    assert lines[0].text == "財團法人金融消費評議中心電話："
    assert lines[1].text == "第 1~2 頁 Annual Report"


def test_numbered_markers_drive_heading_levels_instead_of_font_size_alone() -> None:
    lines = [
        _line("封面標題", y=760.0, size=18.0, bold=True),
        _line("壹、 基金概況", y=720.0, size=16.0, bold=True),
        _line("一、 基金簡介", y=700.0, size=11.0, bold=True),
        _line("（一）投資方針", y=680.0, size=11.0, bold=True),
        _line("本基金主要投資於中華民國境內之上市上櫃股票。", y=660.0),
        _line("二、 基金性質", y=640.0, size=11.0, bold=True),
    ]

    blocks = infer_blocks(lines, page_count=1)
    headings = [(block.text, block.level) for block in blocks if block.kind is BlockKind.HEADING]

    assert ("封面標題", 1) in headings
    assert ("壹、 基金概況", 2) in headings
    assert ("一、 基金簡介", 3) in headings
    assert ("二、 基金性質", 3) in headings
    assert ("（一）投資方針", 4) in headings


def test_table_of_contents_dot_leaders_are_not_promoted_to_headings() -> None:
    lines = [
        _line("目 錄", y=760.0, size=16.0, bold=True),
        _line("壹、 基金概況 .................................. 1", y=720.0, size=11.0, bold=True),
        _line("一、 基金簡介 .................................. 1", y=700.0, size=11.0, bold=True),
    ]

    blocks = infer_blocks(lines, page_count=1)

    assert [block.kind for block in blocks] == [
        BlockKind.HEADING,
        BlockKind.PARAGRAPH,
        BlockKind.PARAGRAPH,
    ]


def test_wrapped_body_lines_are_merged_until_a_sentence_ends() -> None:
    lines = [
        _line("本基金自成立日起至上市日前一個營業日止，經理公司或所委任之基金", y=700.0),
        _line("銷售機構不接受本基金受益權單位之申購或買回。", y=686.0),
        _line("本基金受益憑證之上市買賣，應依相關規定辦理。", y=672.0),
    ]

    blocks = infer_blocks(lines, page_count=1)

    assert len(blocks) == 2
    assert blocks[0].text.endswith("申購或買回。")
    assert blocks[0].text == (
        "本基金自成立日起至上市日前一個營業日止，經理公司或所委任之基金"
        "銷售機構不接受本基金受益權單位之申購或買回。"
    )
    assert blocks[1].text.startswith("本基金受益憑證")


def test_wrapped_numbers_and_latin_words_keep_their_expected_spacing() -> None:
    lines = [
        _line("野村投信客服專線：(02)8758-1568、同業公會電話:(02)2581-", y=700.0),
        _line("7288、財團法人金融消費評議中心電話：0800-789-885", y=686.0),
    ]

    blocks = infer_blocks(lines, page_count=1)

    assert "2581-7288" in blocks[0].text
    assert " 7288" not in blocks[0].text


def test_short_numbered_captions_nest_below_their_parent_section() -> None:
    # Sub-section captions share the body font, so the marker sequence decides.
    lines = [
        _line("壹、 基金概況", page=1, y=760.0, size=12.0, bold=True),
        _line("一、 基金簡介", page=1, y=740.0, size=12.0, bold=True),
        _line("(一)發行總面額", page=1, y=720.0),
        _line("本基金首次募集金額最低為新臺幣貳億元，無最高募集金額之限制。", page=1, y=706.0),
        _line("(二)受益權單位總數", page=1, y=690.0),
        _line("本基金無最高發行受益權單位數之限制。", page=1, y=676.0),
        _line("(三)成立條件", page=1, y=660.0),
        _line(
            "1.本基金之成立條件，為依信託契約第三條第二項之規定，於開始募集日起三十天內"
            "募足最低募集金額新臺幣貳億元整。",
            page=1,
            y=646.0,
        ),
        _line(
            "2.本基金符合成立條件時，經理公司應即函報金管會，經核准後始得成立。", page=1, y=620.0
        ),
    ]

    blocks = infer_blocks(lines, page_count=1)
    headings = [(block.text, block.level) for block in blocks if block.kind is BlockKind.HEADING]

    assert ("一、 基金簡介", 2) in headings
    assert ("(一)發行總面額", 3) in headings
    assert ("(二)受益權單位總數", 3) in headings
    # A caption whose children are numbered keeps the level of its own sequence.
    assert ("(三)成立條件", 3) in headings
    assert all(block.kind is BlockKind.LIST_ITEM for block in blocks if block.text.startswith("1."))


def test_a_bullet_symbol_always_opens_a_new_block() -> None:
    lines = [
        _line("※本基金不受存款保險或其他相關保障機制之保障", y=700.0),
        _line("並由經理公司依相關規定辦理", y=686.0),
        _line("※本公開說明書之內容如有虛偽或隱匿之情事者", y=672.0),
    ]

    blocks = infer_blocks(lines, page_count=1)

    assert len(blocks) == 2
    assert blocks[0].text.endswith("並由經理公司依相關規定辦理")
    assert blocks[1].text.startswith("※本公開說明書")


def test_repeated_running_titles_are_removed_from_every_page() -> None:
    lines = []
    for page in range(1, 9):
        lines.append(_line("野村投信公開說明書", page=page, y=780.0))
        lines.append(_line(f"內容段落 {page} 的敘述文字。", page=page, y=700.0))
        lines.append(_line(f"- {page} -", page=page, y=40.0))

    blocks = infer_blocks(lines, page_count=8)

    assert all("公開說明書" not in block.text for block in blocks)
    assert len(blocks) == 8


def test_body_enumerations_become_list_items_rather_than_headings() -> None:
    lines = [
        _line("壹、 基金概況", y=760.0, size=16.0, bold=True),
        _line(
            "1. 本基金之成立條件，為依信託契約第三條第二項之規定，於開始募集日起"
            "三十天內募足最低募集金額新臺幣貳億元。",
            y=700.0,
        ),
        _line(
            "2. 經理公司應於本基金成立後，依相關規定辦理受益憑證之上市買賣事宜，並公告其上市日期。",
            y=660.0,
        ),
    ]

    blocks = infer_blocks(lines, page_count=1)

    assert blocks[0].kind is BlockKind.HEADING
    assert [block.kind for block in blocks[1:]] == [BlockKind.LIST_ITEM, BlockKind.LIST_ITEM]
    assert all(block.list_level == 0 for block in blocks[1:])


def test_documents_without_markers_fall_back_to_relative_font_size_levels() -> None:
    lines = [
        _line("Annual Report", y=760.0, size=20.0, bold=True),
        _line("Financial Summary", y=720.0, size=14.0, bold=True),
        _line("Revenue increased across every reporting segment.", y=700.0),
    ]

    blocks = infer_blocks(lines, page_count=1)
    headings = [(block.text, block.level) for block in blocks if block.kind is BlockKind.HEADING]

    assert headings == [("Annual Report", 1), ("Financial Summary", 2)]


def test_heading_text_keeps_its_ordinal_marker() -> None:
    lines = [
        _line("壹、 基金概況", y=760.0, size=16.0, bold=True),
        _line("本基金主要投資於中華民國境內之上市上櫃股票。", y=700.0),
        _line("經理公司得依投資策略主動進行投資佈局。", y=686.0),
    ]

    blocks = infer_blocks(lines, page_count=1)

    assert blocks[0].kind is BlockKind.HEADING
    assert blocks[0].text == "壹、 基金概況"


def test_one_oversized_sibling_does_not_split_a_continuous_numbered_sequence() -> None:
    # A half-point font difference on a single line must not outweigh its peers.
    lines = [
        _line("一、 基金名稱：野村臺灣策略高息主動式 ETF 證券投資信託基金", y=740.0),
        _line("二、 基金種類：主動式交易所交易基金", y=726.0),
        _line("三、 基本投資方針：詳見本公開說明書第 1~2 頁", y=712.0),
        _line("四、 基金型態：開放式", y=698.0),
        _line("五、 投資地區：投資於中華民國境內", y=684.0, size=10.5),
        _line("六、 計價幣別：新臺幣", y=670.0),
    ]

    blocks = infer_blocks(lines, page_count=1)

    assert all(block.kind is not BlockKind.HEADING for block in blocks)
    assert any("五、 投資地區" in block.text for block in blocks)
    assert len(blocks) == 6


def test_front_matter_leaves_exactly_one_level_one_heading() -> None:
    lines = [
        _line("野村臺灣策略高息 ETF 基金", page=1, y=760.0, size=16.0),
        _line("（本基金之配息來源可能為收益平準金）", page=1, y=730.0, size=16.0),
        _line("公開說明書", page=1, y=700.0, size=16.0),
        _line("目 錄", page=2, y=760.0, size=18.0),
        _line("壹、 基金概況", page=3, y=760.0, size=12.0),
        _line("一、 基金簡介", page=3, y=730.0, size=12.0),
        _line("本基金主要投資於國內上市上櫃股票，並依投資策略主動調整持股。", page=3, y=700.0),
        _line("經理公司得依市場狀況調整投資組合，以分散投資風險。", page=3, y=686.0),
        _line("基金保管機構依信託契約保管本基金之資產。", page=3, y=672.0),
        _line("受益人得依規定申購或買回本基金之受益權單位。", page=3, y=658.0),
        _line("【封底】", page=4, y=760.0, size=14.0),
    ]

    blocks = infer_blocks(lines, page_count=4)
    headings = [block for block in blocks if block.kind is BlockKind.HEADING]

    assert [block.level for block in headings].count(1) == 1
    assert (
        headings[0].text
        == "野村臺灣策略高息 ETF 基金 （本基金之配息來源可能為收益平準金） 公開說明書"
    )
    assert headings[0].level == 1


def test_heading_levels_never_skip_a_step_in_document_order() -> None:
    lines = [
        _line("野村基金公開說明書", page=1, y=760.0, size=16.0),
        _line("一、 證券投資信託事業總公司之名稱", page=1, y=700.0, size=11.0),
        _line("壹、 基金概況", page=2, y=760.0, size=12.0),
        _line("一、 基金簡介", page=2, y=730.0, size=12.0),
        _line("本基金主要投資於國內上市上櫃股票，並依投資策略主動調整。", page=2, y=700.0),
        _line("經理公司得依市場狀況調整投資組合，以分散投資風險。", page=2, y=686.0),
        _line("基金保管機構依信託契約保管本基金之資產。", page=2, y=672.0),
        _line("受益人得依規定申購或買回本基金之受益權單位。", page=2, y=658.0),
    ]

    blocks = infer_blocks(lines, page_count=2)
    levels = [block.level or 0 for block in blocks if block.kind is BlockKind.HEADING]

    assert levels[0] == 1
    assert all(later - earlier <= 1 for earlier, later in itertools.pairwise(levels))
