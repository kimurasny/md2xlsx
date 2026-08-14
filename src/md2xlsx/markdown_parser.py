"""markdown-it-py のトークン列を中間ブロックモデルへ変換する。

正規表現による解析は行わず、パーサーが返すトークンの構造のみを利用する。
"""

from __future__ import annotations

from markdown_it import MarkdownIt
from markdown_it.token import Token

from .blocks import (
    Block,
    CodeBlock,
    Heading,
    HorizontalRule,
    ImageBlock,
    ListBlock,
    ListItem,
    Paragraph,
    Run,
    Table,
)

# インライン解析の結果。装飾付き文字列か、画像のどちらか。
InlinePiece = Run | ImageBlock


def create_parser() -> MarkdownIt:
    """テーブル等を有効化した Markdown パーサーを生成する。

    linkify は追加依存を避けるため有効化しない。
    """
    return MarkdownIt("commonmark").enable(["table", "strikethrough"])


def parse_markdown(text: str) -> list[Block]:
    """Markdown 文字列をブロックの並びへ変換する。"""
    tokens = create_parser().parse(text)
    return _BlockBuilder(tokens).build()


def _link_label(label: str, href: str) -> str:
    """リンクを Excel のセルに収まる 1 行の文字列へ整形する。"""
    label = label.strip()
    if not href:
        return label
    if not label or label == href:
        return href
    return f"{label} ({href})"


def parse_inline(token: Token) -> list[InlinePiece]:
    """inline トークンの children を装飾付き文字列と画像へ分解する。"""
    pieces: list[InlinePiece] = []
    bold = 0
    italic = 0
    link_stack: list[str] = []
    link_label = ""

    def add_text(text: str) -> None:
        nonlocal link_label
        if link_stack:
            link_label += text
            return
        if text:
            pieces.append(Run(text=text, bold=bold > 0, italic=italic > 0))

    for child in token.children or []:
        kind = child.type
        if kind == "text":
            add_text(child.content)
        elif kind == "code_inline":
            if link_stack:
                link_label += child.content
            else:
                pieces.append(
                    Run(
                        text=child.content,
                        bold=bold > 0,
                        italic=italic > 0,
                        code=True,
                    )
                )
        elif kind in ("softbreak", "hardbreak"):
            add_text("\n")
        elif kind == "strong_open":
            bold += 1
        elif kind == "strong_close":
            bold = max(0, bold - 1)
        elif kind in ("em_open", "s_open"):
            italic += 1
        elif kind in ("em_close", "s_close"):
            italic = max(0, italic - 1)
        elif kind == "link_open":
            link_stack.append(str(child.attrs.get("href", "")))
            link_label = ""
        elif kind == "link_close":
            href = link_stack.pop() if link_stack else ""
            label = link_label
            link_label = ""
            add_text(_link_label(label, href))
        elif kind == "image":
            src = str(child.attrs.get("src", ""))
            alt = child.content or _plain_text(child)
            pieces.append(ImageBlock(src=src, alt=alt))
        elif kind == "html_inline":
            add_text(child.content)
    return pieces


def _plain_text(token: Token) -> str:
    """トークン配下のテキストのみを連結する。"""
    if token.children:
        return "".join(_plain_text(child) for child in token.children)
    return token.content or ""


