"""シート名整形などの補助処理。"""

from __future__ import annotations

MAX_SHEET_NAME_LENGTH = 31

# Excel がシート名に使えない文字。
_FORBIDDEN_CHARS = set(r"[]:*?/\\")

FALLBACK_SHEET_NAME = "Sheet"


def sanitize_sheet_name(name: str) -> str:
    """Excel のシート名制約に合わせて文字列を整形する。

    禁止文字を除去し、先頭・末尾のアポストロフィと空白を落とし、
    31 文字を超える場合は切り詰める。空になる場合は既定名を返す。
    """
    cleaned = "".join(" " if char in _FORBIDDEN_CHARS else char for char in name)
    cleaned = cleaned.replace("\n", " ").replace("\t", " ")
    cleaned = " ".join(cleaned.split())
    cleaned = cleaned.strip("'")
    cleaned = cleaned.strip()
    if not cleaned:
        cleaned = FALLBACK_SHEET_NAME
    return cleaned[:MAX_SHEET_NAME_LENGTH]


def unique_sheet_name(name: str, used: set[str]) -> str:
    """既存シート名と重複しない名前を 31 文字以内で作る。"""
    base = sanitize_sheet_name(name)
    if base.casefold() not in used:
        used.add(base.casefold())
        return base

    index = 2
    while True:
        suffix = f"_{index}"
        trimmed = base[: MAX_SHEET_NAME_LENGTH - len(suffix)].rstrip()
        if not trimmed:
            trimmed = FALLBACK_SHEET_NAME[: MAX_SHEET_NAME_LENGTH - len(suffix)]
        candidate = f"{trimmed}{suffix}"
        if candidate.casefold() not in used:
            used.add(candidate.casefold())
            return candidate
        index += 1
