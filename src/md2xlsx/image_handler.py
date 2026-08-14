"""画像パスの解決と、Excel へ埋め込む際のサイズ決定。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from PIL import Image as PilImage
from PIL import UnidentifiedImageError

# 埋め込み時の最大サイズ（ピクセル）。これに収まるよう縦横比を維持して縮小する。
MAX_IMAGE_WIDTH = 480
MAX_IMAGE_HEIGHT = 360

SUPPORTED_FORMATS = frozenset({"PNG", "JPEG", "GIF"})


@dataclass
class ResolvedImage:
    """画像 1 件の解決結果。"""

    path: Path
    width: int
    height: int


class ImageError(Exception):
    """画像を埋め込めない場合に送出する。"""


def is_remote(src: str) -> bool:
    """HTTP/HTTPS などの外部画像かどうか。"""
    scheme = urlparse(src).scheme.lower()
    return scheme in ("http", "https", "ftp", "ftps")


def is_data_uri(src: str) -> bool:
    """data: スキームの埋め込み画像かどうか。"""
    return urlparse(src).scheme.lower() == "data"


def scale_to_fit(
    width: int,
    height: int,
    max_width: int = MAX_IMAGE_WIDTH,
    max_height: int = MAX_IMAGE_HEIGHT,
) -> tuple[int, int]:
    """縦横比を維持して最大サイズへ収める。小さい画像は拡大しない。"""
    if width <= 0 or height <= 0:
        return max_width, max_height
    ratio = min(max_width / width, max_height / height, 1.0)
    return max(1, int(width * ratio)), max(1, int(height * ratio))


def resolve_image(src: str, base_dir: Path) -> ResolvedImage:
    """ローカル画像を解決し、表示サイズを算出する。

    外部画像やダウンロードが必要な参照は扱わず ImageError を送出する。
    """
    if is_remote(src) or is_data_uri(src):
        raise ImageError("外部画像は対象外です")

    raw_path = unquote(urlparse(src)._replace(fragment="", query="").path or src)
    candidate = Path(raw_path)
    path = candidate if candidate.is_absolute() else (base_dir / candidate)

    if not path.is_file():
        raise ImageError(f"画像ファイルが見つかりません: {src}")

    try:
        with PilImage.open(path) as image:
            image_format = (image.format or "").upper()
            width, height = image.size
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ImageError(f"画像を読み込めません: {src}") from error

    if image_format not in SUPPORTED_FORMATS:
        raise ImageError(f"未対応の画像形式です ({image_format or 'unknown'}): {src}")

    display_width, display_height = scale_to_fit(width, height)
    return ResolvedImage(path=path, width=display_width, height=display_height)
