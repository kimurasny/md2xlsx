"""単一ファイル変換・シート分割・本文配置のテスト。"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import column_values, open_workbook, row_values

from md2xlsx.converter import convert, convert_file

SPEC_MD = """# システム仕様書

この文書について説明します。

## 概要

本文です。

## API

### 詳細

APIについて。

## データベース

DBについて。
"""


def test_default_heading_level_splits_sheets(write_md, tmp_path: Path) -> None:
    source = write_md("spec.md", SPEC_MD)
    output = tmp_path / "out" / "spec.xlsx"
    result = convert_file(source, output)

    assert result.succeeded
    workbook = open_workbook(output)
    assert workbook.sheetnames == ["Introduction", "概要", "API", "データベース"]

    intro = column_values(workbook["Introduction"])
    assert intro == ["システム仕様書", "この文書について説明します。"]
    # シート分割対象外の見出しは本文として A 列に残る
    assert column_values(workbook["API"]) == ["詳細", "APIについて。"]


def test_heading_level_1(write_md, tmp_path: Path) -> None:
    source = write_md("spec.md", SPEC_MD)
    output = tmp_path / "l1.xlsx"
    convert_file(source, output, heading_level=1)

    workbook = open_workbook(output)
    assert workbook.sheetnames == ["システム仕様書"]
    values = column_values(workbook["システム仕様書"])
    assert "概要" in values
    assert "データベース" in values


def test_heading_level_3(write_md, tmp_path: Path) -> None:
    source = write_md("spec.md", SPEC_MD)
    output = tmp_path / "l3.xlsx"
    convert_file(source, output, heading_level=3)

    workbook = open_workbook(output)
    assert workbook.sheetnames == ["Introduction", "詳細"]
    # ### 以降は「詳細」シートへ入り、レベル 2 見出しは本文として残る
    detail = column_values(workbook["詳細"])
    assert detail[0] == "APIについて。"
    assert "データベース" in detail
    intro = column_values(workbook["Introduction"])
    assert intro[:3] == ["システム仕様書", "この文書について説明します。", "概要"]


@pytest.mark.parametrize("level", [4, 5, 6])
def test_heading_levels_4_to_6(write_md, tmp_path: Path, level: int) -> None:
    marker = "#" * level
    source = write_md("deep.md", f"# 見出し1\n\n前文\n\n{marker} 対象\n\n本文\n")
    output = tmp_path / f"l{level}.xlsx"
    convert_file(source, output, heading_level=level)

    workbook = open_workbook(output)
    assert workbook.sheetnames == ["Introduction", "対象"]
    assert column_values(workbook["対象"]) == ["本文"]


def test_no_intro_sheet_when_no_leading_content(write_md, tmp_path: Path) -> None:
    source = write_md("a.md", "## 概要\n\n本文\n")
    output = tmp_path / "a.xlsx"
    convert_file(source, output)

    workbook = open_workbook(output)
    assert workbook.sheetnames == ["概要"]


def test_duplicate_headings(write_md, tmp_path: Path) -> None:
    source = write_md("dup.md", "## API\n\n1つ目\n\n## API\n\n2つ目\n\n## API\n\n3つ目\n")
    output = tmp_path / "dup.xlsx"
    convert_file(source, output)

    workbook = open_workbook(output)
    assert workbook.sheetnames == ["API", "API_2", "API_3"]
    assert column_values(workbook["API_2"]) == ["2つ目"]


def test_long_and_forbidden_heading_names(write_md, tmp_path: Path) -> None:
    long_heading = "あ" * 40
    source = write_md("names.md", f"## {long_heading}\n\n本文\n\n## API[v1]:/list*?\n\n本文2\n")
    output = tmp_path / "names.xlsx"
    convert_file(source, output)

    workbook = open_workbook(output)
    assert len(workbook.sheetnames) == 2
    for name in workbook.sheetnames:
        assert len(name) <= 31
        assert not set(name) & set("[]:*?/\\")


def test_no_target_heading(write_md, tmp_path: Path) -> None:
    source = write_md("flat.md", "# タイトル\n\n本文のみ。\n")
    output = tmp_path / "flat.xlsx"
    convert_file(source, output)

    workbook = open_workbook(output)
    assert workbook.sheetnames == ["Introduction"]
    assert column_values(workbook["Introduction"]) == ["タイトル", "本文のみ。"]


def test_empty_markdown(write_md, tmp_path: Path) -> None:
    source = write_md("empty.md", "")
    output = tmp_path / "empty.xlsx"
    result = convert_file(source, output)

    assert result.succeeded
    workbook = open_workbook(output)
    assert workbook.sheetnames == ["Introduction"]
    assert column_values(workbook["Introduction"]) == []


def test_lists_code_quote_and_inline(write_md, tmp_path: Path) -> None:
    markdown = """## 概要

これは**重要**な`概要`です。

- 項目A
- 項目B
  - 項目B-1

1. 一番目
2. 二番目

