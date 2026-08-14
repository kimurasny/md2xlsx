"""日本語ファイル名・ディレクトリ名・画像名のテスト。"""

from __future__ import annotations

from pathlib import Path

from conftest import column_values, open_workbook

from md2xlsx.converter import convert


def test_japanese_paths_and_contents(tmp_path: Path, make_png) -> None:
    docs = tmp_path / "資料" / "設計"
    docs.mkdir(parents=True)
    make_png(docs / "画像" / "構成図.png", size=(200, 100))
    (docs / "仕様書.md").write_text(
        "# 仕様書\n\nはじめに。\n\n## 概要\n\n日本語の本文です。\n\n![構成図](./画像/構成図.png)\n",
        encoding="utf-8",
    )

    summary = convert(tmp_path / "資料", output=tmp_path / "出力", recursive=True)

    assert summary.succeeded == 1
    assert summary.warning_count == 0
    output = tmp_path / "出力" / "設計" / "仕様書.xlsx"
    assert output.is_file()

    workbook = open_workbook(output)
    assert workbook.sheetnames == ["Introduction", "概要"]
    assert column_values(workbook["Introduction"]) == ["仕様書", "はじめに。"]
    assert "日本語の本文です。" in column_values(workbook["概要"])
    assert len(workbook["概要"]._images) == 1
