"""CLI の引数解釈と終了コード・サマリー出力のテスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

from md2xlsx.cli import main


def test_single_file_default_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "README.md"
    source.write_text("## 概要\n\n本文\n", encoding="utf-8")

    assert main([str(source)]) == 0
    assert (tmp_path / "README.xlsx").is_file()

    captured = capsys.readouterr()
    assert "Processed: 1" in captured.err
    assert "Succeeded: 1" in captured.err
    assert "Failed: 0" in captured.err
    assert "Warnings: 0" in captured.err


def test_output_directory_and_heading_level(tmp_path: Path) -> None:
    source = tmp_path / "spec.md"
    source.write_text("# T\n\n前文\n\n### 詳細\n\n本文\n", encoding="utf-8")
    out_dir = tmp_path / "xlsx"

    assert main([str(source), "--heading-level", "3", "--output", str(out_dir)]) == 0
    assert (out_dir / "spec.xlsx").is_file()


def test_recursive_option(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "api"
    docs.mkdir(parents=True)
    (tmp_path / "docs" / "README.md").write_text("## A\n\n本文\n", encoding="utf-8")
    (docs / "api.md").write_text("## B\n\n本文\n", encoding="utf-8")

    assert main([str(tmp_path / "docs"), "-r", "-o", str(tmp_path / "out")]) == 0
    assert (tmp_path / "out" / "README.xlsx").is_file()
    assert (tmp_path / "out" / "api" / "api.xlsx").is_file()


def test_invalid_heading_level(tmp_path: Path) -> None:
    source = tmp_path / "a.md"
    source.write_text("## A\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        main([str(source), "--heading-level", "7"])
    assert exc.value.code == 2


def test_missing_input(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(tmp_path / "missing.md")]) == 2
    assert "入力パスが存在しません" in capsys.readouterr().err


def test_directory_without_markdown(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "empty").mkdir()
    assert main([str(tmp_path / "empty")]) == 2
    assert "Markdown ファイルが見つかりません" in capsys.readouterr().err


def test_warning_is_reported(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "a.md"
    source.write_text("## 図\n\n![x](https://example.com/a.png)\n", encoding="utf-8")

    assert main([str(source)]) == 0
    captured = capsys.readouterr()
    assert "Warning:" in captured.err
    assert "Warnings: 1" in captured.err


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "md2xlsx" in capsys.readouterr().out
