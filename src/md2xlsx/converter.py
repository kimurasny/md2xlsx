"""変換処理全体の制御。ファイル探索から XLSX 保存までを束ねる。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .discovery import find_markdown_files
from .markdown_parser import parse_markdown
from .sections import DEFAULT_INTRO_TITLE, split_sections
from .workbook import WorkbookBuilder

DEFAULT_HEADING_LEVEL = 2


@dataclass
class FileResult:
    """1 ファイル分の変換結果。"""

    source: Path
    output: Path | None = None
    succeeded: bool = False
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    sheet_count: int = 0
    image_count: int = 0


@dataclass
class ConversionSummary:
    """複数ファイル処理のサマリー。"""

    results: list[FileResult] = field(default_factory=list)

    @property
    def processed(self) -> int:
        return len(self.results)

    @property
    def succeeded(self) -> int:
        return sum(1 for result in self.results if result.succeeded)

    @property
    def failed(self) -> int:
        return self.processed - self.succeeded

    @property
    def warning_count(self) -> int:
        return sum(len(result.warnings) for result in self.results)

    @property
    def failures(self) -> list[FileResult]:
        return [result for result in self.results if not result.succeeded]


def convert_file(
    source: Path,
    output_path: Path,
    heading_level: int = DEFAULT_HEADING_LEVEL,
    intro_title: str = DEFAULT_INTRO_TITLE,
) -> FileResult:
    """Markdown ファイル 1 つを XLSX へ変換する。"""
    result = FileResult(source=source, output=output_path)
    text = source.read_text(encoding="utf-8")
    blocks = parse_markdown(text)
    sections = split_sections(blocks, heading_level=heading_level, intro_title=intro_title)

    builder = WorkbookBuilder(base_dir=source.parent)
    workbook = builder.build(sections)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)

    result.succeeded = True
    result.warnings = builder.warnings
    result.sheet_count = len(workbook.sheetnames)
    result.image_count = builder.image_count
    return result


def _resolve_output_path(
    source: Path,
    input_path: Path,
    output: Path | None,
) -> Path:
    """入力ファイルに対する出力 XLSX のパスを決める。

    ディレクトリ入力の場合、入力からの相対構造を出力先でも維持する。
    """
    if input_path.is_file():
        if output is None:
            return source.with_suffix(".xlsx")
        if output.suffix.lower() == ".xlsx":
            return output
        return output / f"{source.stem}.xlsx"

    base_output = output if output is not None else input_path
    relative = source.relative_to(input_path).parent
    return base_output / relative / f"{source.stem}.xlsx"


def convert(
    input_path: Path,
    output: Path | None = None,
    recursive: bool = False,
    heading_level: int = DEFAULT_HEADING_LEVEL,
    intro_title: str = DEFAULT_INTRO_TITLE,
) -> ConversionSummary:
    """入力パス配下の Markdown をまとめて変換する。

    1 ファイルの失敗で全体を中断せず、残りのファイルの処理を継続する。
    """
    summary = ConversionSummary()
    files = find_markdown_files(input_path, recursive=recursive)

    for source in files:
        try:
            output_path = _resolve_output_path(source, input_path, output)
            summary.results.append(
                convert_file(
                    source,
                    output_path,
                    heading_level=heading_level,
                    intro_title=intro_title,
                )
            )
        except Exception as error:  # 1 ファイルの失敗で全体を止めない
            summary.results.append(
                FileResult(source=source, succeeded=False, error=f"{type(error).__name__}: {error}")
            )
    return summary
