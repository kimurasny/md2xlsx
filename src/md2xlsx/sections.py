"""ブロック列を、シート単位のセクションへ分割する。"""

from __future__ import annotations

from .blocks import Block, Heading, Section

DEFAULT_INTRO_TITLE = "Introduction"


def split_sections(
    blocks: list[Block],
    heading_level: int,
    intro_title: str = DEFAULT_INTRO_TITLE,
) -> list[Section]:
    """指定レベルの見出しを境界としてセクションへ分割する。

    最初の対象見出しより前のコンテンツは intro セクションへ入れる。
    実質的なコンテンツが無い場合、intro セクションは作らない。
    """
    intro = Section(title=intro_title, is_intro=True)
    sections: list[Section] = []
    current = intro

    for block in blocks:
        if isinstance(block, Heading) and block.level == heading_level:
            title = block.text.strip()
            current = Section(title=title)
            sections.append(current)
            continue
        current.blocks.append(block)

    result: list[Section] = []
    if intro.has_content() or not sections:
        result.append(intro)
    result.extend(sections)
    return result
