"""Markdown と Excel の間に置く中間ブロックモデル。

markdown-it-py のトークン列を、この単純なデータ構造へ変換してから
Excel へ描画する。パーサー依存を Excel 側へ持ち込まないための層。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Run:
    """段落内の連続した文字列と、その装飾情報。"""

    text: str
    bold: bool = False
    italic: bool = False
    code: bool = False


@dataclass
class Heading:
    """見出し（#〜######）。"""

    level: int
    runs: list[Run] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(run.text for run in self.runs)


@dataclass
class Paragraph:
    """通常の段落。引用の本文としても使う。"""

    runs: list[Run] = field(default_factory=list)
    quote: bool = False

    @property
    def text(self) -> str:
        return "".join(run.text for run in self.runs)


@dataclass
class ListItem:
    """リストの 1 項目。"""

    marker: str
    runs: list[Run] = field(default_factory=list)
    indent: int = 0


@dataclass
class ListBlock:
    """箇条書き / 番号付きリスト。"""

    items: list[ListItem] = field(default_factory=list)
    ordered: bool = False


@dataclass
class Table:
    """Markdown テーブル。セル文字列を行列で保持する。"""

    header: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)

    @property
    def column_count(self) -> int:
        widths = [len(self.header)] + [len(row) for row in self.rows]
        return max(widths) if widths else 0


@dataclass
class CodeBlock:
    """コードブロック（フェンス / インデント）。"""

    text: str
    language: str = ""

    @property
    def lines(self) -> list[str]:
        return self.text.splitlines() or [""]


@dataclass
class ImageBlock:
    """画像。src はリンク先そのままの文字列。"""

    src: str
    alt: str = ""


@dataclass
class HorizontalRule:
    """水平線。"""


Block = Heading | Paragraph | ListBlock | Table | CodeBlock | ImageBlock | HorizontalRule


@dataclass
class Section:
    """1 つの Excel シートに対応する Markdown の区間。"""

    title: str
    blocks: list[Block] = field(default_factory=list)
    is_intro: bool = False

    def has_content(self) -> bool:
        """空白のみでない実質的なコンテンツを持つか。"""
        for block in self.blocks:
            if isinstance(block, (Table, CodeBlock, ImageBlock, ListBlock)):
                return True
            if isinstance(block, (Heading, Paragraph)) and block.text.strip():
                return True
        return False
