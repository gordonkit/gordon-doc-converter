# GordonKit ドキュメントコンバーター

[![CI](https://github.com/gordonkit/gordon-doc-converter/actions/workflows/ci.yml/badge.svg)](https://github.com/gordonkit/gordon-doc-converter/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![ライセンス：Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![開発ステータス：Pre-Alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](https://pypi.org/classifiers/)

[English](https://github.com/gordonkit/gordon-doc-converter/blob/main/README.md) ·
[繁體中文](https://github.com/gordonkit/gordon-doc-converter/blob/main/README.zh-TW.md) ·
[简体中文](https://github.com/gordonkit/gordon-doc-converter/blob/main/README.zh-CN.md)

[オンラインドキュメント](https://docs.gordonkit.com/)

GordonKit Document Converter は、DOCX をはじめとするドキュメント形式を PDF、HTML、
Markdown、画像などへ変換します。Python ライブラリ、CLI、HTTP API を提供し、組版には
Microsoft Word、LibreOffice、Pandoc、Gotenberg を利用します。

## 対応する変換フォーマット

| 入力 | DOCX | PDF | ODT | HTML | Markdown | YAML | JSON | 画像 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DOCX | × | Auto | LO | ✓ | ✓ | ✓ | ✓ | PDF |
| PDF | — | × | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| ODT | LO | LO | × | — | — | — | — | — |
| HTML | P | P+ | — | × | ✓ | ✓ | ✓ | — |
| Markdown | P | P+ | — | — | × | — | — | — |

`Auto` ポリシーに基づくエンジン選択 · `✓` 標準対応 · `LO` LibreOffice · `P` Pandoc ·
`P+` Pandoc と PDF backend · `PDF` 中間 PDF 経由 · `—` 非対応 ·
`×` 同一フォーマットのため変換しない

ページ画像は PNG または JPEG で出力できます。Markdown、HTML、YAML、JSON、画像ファイルは
DOCX / PDF ソースからの出力 artifact です。Markdown と HTML は PDF / DOCX への変換の入力
としても受け付けます。HTML はさらに、DOCX や PDF と同じセマンティック抽出によって
Markdown、YAML、JSON へ変換でき、この経路に外部エンジンは不要です。Markdown の変換先は
引き続き PDF と DOCX のみです。

DOCX から ODT、ODT から DOCX、ODT から PDF への変換には LibreOffice を使用します。DOCX の
変換は次のエンジンポリシーに従います。

- 対話的な Windows での DOCX から PDF：自動モードは Word COM を優先します。
- サーバーでの DOCX から PDF：自動モードは Gotenberg、次に LibreOffice を優先します。
- その他のホストでの DOCX から PDF：自動モードは LibreOffice を優先します。
- DOCX から HTML：既定はセマンティック抽出です。Word COM が利用できる Windows デスクトップ
    では、Word による組版のほうが視覚的な忠実度が高くなります。
- `--engine word-com` で Word COM による HTML 出力を、`--mode server` でセマンティック抽出を
    強制できます。
- エンジンの明示指定と strict モードでは決してフォールバックしません。
- エンジンによって組版結果が異なる場合があります。

ODT のサポート対象は ODF-CNS 15251 / ISO/IEC 26300 の Writer ドキュメントです。パッケージ
構造と内容の読み取り可能性を検証しますが、ピクセル単位で同一のラウンドトリップは保証
しません。

HTML / Markdown から PDF と DOCX への変換には Pandoc が必要です。PDF 出力にはさらに
`wkhtmltopdf` などの Pandoc PDF backend が必要です。`gordon-doc template report.html` で
編集可能な印刷向け A4 の出発点を作成し、`gordon-doc convert report.html --to pdf` または
`--to docx` で変換します。A4 横向きのレイアウトには `--orientation landscape` を使って
ください。

HTML から Markdown / YAML / JSON への変換はドキュメントを直接解析するため、エンジンは
不要です。

```console
gordon-doc convert report.html --to markdown --to yaml --to json
```

見出し、段落、リスト、表、リンク、`<ins>` / `<del>` の変更履歴、`<title>` / `<meta>` の
metadata は、DOCX や PDF と同じスキーマに正規化されます。インラインの `data:` 画像は
`<stem>.assets` ディレクトリのファイルになり、URL で参照される画像はリンクのまま残ります。
script、style、埋め込みオブジェクト要素は省略され、省略や非可逆な対応はすべて機械可読な
警告として報告されます。

## インターフェース

| インターフェース | 想定用途 |
| --- | --- |
| Python ライブラリ | 型付きの変換呼び出し、バッチ、エンジン診断を Python アプリケーションに組み込む |
| `gordon-doc` CLI | ターミナル、スクリプト、CI ジョブからローカル変換を実行する |
| HTTP API | 認証付きの変換リクエストをプライベートなサービス配備に送る |
| コンテナー profile | renderer の依存関係ごと分離したイメージで CLI や HTTP API を実行する |

どのインターフェースも同じ application service を経由し、構造化された結果、エンジン
ポリシー、診断情報を保持します。変換をどこから開始するかに合ったインターフェースを選び、
下のクイックスタートに従ってください。

## インストール

| インターフェース | インストール |
| --- | --- |
| Python ライブラリ | `python -m pip install gordon-doc-converter` |
| `gordon-doc` CLI | `gordon-doc-converter` に同梱。`gordon-doc version` で確認 |
| HTTP API | `python -m pip install "gordon-doc-converter[api]"` |
| コンテナー profile | Compose v2 付きの Docker Engine または Docker Desktop を導入。ローカルの Python パッケージは不要 |

組版や出力の機能には任意の extra が必要になる場合があります：
`gordon-doc-converter[images]`、`gordon-doc-converter[gotenberg]`、
`gordon-doc-converter[word]`。エンジンとプラットフォームの要件は
[オンラインドキュメント](https://docs.gordonkit.com/)を参照してください。

## クイックスタート

### Python ライブラリ

変換が Python アプリケーションの一部である場合はライブラリを使います。

```python
from pathlib import Path

from gordon_doc_converter import ConversionRequest, convert

request = ConversionRequest.from_source(Path("example.docx"))
result = convert(request)
if not result.success:
    raise RuntimeError(result.error.message if result.error else "conversion failed")
print(result.artifacts[0].path)
```

`convert()` は配備ポリシーに従ってエンジンを選択し、一時出力を検証し、検証に成功した後に
のみ PDF を公開します。エンジンの注入には `DocumentConversionService`、逐次で失敗を隔離
するバッチには `convert_batch()`、機能の診断には `probe_engines()` を使ってください。

### CLI

対話的な利用、シェルスクリプト、CI ジョブには CLI を使います。

```console
gordon-doc convert example.docx --output example.pdf
```

### コンテナー

ホストに Python や LibreOffice を入れたくない場合は、単一のコンテナーイメージを使います。
`cli` profile はカレントディレクトリを `/work` にマウントし、API key を必要としません。
次のコマンドは Bash でも PowerShell でも同じです。

```console
docker compose -f docker/compose.yaml --profile cli run --rm cli convert /work/example.docx --output /work/example.pdf
```

同じイメージ内の LibreOffice でプライベートな HTTP サービスを動かすには、API key を設定して
`standalone-lo` profile を起動します。`.env` ファイルは Bash でも PowerShell でも使えます。

```dotenv
GORDON_DOC_API_KEY=replace-with-a-strong-random-value
```

```console
docker compose -f docker/compose.yaml --env-file .env --profile standalone-lo up --build
```

同じ API イメージを共有 Docker network 上の別の Gotenberg renderer と組み合わせるには、
代わりに `gateway-gotenberg` を使います。`GORDON_DOC_GOTENBERG_URL` を設定すると Gotenberg が
API の明示的な既定エンジンになり、Gotenberg のリクエストが失敗しても暗黙に LibreOffice へ
フォールバックすることはありません。コンテナー profile、セキュリティ上の注意、smoke check は
[コンテナードキュメント](https://github.com/gordonkit/gordon-doc-converter/blob/main/docker/README.md)
に記載しています。タグ付きリリースでは `gordonkit/gordon-doc-converter` を Docker Hub に公開
します。必要なリポジトリ変数、secret、リリース手順もそこに記載しています。

### HTTP API

API を起動したら、元のファイル名と bearer token を添えて DOCX のバイト列を送信します。

```sh
curl --fail -H "Authorization: Bearer replace-me" \
    -H "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document" \
    -H "X-Filename: example.docx" --data-binary @example.docx \
    http://localhost:8000/conversions --output example.pdf
```

PowerShell では `Invoke-WebRequest -InFile ... -OutFile ...` を使います。LibreOffice と
Gotenberg の profile について、停止手順を含む Bash と PowerShell の完全な例は
[コンテナードキュメント](docker/README.md)にあります。

PDFium / Pillow によるラスタライズには `.[images]`、リモート adapter には `.[gotenberg]`、
FastAPI には `.[api]`、Windows COM には `.[word]` をインストールしてください。

## コマンドラインインターフェース

```console
gordon-doc doctor
gordon-doc engines --json
gordon-doc template report.html --orientation portrait
gordon-doc convert example.docx --output example.pdf
gordon-doc convert report.odt --to docx
gordon-doc convert example.docx --to odt --engine libreoffice
gordon-doc convert report.html --to pdf --orientation landscape
gordon-doc convert report.html --to docx
gordon-doc convert example.pdf --to images --dpi 144
gordon-doc convert example.docx --to markdown --to html --to yaml --to json
gordon-doc convert example.docx --to html --engine word-com
gordon-doc convert example.docx --to yaml --metadata layout --progress
gordon-doc compare expected.pdf actual.pdf --diff-dir differences --json
gordon-doc batch one.docx two.docx --output-dir converted --json
gordon-doc version
```

エンジンを厳密に明示指定するには `--engine word-com`、`--engine libreoffice`、または設定済みの
`--engine gotenberg` を使います。DOCX から HTML では、`--engine word-com` が Word COM で組版し、
省略するか `--mode server` を使うとセマンティック抽出になります。変換オプションにはこのほか
`--mode`、`--revisions`、`--comments`、`--metadata`、`--timeout`、`--overwrite`、画像の
フォーマット / 品質 / ページ選択、任意の `--gotenberg-url` があります。ページ画像は
`<stem>.pages/0001.png`、セマンティック artifact は `.md`、`.html`、`.yaml`、`.json`、共有の
`.assets/`、および注釈がある場合は sidecar を使います。
YAML と JSON は、下流のインデックス作成を想定したバージョン付きの見出し / 段落 / リスト / 表
スキーマを共有します。`--to json` はそのドキュメント artifact を書き出し、これとは別の
`--json` フラグは自動化向けに CLI の結果契約を出力します。

PDF ソースにはセマンティックなタグがないため、block はレイアウトから推定されます。
コンバーターはグリフ位置からテキスト行を再構成し、繰り返される柱やフッターを取り除き、
PDF の outline、相対的なフォントサイズ、太さ、間隔、序数マーカーから見出しを分類します。
マーカーは体系、スタイル、単位ごとに解析され、アラビア数字、ローマ数字、ラテン文字、丸数字、
CJK 数字に対応します。そのため見出しレベルは、フォントサイズだけでなくドキュメント自身の
番号付けに従います。推定はヒューリスティックであり、読み順は推定値として報告され続けます。

metadata detail は `none`、`basic`（既定の許可リスト済みドキュメントプロパティ）、`layout` の
いずれかです。PDF の物理ページは 1 起点で、提供元として `pypdf` を示します。DOCX の物理ページと
表示上のページラベルは、layout provider を設定するまで capability を明示的に unavailable として
省略します。コンバーターは推定したページ番号を正確な値として提示しません。

構造化 artifact にはフォーマットをまたぐ逆引き locator が含まれます。`source.sha256` はソース
ファイルを厳密に特定し、各 `source_anchor` には検証用に正規化済みコンテンツの SHA-256 が
含まれます。DOCX の block は `word/document.xml` の element（表セルは行 / セル単位）を指し、
PDF の block は 1 起点の物理ページを指します。PDF の anchor は現時点で bounding box ではなく
ページを特定します。将来の layout provider は DOCX の locator 契約を変えずにページ座標を追加
できます。任意の locator フィールドは null としてシリアライズされるのではなく省略されます。

```yaml
schema_version: "1.3"
source: {format: "pdf", sha256: "<source-file-sha256>"}
root_blocks: [{
    id: "block-000001",
    source_order: 0,
    kind: "paragraph",
    physical_page_number: 1,
    text: "Page text",
    source_anchor: {
        locator: "pdf-page",
        page_number: 1,
        content_sha256: "<normalized-content-sha256>"
    }
}]
```

バイトオフセットは意図的に安定した locator 契約に含めていません。DOCX のオフセットは圧縮された
ZIP メンバー内を指し、Office がパッケージを書き換えたり再圧縮したりすると変わります。PDF の
オフセットはシリアライズされたオブジェクトやストリームを指し、最適化、線形化、増分保存の後に
変わります。代わりにソースのフィンガープリントと、OOXML の element path または PDF のページ
anchor を使ってください。バイトオフセットは将来、権威を持たない診断用のヒントとしてのみ追加
される可能性があります。

`convert` と `batch` は、対話的なターミナルで変換の段階を自動的に表示します。進捗は stderr にのみ
書き出され、`--json` やリダイレクトされた出力では自動的に無効になります。自動判定を上書きする
には `--progress` または `--no-progress` を使ってください。

安定した exit code は、成功が `0`、入力が無効または出力が既に存在する場合が `2`、エンジンや機能が
利用できない場合が `3`、変換の失敗・タイムアウト・出力なしが `4`、PDF 検証の失敗が `5` です。

Microsoft Word と LibreOffice は同じドキュメントを異なる形で組版することがあります。本
プロジェクトは選択したエンジンとフォールバックの理由を報告しますが、同一の出力を保証したり、
明示的に選択されたエンジンを暗黙に切り替えたりすることはありません。

## 開発環境の構築

```console
uv sync --dev
uv sync --dev --all-extras
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
uv build
```

`soffice` が見つからない場合、LibreOffice の実機統合テストはスキップされます。LibreOffice を
インストールしたホストでは `uv run pytest -m integration tests/integration/libreoffice` で
実行できます。

Microsoft Word の統合テストには、Windows、正規ライセンスの Microsoft Word、`word` 任意依存
パッケージが必要です。管理された対話的環境でのみ、`uv sync --dev --extra word --locked` の後に
`uv run pytest -m integration tests/integration/word_com` を実行してください。

静的ドキュメントサイトは、React、Vite、Tailwind CSS、同梱の Heroicons と Swagger UI で構築
しています。`docs/` を再ビルドする前に API とフロントエンドの依存パッケージをインストールして
ください。ビルド時に現在の FastAPI 契約が自動的に `openapi.json` へエクスポートされます。

```console
uv sync --dev --extra api --locked
npm ci
npm run build
```

生成されたサイトは `docs/` 以下で自己完結しており、
[docs.gordonkit.com](https://docs.gordonkit.com/) で公開されています。ビルドは
`/en/<topic>/`、`/zh-TW/<topic>/`、`/zh-CN/<topic>/`、`/ja/<topic>/` にインデックス可能な
ページを生成し、
ローカライズされた metadata、canonical、言語 alternate、構造化データ、sitemap、robots の指示を
含みます。サイトは英語・繁体中文・简体中文・日本語の言語ドロップダウンに加えて、検索、レスポンシブ
レイアウト、ライト / ダークテーマにも対応します。生成された API 契約は `docs/openapi.json`、
読み取り専用の Swagger UI は `docs/swagger/index.html` にあります。エクスポートが古くなって
いないかは `npm run openapi:check` で確認できます。

技術リファレンス、ユーザーガイド、互換性に関する注意、開発規約は
[英語ドキュメント](https://docs.gordonkit.com/en/overview/)、
[繁体中文ドキュメント](https://docs.gordonkit.com/zh-TW/overview/)、
[简体中文ドキュメント](https://docs.gordonkit.com/zh-CN/overview/)、
[日本語ドキュメント](https://docs.gordonkit.com/ja/overview/)から参照できます。

## ライセンス

Apache License 2.0 を採用しています。詳細は [LICENSE](LICENSE)、[NOTICE](NOTICE)、
[THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt) を参照してください。
