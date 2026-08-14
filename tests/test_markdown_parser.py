"""Markdown 解析（ブロック抽出とインライン装飾）のテスト。"""

from __future__ import annotations

from md2xlsx.blocks import CodeBlock, Heading, ImageBlock, ListBlock, Paragraph, Table
from md2xlsx.markdown_parser import parse_markdown


def test_headings_and_paragraph() -> None:
    blocks = parse_markdown("# タイトル\n\n本文です。\n")
    assert isinstance(blocks[0], Heading)
    assert (blocks[0].level, blocks[0].text) == (1, "タイトル")
    assert isinstance(blocks[1], Paragraph)
    assert blocks[1].text == "本文です。"


def test_inline_decorations() -> None:
    blocks = parse_markdown("これは**太字**と*斜体*と`コード`です。\n")
    runs = blocks[0].runs
    assert [(run.text, run.bold, run.italic, run.code) for run in runs] == [
        ("これは", False, False, False),
        ("太字", True, False, False),
        ("と", False, False, False),
        ("斜体", False, True, False),
        ("と", False, False, False),
        ("コード", False, False, True),
        ("です。", False, False, False),
    ]


def test_nested_lists() -> None:
    blocks = parse_markdown("- A\n  - A1\n- B\n\n1. 一\n2. 二\n")
    bullets, ordered = [block for block in blocks if isinstance(block, ListBlock)]
    assert bullets.ordered is False
    assert [(item.marker, item.indent) for item in bullets.items] == [
        ("・", 0),
        ("・", 1),
        ("・", 0),
    ]
    assert ordered.ordered is True
    assert [item.marker for item in ordered.items] == ["1.", "2."]


def test_table_cells() -> None:
    markdown = "| Name | Type |\n|---|---|\n| id | `string` |\n"
    table = next(block for block in parse_markdown(markdown) if isinstance(block, Table))
    assert table.header == ["Name", "Type"]
    assert table.rows == [["id", "string"]]
    assert table.column_count == 2


def test_code_block_language() -> None:
    block = next(
        item for item in parse_markdown("```python\nx = 1\n```\n") if isinstance(item, CodeBlock)
    )
    assert block.language == "python"
    assert block.lines == ["x = 1"]


def test_image_splits_paragraph() -> None:
    blocks = parse_markdown("前の文 ![図](./a.png) 後の文\n")
    kinds = [type(block) for block in blocks]
    assert kinds == [Paragraph, ImageBlock, Paragraph]
    assert blocks[0].text.strip() == "前の文"
    assert (blocks[1].src, blocks[1].alt) == ("./a.png", "図")
    assert blocks[2].text.strip() == "後の文"


def test_link_is_flattened() -> None:
    blocks = parse_markdown("[ドキュメント](https://example.com/a)\n")
    assert blocks[0].text == "ドキュメント (https://example.com/a)"


def test_blockquote_is_marked() -> None:
    blocks = parse_markdown("> 引用です\n")
    assert isinstance(blocks[0], Paragraph)
    assert blocks[0].quote is True
