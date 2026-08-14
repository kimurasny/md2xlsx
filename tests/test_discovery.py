"""入力探索（単一ファイル / ディレクトリ / recursive）のテスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

from md2xlsx.discovery import find_markdown_files


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "README.md").write_text("# a\n", encoding="utf-8")
    (tmp_path / "docs" / "UPPER.MD").write_text("# b\n", encoding="utf-8")
    (tmp_path / "docs" / "note.txt").write_text("x", encoding="utf-8")
    (tmp_path / "docs" / "api").mkdir()
    (tmp_path / "docs" / "api" / "api.md").write_text("# c\n", encoding="utf-8")
    return tmp_path / "docs"


def test_single_file(tree: Path) -> None:
    files = find_markdown_files(tree / "README.md", recursive=False)
    assert files == [tree / "README.md"]


def test_directory_non_recursive(tree: Path) -> None:
    files = find_markdown_files(tree, recursive=False)
    names = sorted(path.name for path in files)
    assert names == ["README.md", "UPPER.MD"]


def test_directory_recursive(tree: Path) -> None:
    files = find_markdown_files(tree, recursive=True)
    names = sorted(path.name for path in files)
    assert names == ["README.md", "UPPER.MD", "api.md"]


def test_missing_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        find_markdown_files(tmp_path / "nope", recursive=False)
