"""テーブルの配色・罫線とグリッド線非表示のテスト。"""

from __future__ import annotations

from pathlib import Path

from conftest import open_workbook

from md2xlsx.converter import convert_file
from md2xlsx.workbook import TABLE_BORDER_COLOR, TABLE_HEADER_COLOR

MARKDOWN = """## 計画

| 項目 | 所要期間（週） |
|------|----------------|
| 事前調査 | 4 |

本文。
"""


def _convert(write_md, tmp_path: Path):
    source = write_md("plan.md", MARKDOWN)
    output = tmp_path / "plan.xlsx"
    convert_file(source, output)
    return open_workbook(output)["計画"]


def test_table_header_and_border_colors(write_md, tmp_path: Path) -> None:
    sheet = _convert(write_md, tmp_path)
    header_row = next(
        row
        for row in range(1, sheet.max_row + 1)
        if sheet.cell(row=row, column=1).value == "項目"
    )

    header = sheet.cell(row=header_row, column=1)
    assert header.fill.fgColor.rgb.endswith(TABLE_HEADER_COLOR)
    for side in (header.border.top, header.border.left):
        assert side.style == "thin"
        assert side.color.rgb.endswith(TABLE_BORDER_COLOR)

    body = sheet.cell(row=header_row + 1, column=1)
    assert body.fill.fill_type is None
    assert body.border.bottom.color.rgb.endswith(TABLE_BORDER_COLOR)


def test_non_table_cells_have_no_border(write_md, tmp_path: Path) -> None:
    sheet = _convert(write_md, tmp_path)
    text_row = next(
        row
        for row in range(1, sheet.max_row + 1)
        if sheet.cell(row=row, column=1).value == "本文。"
    )
    cell = sheet.cell(row=text_row, column=1)
    assert cell.border.top.style is None
    assert cell.border.bottom.style is None


def test_grid_lines_are_hidden(write_md, tmp_path: Path) -> None:
    sheet = _convert(write_md, tmp_path)
    assert sheet.sheet_view.showGridLines is False
