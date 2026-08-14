"""シート名制約（禁止文字 / 31 文字 / 重複）のテスト。"""

from __future__ import annotations

from md2xlsx.utils import MAX_SHEET_NAME_LENGTH, sanitize_sheet_name, unique_sheet_name


def test_forbidden_characters_are_removed() -> None:
    name = sanitize_sheet_name("API[v1]:/get*?\\list")
    for char in "[]:*?/\\":
        assert char not in name


def test_empty_name_falls_back() -> None:
    assert sanitize_sheet_name("   ") == "Sheet"
    assert sanitize_sheet_name("[]") == "Sheet"


def test_long_name_is_truncated() -> None:
    name = sanitize_sheet_name("あ" * 60)
    assert len(name) == MAX_SHEET_NAME_LENGTH


def test_duplicates_get_suffix() -> None:
    used: set[str] = set()
    assert unique_sheet_name("API", used) == "API"
    assert unique_sheet_name("API", used) == "API_2"
    assert unique_sheet_name("API", used) == "API_3"


def test_duplicate_long_names_stay_within_limit() -> None:
    used: set[str] = set()
    long_title = "z" * 40
    first = unique_sheet_name(long_title, used)
    second = unique_sheet_name(long_title, used)
    assert len(first) == MAX_SHEET_NAME_LENGTH
    assert len(second) <= MAX_SHEET_NAME_LENGTH
    assert first != second
    assert second.endswith("_2")