> 引用文

```python
value = 1
```

インライン [リンク](https://example.com/docs) を含みます。

---
"""
    source = write_md("elements.md", markdown)
    output = tmp_path / "elements.xlsx"
    convert_file(source, output)

    values = column_values(open_workbook(output)["概要"])
    joined = "\n".join(values)
    assert "これは重要な概要です。" in values
    assert "・ 項目A" in values
    assert any(value.strip() == "・ 項目B-1" for value in values)
    assert "1. 一番目" in values
    assert "2. 二番目" in values
    assert "> 引用文" in values
    assert "[code: python]" in values
    assert "value = 1" in values
    assert "リンク (https://example.com/docs)" in joined


def test_table_expanded_into_cells(write_md, tmp_path: Path) -> None:
    markdown = """## API

| Name | Type | Required |
|------|------|----------|
| id | string | Yes |
| name | string | No |

テーブルの後の文章。
"""
    source = write_md("table.md", markdown)
    output = tmp_path / "table.xlsx"
    convert_file(source, output)

    sheet = open_workbook(output)["API"]
    header_row = next(
        row
        for row in range(1, sheet.max_row + 1)
        if sheet.cell(row=row, column=1).value == "Name"
    )
    assert row_values(sheet, header_row, 3) == ["Name", "Type", "Required"]
    assert row_values(sheet, header_row + 1, 3) == ["id", "string", "Yes"]
    assert row_values(sheet, header_row + 2, 3) == ["name", "string", "No"]
    assert sheet.cell(row=header_row, column=1).font.bold is True
    assert sheet.cell(row=header_row, column=1).border.top.style == "thin"
    assert "テーブルの後の文章。" in column_values(sheet)


def test_multiple_tables(write_md, tmp_path: Path) -> None:
    markdown = """## 表

| A | B |
|---|---|
| 1 | 2 |

間の文章

| C | D | E |
|---|---|---|
| 3 | 4 | 5 |
"""
    source = write_md("tables.md", markdown)
    output = tmp_path / "tables.xlsx"
    convert_file(source, output)

    sheet = open_workbook(output)["表"]
    column_a = column_values(sheet)
    assert column_a.count("A") == 1
    assert "C" in column_a
    assert "間の文章" in column_a
    row_of_c = next(
        row for row in range(1, sheet.max_row + 1) if sheet.cell(row=row, column=1).value == "C"
    )
    assert row_values(sheet, row_of_c + 1, 3) == ["3", "4", "5"]


def test_directory_conversion_non_recursive(tmp_path: Path) -> None:
    (tmp_path / "input" / "sub").mkdir(parents=True)
    (tmp_path / "input" / "aaa.md").write_text("## A\n\nA本文\n", encoding="utf-8")
    (tmp_path / "input" / "bbb.md").write_text("## B\n\nB本文\n", encoding="utf-8")
    (tmp_path / "input" / "sub" / "ccc.md").write_text("## C\n\nC本文\n", encoding="utf-8")

    summary = convert(tmp_path / "input", output=tmp_path / "output", recursive=False)

    assert summary.processed == 2
    assert summary.succeeded == 2
    assert (tmp_path / "output" / "aaa.xlsx").is_file()
    assert (tmp_path / "output" / "bbb.xlsx").is_file()
    assert not (tmp_path / "output" / "sub").exists()


def test_directory_conversion_recursive_keeps_structure(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    (docs / "api").mkdir(parents=True)
    (docs / "database").mkdir(parents=True)
    (docs / "README.md").write_text("## 概要\n\n本文\n", encoding="utf-8")
    (docs / "api" / "api.md").write_text("## API\n\n本文\n", encoding="utf-8")
    (docs / "database" / "database.md").write_text("## DB\n\n本文\n", encoding="utf-8")

    summary = convert(docs, output=tmp_path / "output", recursive=True)

    assert summary.processed == 3
    assert summary.failed == 0
    assert (tmp_path / "output" / "README.xlsx").is_file()
    assert (tmp_path / "output" / "api" / "api.xlsx").is_file()
    assert (tmp_path / "output" / "database" / "database.xlsx").is_file()


def test_partial_failure_continues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder = tmp_path / "docs"
    folder.mkdir()
    (folder / "ok.md").write_text("## OK\n\n本文\n", encoding="utf-8")
    (folder / "ng.md").write_text("## NG\n\n本文\n", encoding="utf-8")

    original_read_text = Path.read_text

    def flaky_read_text(self: Path, *args, **kwargs):
        if self.name == "ng.md":
            raise OSError("読み込み失敗")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", flaky_read_text)

    summary = convert(folder, output=tmp_path / "out", recursive=False)

    assert summary.processed == 2
    assert summary.succeeded == 1
    assert summary.failed == 1
    assert summary.failures[0].source.name == "ng.md"
    assert "読み込み失敗" in (summary.failures[0].error or "")
    assert (tmp_path / "out" / "ok.xlsx").is_file()
