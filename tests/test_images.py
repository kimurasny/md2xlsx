"""画像の埋め込み・エラー処理・Web 画像のテスト。"""

from __future__ import annotations

from pathlib import Path

from conftest import column_values, image_size_px, open_workbook

from md2xlsx.converter import convert_file
from md2xlsx.image_handler import scale_to_fit


def test_local_image_is_embedded(write_md, make_png, tmp_path: Path) -> None:
    make_png(tmp_path / "images" / "architecture.png", size=(1200, 800))
    source = write_md(
        "README.md",
        "## 構成\n\nシステム構成は以下です。\n\n"
        "![構成図](./images/architecture.png)\n\n詳細を説明します。\n",
    )
    output = tmp_path / "out.xlsx"
    result = convert_file(source, output)

    assert result.image_count == 1
    assert result.warnings == []

    workbook = open_workbook(output)
    sheet = workbook["構成"]
    assert len(sheet._images) == 1
    embedded = sheet._images[0]
    assert image_size_px(embedded) == scale_to_fit(1200, 800)

    values = column_values(sheet)
    text_index = values.index("システム構成は以下です。")
    assert values.index("詳細を説明します。") > text_index
    assert any(value.startswith("図: 構成図") for value in values)

    anchor_row = embedded.anchor._from.row + 1
    assert sheet.row_dimensions[anchor_row].height is not None


def test_missing_image_reports_placeholder(write_md, tmp_path: Path) -> None:
    source = write_md("a.md", "## 図\n\n![図](./images/foo.png)\n")
    output = tmp_path / "a.xlsx"
    result = convert_file(source, output)

    assert result.succeeded
    assert result.image_count == 0
    assert len(result.warnings) == 1
    values = column_values(open_workbook(output)["図"])
    assert "[Image unavailable: ./images/foo.png]" in values


def test_web_image_is_not_downloaded(write_md, tmp_path: Path) -> None:
    url = "https://example.com/image.png"
    source = write_md("a.md", f"## 図\n\n![image]({url})\n")
    output = tmp_path / "a.xlsx"
    result = convert_file(source, output)

    assert result.image_count == 0
    assert len(result.warnings) == 1
    values = column_values(open_workbook(output)["図"])
    assert any(url in value and "External image" in value for value in values)


def test_corrupted_image_does_not_fail_workbook(write_md, tmp_path: Path) -> None:
    broken = tmp_path / "images" / "broken.png"
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_bytes(b"not really a png")
    source = write_md("a.md", "## 図\n\n![壊れ](./images/broken.png)\n")
    output = tmp_path / "a.xlsx"
    result = convert_file(source, output)

    assert result.succeeded
    assert len(result.warnings) == 1
    assert "[Image unavailable: ./images/broken.png]" in column_values(open_workbook(output)["図"])


def test_unsupported_format_is_reported(write_md, tmp_path: Path) -> None:
    from PIL import Image as PilImage

    bmp = tmp_path / "images" / "diagram.bmp"
    bmp.parent.mkdir(parents=True, exist_ok=True)
    PilImage.new("RGB", (10, 10), color=(0, 0, 0)).save(bmp)
    source = write_md("a.md", "## 図\n\n![bmp](./images/diagram.bmp)\n")
    output = tmp_path / "a.xlsx"
    result = convert_file(source, output)

    assert result.succeeded
    assert result.image_count == 0
    assert len(result.warnings) == 1


def test_small_image_is_not_enlarged(write_md, make_png, tmp_path: Path) -> None:
    make_png(tmp_path / "small.png", size=(40, 30))
    source = write_md("a.md", "## 図\n\n![小](./small.png)\n")
    output = tmp_path / "a.xlsx"
    convert_file(source, output)

    embedded = open_workbook(output)["図"]._images[0]
    assert image_size_px(embedded) == (40, 30)


def test_multiple_images_keep_order(write_md, make_png, tmp_path: Path) -> None:
    make_png(tmp_path / "one.png", size=(100, 50))
    make_png(tmp_path / "two.png", size=(100, 50))
    source = write_md("a.md", "## 図\n\n![一](./one.png)\n\n間の文章\n\n![二](./two.png)\n")
    output = tmp_path / "a.xlsx"
    result = convert_file(source, output)

    assert result.image_count == 2
    sheet = open_workbook(output)["図"]
    rows = [image.anchor._from.row for image in sheet._images]
    assert rows == sorted(rows)
    text_row = next(
        row - 1
        for row in range(1, sheet.max_row + 1)
        if sheet.cell(row=row, column=1).value == "間の文章"
    )
    assert rows[0] < text_row < rows[1]


def test_gif_and_jpeg_are_supported(write_md, tmp_path: Path) -> None:
    from PIL import Image as PilImage

    PilImage.new("RGB", (60, 40), color=(200, 10, 10)).save(tmp_path / "anim.gif")
    PilImage.new("RGB", (60, 40), color=(10, 200, 10)).save(tmp_path / "photo.jpg")
    source = write_md("a.md", "## 図\n\n![gif](./anim.gif)\n\n![jpg](./photo.jpg)\n")
    output = tmp_path / "a.xlsx"
    result = convert_file(source, output)

    assert result.image_count == 2
    assert result.warnings == []
    assert len(open_workbook(output)["図"]._images) == 2


def test_scale_to_fit_keeps_aspect_ratio() -> None:
    width, height = scale_to_fit(1000, 500, max_width=480, max_height=360)
    assert width == 480
    assert height == 240
