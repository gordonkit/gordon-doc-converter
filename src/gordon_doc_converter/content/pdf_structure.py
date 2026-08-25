"""Heuristic block and heading inference from reconstructed PDF text lines."""

from __future__ import annotations

import functools
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from gordon_doc_converter.content.models import (
    BlockKind,
    ContentBlock,
    InlineKind,
    InlineSpan,
    SourceAnchor,
)
from gordon_doc_converter.content.numbering import (
    NumberToken,
    ends_with_sentence_terminator,
    has_dot_leader,
    parse_marker,
    starts_with_bullet,
)
from gordon_doc_converter.content.pdf_layout import TextLine, join_wrapped

HEADING_THRESHOLD = 45
_PROMINENT_SIZE_RATIO = 1.25
_MAX_UNNUMBERED_LENGTH = 40
_MAX_RUNNING_TITLE_LENGTH = 40
_MAX_CAPTION_LENGTH = 30
_CONSENSUS_MARGIN = 20
_MAX_HEADING_LEVEL = 6
_RUNNING_TITLE_RATIO = 0.4
_DIGITS = re.compile(r"\d+")


def _running_key(text: str) -> str:
    """Normalize page numbers so that folios repeat identically across pages."""
    return _DIGITS.sub("#", text)


@dataclass(frozen=True, slots=True)
class _Candidate:
    line: TextLine
    token: NumberToken | None
    score: int


def _body_size(lines: Sequence[TextLine]) -> float:
    weights: Counter[float] = Counter()
    for line in lines:
        weights[line.size] += max(len(line.text), 1)
    if not weights:
        return 10.0
    return max(weights.items(), key=lambda entry: (entry[1], -entry[0]))[0]


def _running_titles(lines: Sequence[TextLine], page_count: int) -> set[str]:
    if page_count < 4:
        return set()
    extremes: dict[int, list[TextLine]] = {}
    for line in lines:
        extremes.setdefault(line.page_number, []).append(line)
    seen: dict[str, set[int]] = {}
    for page_number, page_lines in extremes.items():
        ordered = sorted(page_lines, key=lambda item: item.y)
        for line in {ordered[0], ordered[-1]}:
            if len(line.text) > _MAX_RUNNING_TITLE_LENGTH:
                continue
            seen.setdefault(_running_key(line.text), set()).add(page_number)
    threshold = max(3, int(page_count * _RUNNING_TITLE_RATIO))
    return {key for key, pages in seen.items() if len(pages) >= threshold}


def _score(
    line: TextLine,
    token: NumberToken | None,
    body_size: float,
    gap: float,
    *,
    captions_prose: bool = False,
) -> int:
    ratio = line.size / body_size if body_size else 1.0
    length = len(line.text)
    # Body text often differs from section headings by a single point, so an
    # ordinal marker or a short, clearly larger line is required before scoring.
    if token is None and (ratio < _PROMINENT_SIZE_RATIO or length > _MAX_UNNUMBERED_LENGTH):
        return 0
    score = 0
    if ratio >= 1.5:
        score += 45
    elif ratio >= _PROMINENT_SIZE_RATIO:
        score += 35
    elif ratio >= 1.05:
        score += 20
    if line.bold:
        score += 10
    if token is not None:
        score += 25 if token.unit else 15
    # A short numbered line introducing unnumbered prose is acting as a caption.
    if captions_prose:
        score += 15
    if length <= 30:
        score += 15
    elif length <= 50:
        score += 5
    if length > 70:
        score -= 35
    if ends_with_sentence_terminator(line.text):
        score -= 25
    if has_dot_leader(line.text):
        score -= 60
    if gap >= line.size * 1.5:
        score += 10
    return score


def _signature(candidate: _Candidate) -> tuple[float, str]:
    numbering = candidate.token.numbering_class if candidate.token else ""
    return (candidate.line.size, numbering)


def _heading_levels(candidates: Sequence[_Candidate]) -> dict[tuple[float, str], int]:
    order: dict[tuple[float, str], int] = {}
    for index, candidate in enumerate(candidates):
        order.setdefault(_signature(candidate), index)

    # Ordinal markers describe the author's own hierarchy, so they outrank size.
    numbered = {signature: index for signature, index in order.items() if signature[1]}
    if not numbered:
        sizes = sorted({signature[0] for signature in order}, reverse=True)
        return {
            signature: min(sizes.index(signature[0]) + 1, _MAX_HEADING_LEVEL) for signature in order
        }

    ranked = sorted(numbered.items(), key=lambda entry: (-entry[0][0], entry[1]))
    backbone_size = ranked[0][0][0]
    front_matter = {
        signature: index
        for signature, index in order.items()
        if not signature[1] and signature[0] > backbone_size
    }
    # Cover pages, tables of contents, and back matter outrank the numbered
    # backbone in size without being hierarchy levels, so only the first of them
    # keeps level one and everything else moves one level down.
    shift = 1 if front_matter else 0
    levels = {
        signature: min(rank + 1 + shift, _MAX_HEADING_LEVEL)
        for rank, (signature, _) in enumerate(ranked)
    }
    title = (
        min(front_matter, key=lambda signature: front_matter[signature]) if front_matter else None
    )
    for signature in front_matter:
        levels[signature] = 1 if signature == title else min(1 + shift, _MAX_HEADING_LEVEL)
    for signature in order:
        if signature in levels:
            continue
        nearest = min(ranked, key=lambda entry: abs(entry[0][0] - signature[0]))[0]
        levels[signature] = levels[nearest]
    return levels


