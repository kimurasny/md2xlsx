"""md2xlsx のコマンドラインインターフェース。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .converter import DEFAULT_HEADING_LEVEL, ConversionSummary, convert
from .discovery import find_markdown_files
from .sections import DEFAULT_INTRO_TITLE

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2


def _heading_level(value: str) -> int:
    """--heading-level の値を 1〜6 に制限して解釈する。"""
    try:
        level = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("見出しレベルは整数で指定してください") from error
    if not 1 <= level <= 6:
        raise argparse.ArgumentTypeError("見出しレベルは 1〜6 で指定してください")
    return level


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="md2xlsx",
        description="Markdown ファイルを Excel(.xlsx) へ変換します。",
    )
    parser.add_argument("input", type=Path, help="変換対象の Markdown ファイルまたはディレクトリ")
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="ディレクトリ指定時にサブディレクトリも再帰的に探索する",
    )
    parser.add_argument(
        "-l",
        "--heading-level",
        type=_heading_level,
        default=DEFAULT_HEADING_LEVEL,
        metavar="{1-6}",
        help="シート分割の基準となる見出しレベル (既定: %(default)s)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="XLSX の出力先（ファイルまたはディレクトリ）",
    )
    parser.add_argument(
        "--intro-sheet-name",
        default=DEFAULT_INTRO_TITLE,
        help="最初の対象見出しより前の内容を格納するシート名 (既定: %(default)s)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"md2xlsx {__version__}",
    )
    return parser


def _print_summary(summary: ConversionSummary, stream) -> None:
    """変換結果のサマリーと、失敗・警告の詳細を出力する。"""
    for result in summary.results:
        for warning in result.warnings:
            print(f"Warning: {result.source}: {warning}", file=stream)
    for result in summary.failures:
        print(f"Failed: {result.source}: {result.error}", file=stream)

    print(f"Processed: {summary.processed}", file=stream)
    print(f"Succeeded: {summary.succeeded}", file=stream)
    print(f"Failed: {summary.failed}", file=stream)
    print(f"Warnings: {summary.warning_count}", file=stream)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path: Path = args.input
    if not input_path.exists():
        print(f"Error: 入力パスが存在しません: {input_path}", file=sys.stderr)
        return EXIT_USAGE

    try:
        files = find_markdown_files(input_path, recursive=args.recursive)
    except OSError as error:
        print(f"Error: 入力の探索に失敗しました: {error}", file=sys.stderr)
        return EXIT_USAGE

    if not files:
        print(f"Error: Markdown ファイルが見つかりません: {input_path}", file=sys.stderr)
        return EXIT_USAGE

    summary = convert(
        input_path,
        output=args.output,
        recursive=args.recursive,
        heading_level=args.heading_level,
        intro_title=args.intro_sheet_name,
    )

    for result in summary.results:
        if result.succeeded:
            print(f"Converted: {result.source} -> {result.output}")

    _print_summary(summary, sys.stderr)
    return EXIT_OK if summary.failed == 0 else EXIT_FAILED


if __name__ == "__main__":
    raise SystemExit(main())