class _BlockBuilder:
    """トークン列を先頭から順に読み進めてブロックを組み立てる。"""

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._index = 0
        self._blocks: list[Block] = []

    def build(self) -> list[Block]:
        while self._index < len(self._tokens):
            token = self._tokens[self._index]
            handler = self._dispatch(token.type)
            if handler is None:
                self._index += 1
                continue
            handler()
        return self._blocks

    def _dispatch(self, token_type: str):
        table = {
            "heading_open": self._read_heading,
            "paragraph_open": self._read_paragraph,
            "bullet_list_open": self._read_list,
            "ordered_list_open": self._read_list,
            "table_open": self._read_table,
            "fence": self._read_code,
            "code_block": self._read_code,
            "blockquote_open": self._read_blockquote,
            "hr": self._read_rule,
            "html_block": self._read_html_block,
        }
        return table.get(token_type)

    def _current(self) -> Token:
        return self._tokens[self._index]

    def _emit_pieces(self, pieces: list[InlinePiece], *, quote: bool = False) -> None:
        """装飾付き文字列と画像の並びを段落 / 画像ブロックへ振り分ける。"""
        buffer: list[Run] = []
        for piece in pieces:
            if isinstance(piece, ImageBlock):
                if any(run.text.strip() for run in buffer):
                    self._blocks.append(Paragraph(runs=buffer, quote=quote))
                buffer = []
                self._blocks.append(piece)
            else:
                buffer.append(piece)
        if any(run.text.strip() for run in buffer):
            self._blocks.append(Paragraph(runs=buffer, quote=quote))

    def _read_heading(self) -> None:
        level = int(self._current().tag[1:])
        self._index += 1
        runs: list[Run] = []
        while self._index < len(self._tokens) and self._current().type != "heading_close":
            if self._current().type == "inline":
                for piece in parse_inline(self._current()):
                    if isinstance(piece, Run):
                        runs.append(piece)
            self._index += 1
        self._index += 1
        self._blocks.append(Heading(level=level, runs=runs))

    def _read_paragraph(self, *, quote: bool = False) -> None:
        self._index += 1
        pieces: list[InlinePiece] = []
        while self._index < len(self._tokens) and self._current().type != "paragraph_close":
            if self._current().type == "inline":
                pieces.extend(parse_inline(self._current()))
            self._index += 1
        self._index += 1
        self._emit_pieces(pieces, quote=quote)

    def _read_blockquote(self) -> None:
        depth = 0
        self._index += 1
        while self._index < len(self._tokens):
            token = self._current()
            if token.type == "blockquote_open":
                depth += 1
            elif token.type == "blockquote_close":
                if depth == 0:
                    self._index += 1
                    return
                depth -= 1
            elif token.type == "paragraph_open":
                self._read_paragraph(quote=True)
                continue
            elif token.type in ("fence", "code_block"):
                self._read_code()
                continue
            elif token.type in ("bullet_list_open", "ordered_list_open"):
                self._read_list()
                continue
            elif token.type == "table_open":
                self._read_table()
                continue
            self._index += 1

    def _read_code(self) -> None:
        token = self._current()
        language = (token.info or "").strip().split(" ")[0]
        self._blocks.append(CodeBlock(text=token.content.rstrip("\n"), language=language))
        self._index += 1

    def _read_rule(self) -> None:
        self._blocks.append(HorizontalRule())
        self._index += 1

    def _read_html_block(self) -> None:
        content = self._current().content.strip()
        self._index += 1
        if content:
            self._blocks.append(Paragraph(runs=[Run(text=content)]))

    def _read_list(self) -> None:
        ordered = self._current().type == "ordered_list_open"
        block = ListBlock(ordered=ordered)
        self._blocks.append(block)
        self._consume_list(block, indent=0)

    def _consume_list(self, block: ListBlock, indent: int) -> None:
        """リストを 1 つ読み進める。ネストは indent を増やして同じ block へ格納する。"""
        ordered = self._current().type == "ordered_list_open"
        counter = 0
        self._index += 1
        while self._index < len(self._tokens):
            token = self._current()
            if token.type in ("bullet_list_close", "ordered_list_close"):
                self._index += 1
                return
            if token.type == "list_item_open":
                counter += 1
                marker = f"{counter}." if ordered else "・"
                self._index += 1
                self._consume_list_item(block, marker=marker, indent=indent)
                continue
            self._index += 1

    def _consume_list_item(self, block: ListBlock, marker: str, indent: int) -> None:
        first_line = True
        while self._index < len(self._tokens):
            token = self._current()
            if token.type == "list_item_close":
                self._index += 1
                return
            if token.type == "paragraph_open":
                self._index += 1
                pieces: list[InlinePiece] = []
                while self._index < len(self._tokens) and self._current().type != "paragraph_close":
                    if self._current().type == "inline":
                        pieces.extend(parse_inline(self._current()))
                    self._index += 1
                self._index += 1
                runs = [piece for piece in pieces if isinstance(piece, Run)]
                images = [piece for piece in pieces if isinstance(piece, ImageBlock)]
                if any(run.text.strip() for run in runs):
                    item_marker = marker if first_line else ""
                    block.items.append(ListItem(marker=item_marker, runs=runs, indent=indent))
                    first_line = False
                for image in images:
                    self._blocks.append(image)
                continue
            if token.type in ("bullet_list_open", "ordered_list_open"):
                self._consume_list(block, indent=indent + 1)
                continue
            if token.type in ("fence", "code_block"):
                self._read_code()
                continue
            if token.type == "table_open":
                self._read_table()
                continue
            self._index += 1

    def _read_table(self) -> None:
        table = Table()
        in_header = False
        current_row: list[str] | None = None
        self._index += 1
        while self._index < len(self._tokens):
            token = self._current()
            kind = token.type
            if kind == "table_close":
                self._index += 1
                break
            if kind == "thead_open":
                in_header = True
            elif kind == "thead_close":
                in_header = False
            elif kind == "tr_open":
                current_row = []
            elif kind == "tr_close":
                if current_row is not None:
                    if in_header and not table.header:
                        table.header = current_row
                    else:
                        table.rows.append(current_row)
                current_row = None
            elif kind in ("th_open", "td_open"):
                self._index += 1
                cell = self._read_cell()
                if current_row is not None:
                    current_row.append(cell)
                continue
            self._index += 1
        self._blocks.append(table)

    def _read_cell(self) -> str:
        """テーブルセルの内容を 1 つの文字列として取り出す。"""
        parts: list[str] = []
        while self._index < len(self._tokens):
            token = self._current()
            if token.type in ("th_close", "td_close"):
                self._index += 1
                break
            if token.type == "inline":
                for piece in parse_inline(token):
                    if isinstance(piece, Run):
                        parts.append(piece.text)
                    else:
                        parts.append(f"[{piece.alt or 'image'}: {piece.src}]")
            self._index += 1
        return "".join(parts).strip()
