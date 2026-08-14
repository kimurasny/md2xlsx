"""入力パスから対象 Markdown ファイルを探索する。"""

from __future__ import annotations

from pathlib import Path

MARKDOWN_SUFFIXES = frozenset({".md", ".markdown", ".mdown", ".mkd"})


def is_markdown_file(path: Path) -> bool:
    """拡張子から Markdown ファイルか判定する（大文字小文字を区別しない）。"""
    return path.is_file() and path.suffix.lower() in MARKDOWN_SUFFIXES


def find_markdown_files(input_path: Path, recursive: bool) -> list[Path]:
    """変換対象のファイル一覧を返す。

    ファイル指定ならそのファイル、ディレクトリ指定なら直下（recursive 時は
    すべての下位ディレクトリ）の Markdown ファイルを返す。
    """
    if input_path.is_file():
        return [input_path]

    if not input_path.is_dir():
        raise FileNotFoundError(f"入力パスが存在しません: {input_path}")

    pattern = "**/*" if recursive else "*"
    files = [path for path in sorted(input_path.glob(pattern)) if is_markdown_file(path)]
    return files