def _list_levels(tokens: Sequence[NumberToken]) -> dict[str, int]:
    order: list[str] = []
    for token in tokens:
        if token.numbering_class not in order:
            order.append(token.numbering_class)
    return {numbering_class: index for index, numbering_class in enumerate(order)}


def _block(kind: BlockKind, text: str, line: TextLine, **fields: object) -> ContentBlock:
    return ContentBlock(
        kind,
        (InlineSpan(InlineKind.TEXT, text),),
        page_number=line.page_number,
        source_anchor=SourceAnchor("pdf-page", page_number=line.page_number),
        **fields,  # type: ignore[arg-type]
    )


def _consistent_headings(kept: Sequence[tuple[TextLine, NumberToken | None, int]]) -> set[int]:
    """Align each numbering sequence with the verdict most of its members reached."""
    headings = {index for index, (_, _, score) in enumerate(kept) if score >= HEADING_THRESHOLD}
    groups: dict[tuple[int, str], list[int]] = {}
    for index, (line, token, _) in enumerate(kept):
        if token is None:
            continue
        groups.setdefault((line.page_number, token.numbering_class), []).append(index)
    for members in groups.values():
        promoted = [index for index in members if index in headings]
        if not promoted:
            continue
        if len(promoted) * 2 < len(members):
            headings.difference_update(promoted)
            continue
        headings.update(
            index for index in members if kept[index][2] >= HEADING_THRESHOLD - _CONSENSUS_MARGIN
        )
    return headings


def infer_blocks(lines: Sequence[TextLine], page_count: int) -> list[ContentBlock]:
    """Classify text lines into headings, list items, and merged paragraphs."""
    running = _running_titles(lines, page_count)
    body_size = _body_size(lines)

    kept: list[tuple[TextLine, NumberToken | None, int]] = []
    parsed: list[tuple[TextLine, NumberToken | None, float]] = []
    previous_y: float | None = None
    previous_page = 0
    for line in lines:
        if _running_key(line.text) in running:
            previous_y = None
            continue
        gap = 0.0
        if previous_y is not None and line.page_number == previous_page:
            gap = max(previous_y - line.y, 0.0)
        previous_y, previous_page = line.y, line.page_number
        parsed.append((line, parse_marker(line.text), gap))

    for index, (line, token, gap) in enumerate(parsed):
        following = parsed[index + 1] if index + 1 < len(parsed) else None
        captions_prose = (
            token is not None
            and len(line.text) <= _MAX_CAPTION_LENGTH
            and following is not None
            and following[1] is None
            and following[0].page_number == line.page_number
            and not starts_with_bullet(following[0].text)
        )
        kept.append(
            (line, token, _score(line, token, body_size, gap, captions_prose=captions_prose))
        )

    headings = _consistent_headings(kept)
    candidates = [
        _Candidate(line, token, score)
        for index, (line, token, score) in enumerate(kept)
        if index in headings
    ]
    levels = _heading_levels(candidates)
    heading_classes = {
        candidate.token.numbering_class for candidate in candidates if candidate.token
    }
    list_tokens = [
        token
        for index, (line, token, score) in enumerate(kept)
        if token is not None
        and index not in headings
        and token.numbering_class not in heading_classes
    ]
    list_levels = _list_levels(list_tokens)

    blocks: list[ContentBlock] = []
    pending: list[str] | None = None
    pending_line: TextLine | None = None
    open_title: tuple[float, str] | None = None
    previous_level = 0
    assigned: dict[tuple[float, str], int] = {}

    def flush() -> None:
        nonlocal pending, pending_line
        if pending is not None and pending_line is not None:
            text = functools.reduce(join_wrapped, pending)
            blocks.append(_block(BlockKind.PARAGRAPH, text, pending_line))
        pending = None
        pending_line = None

    for index, (line, token, score) in enumerate(kept):
        if index in headings:
            flush()
            signature = _signature(_Candidate(line, token, score))
            # An unnumbered title block spans several lines of identical styling.
            if token is None and open_title == signature:
                previous = blocks[-1]
                blocks[-1] = _block(
                    BlockKind.HEADING,
                    f"{previous.text} {line.text}",
                    line,
                    level=previous.level,
                )
                continue
            open_title = signature if token is None else None
            # Inferred styles can leave gaps, but a readable outline never skips a
            # level, and every heading of one style has to stay on its own level.
            level = assigned.get(signature)
            if level is None:
                level = min(levels[signature], previous_level + 1)
                assigned[signature] = level
            previous_level = level
            blocks.append(_block(BlockKind.HEADING, line.text, line, level=level))
            continue
        open_title = None
        if token is not None and token.numbering_class in list_levels:
            flush()
            if has_dot_leader(line.text):
                blocks.append(_block(BlockKind.PARAGRAPH, line.text, line))
                continue
            blocks.append(
                _block(
                    BlockKind.LIST_ITEM,
                    line.text,
                    line,
                    list_level=list_levels[token.numbering_class],
                )
            )
            continue
        if pending is not None and pending_line is not None:
            # A marker or bullet at the start of a line always opens a new block.
            continuous = (
                token is None
                and not starts_with_bullet(line.text)
                and not ends_with_sentence_terminator(pending[-1])
            )
            if continuous and line.page_number == pending_line.page_number:
                pending.append(line.text)
                continue
            flush()
        pending = [line.text]
        pending_line = line

    flush()
    return blocks
