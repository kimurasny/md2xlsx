# md2xlsx

Markdown ファイルを、業務文書として読みやすい Excel（`.xlsx`）へ変換する CLI ツールです。

- 単一 Markdown ファイルの変換
- ディレクトリ内の一括変換（サブディレクトリの再帰処理に対応）
- Markdown 見出し単位での Excel シート分割
- Markdown テーブルの Excel セルへの展開
- ローカル画像の Excel への埋め込み（Web 画像はダウンロードしません）

## 動作環境

- Python 3.11 以上
- 依存ライブラリ
  - [markdown-it-py](https://github.com/executablebooks/markdown-it-py)（Markdown の構造解析）
  - [openpyxl](https://openpyxl.readthedocs.io/)（XLSX 生成）
  - [Pillow](https://python-pillow.org/)（画像サイズ取得・形式判定）

## インストール

```bash
python -m venv .venv
source .venv/bin/activate        # Windows は .venv\Scripts\activate
pip install -e .
```

開発用（テスト・Lint）を含める場合:

```bash
pip install -e ".[dev]"
```

## 実行方法

```bash
md2xlsx <input> [options]
```

`<input>` には Markdown ファイル、またはディレクトリを指定します。
インストールせずに実行する場合は `python -m md2xlsx.cli <input>` でも同じ動作になります。

## CLI オプション

| オプション | 説明 |
| --- | --- |
| `-r`, `--recursive` | ディレクトリ指定時、サブディレクトリまで再帰的に `.md` を探索する |
| `-l`, `--heading-level <1-6>` | Excel シートを分割する見出しレベル（既定: `2`） |
| `-o`, `--output <path>` | XLSX の出力先（ファイルまたはディレクトリ） |
| `--intro-sheet-name <name>` | 最初の対象見出しより前の内容を格納するシート名（既定: `Introduction`） |
| `-h`, `--help` | ヘルプを表示する |
| `--version` | バージョンを表示する |

## 使用例

```bash
md2xlsx README.md
md2xlsx README.md --heading-level 3
md2xlsx ./docs --recursive
md2xlsx ./docs --recursive --heading-level 2 --output ./xlsx
```

`-o` を省略した場合、単一ファイル指定では入力と同じ場所に、ディレクトリ指定では入力ディレクトリ内に XLSX を出力します。

### ディレクトリ一括変換

Markdown ファイル 1 つにつき XLSX ファイル 1 つを生成します。

```text
input/                      output/
├── aaa.md        →         ├── aaa.xlsx
└── bbb.md                  └── bbb.xlsx
```

### recursive

既定では、指定したディレクトリ直下の Markdown のみを処理します。

```bash
md2xlsx ./docs
```

`--recursive` を指定すると下位ディレクトリまで探索し、入力ディレクトリからの相対構造を出力先でも維持します。

```text
docs/                       output/
├── README.md      →        ├── README.xlsx
├── api/                    ├── api/
│   └── api.md              │   └── api.xlsx
└── database/               └── database/
    └── database.md             └── database.xlsx
```

拡張子は `.md` / `.MD` のように大文字小文字を区別せず判定します（`.markdown` / `.mdown` / `.mkd` も対象）。

### heading-level

指定した見出しレベルを境界としてシートを分割します（既定は `2`、つまり `##`）。

```markdown
# システム仕様書

この文書について説明します。

## 概要

...

## API

...
```

上記を既定設定で変換すると、次のシートが生成されます。

```text
Introduction / 概要 / API
```

- 最初の対象見出しより前のコンテンツは `Introduction` シートへ格納します。
- そこに実質的なコンテンツが無い場合、`Introduction` シートは作成しません。
- 分割対象より深い / 浅い見出しは、本文として A 列に配置します。

## Markdown → Excel 変換ルール

| Markdown | Excel での表現 |
| --- | --- |
| 見出し `#`〜`######` | A 列に配置。レベルに応じたフォントサイズ・太字（レベル 1〜2 は背景色付き） |
| 段落 | A 列に 1 セル 1 段落、折り返し表示 |
| 太字 / 斜体 | セル内リッチテキストとして太字・斜体を保持 |
| インラインコード | セル内リッチテキストで等幅フォント |
| 箇条書き | `・` プレフィックス付きで 1 項目 1 行（ネストはインデント） |
| 番号付きリスト | `1.` `2.` … のプレフィックス付きで 1 項目 1 行 |
| テーブル | Excel の行・列へ展開（下記参照） |
| コードブロック | `[code: 言語]` ラベル＋1 行 1 セル、等幅フォント・背景色付き（折り返しなし） |
| リンク | `ラベル (URL)` の形式でテキスト化 |
| 引用 | `>` プレフィックス付きの斜体・グレー表示 |
| 水平線 | 罫線相当の記号行 |
| ローカル画像 | 画像として埋め込み（下記参照） |

既定フォントは本文が **メイリオ（Meiryo）**、コードブロックとインラインコードが Consolas です（Workbook の Normal スタイルにもメイリオを設定するため、変換後に利用者が入力するセルも同じフォントになります）。

本文は Markdown の読み順を保ったまま A 列へ上から配置します。空行数を Markdown と厳密に一致させることはせず、読みやすさを優先してブロック間に空行を挟みます。

### Markdown テーブルの扱い

テーブルは 1 セルに Markdown 文字列として入れず、行・列へ展開します。

```markdown
| Name | Type | Required |
|------|------|----------|
| id | string | Yes |
```

```text
     A       B         C
1  Name    Type     Required     ← 太字・背景色・罫線
2  id      string   Yes          ← 罫線
```

ヘッダー行は太字と青系の背景色（`8DB4E2`）で本文と区別し、テーブル全体へ黒（`000000`）の細罫線を設定します。テーブルの後続コンテンツは、その下の行から続けて配置します。

罫線はテーブルにのみ設定し、シートの背景のグリッド線は非表示にしているため、Excel 上ではテーブルの枠線だけが見えます。

### ローカル画像の扱い

- 画像パスは、Markdown ファイルが存在するディレクトリを基準に相対解決します。
- 対応形式は PNG / JPEG / JPG / GIF です。
- Markdown 内の出現順を維持して配置し、直前・直後の文章との位置関係を保ちます。
- 巨大な画像は縦横比を維持して最大 480 × 360 ピクセルへ縮小します（小さい画像は拡大しません）。
- 画像を貼り付けた行の行高を画像サイズに合わせ、後続コンテンツと重ならないようにします。
- `alt` テキストがある場合は、画像の下に `図: <alt>` のキャプションを出力します。

### Web 画像は対象外

`http` / `https` などの外部画像はダウンロードしません（Web アクセスを一切行いません）。
該当箇所には次のような情報をセルへ記載し、警告として出力したうえで変換を継続します。

```text
[External image (not downloaded): https://example.com/image.png]
```

### 画像エラー時の挙動

ファイルが存在しない、破損している、未対応形式、埋め込みに失敗した場合でも Workbook 全体の変換は失敗させません。
該当箇所へ次のように記載し、警告を出力します。

```text
[Image unavailable: ./images/foo.png]
```

## エラーハンドリング

複数ファイル処理中に 1 ファイルが失敗しても、残りのファイルの処理を継続し、最後にサマリーを標準エラー出力へ表示します。

```text
Processed: 10
Succeeded: 9
Failed: 1
Warnings: 3
```

失敗したファイルはパスとエラー内容を、警告は対象ファイルと内容を併せて表示します。
終了コードは、全ファイル成功で `0`、1 件以上失敗で `1`、入力指定が不正な場合は `2` です。

## 文字コード

入力は UTF-8 の Markdown を前提とします。日本語のファイル名・ディレクトリ名・見出し・本文・画像ファイル名を扱えます。

## 制約事項

- Excel 上で Markdown を完全再現することは目的としていません（情報構造の保持と可読性を優先します）。
- Web 画像・data URI 画像は埋め込まず、注記のみを出力します。
- GIF はアニメーションを保持せず、静止画として埋め込みます。
- 取り消し線は斜体として表現します。
- 既定フォントのメイリオが存在しない環境（macOS / Linux など）では、Excel 側の代替フォントで表示されます。
- HTML ブロック・HTML インラインはテキストとしてそのまま出力します。
- シート名は Excel の制約（31 文字以内、禁止文字なし、重複不可）に合わせて自動調整します（重複時は `API`、`API_2`、`API_3` の形式）。
- 脚注・定義リストなどの CommonMark 拡張は未対応です。

## テスト実行方法

```bash
pip install -e ".[dev]"
pytest
```

Lint を実行する場合:

```bash
ruff check .
```
