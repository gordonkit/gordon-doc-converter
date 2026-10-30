# 互換性ポリシー

[English](COMPATIBILITY.md) · [繁體中文](COMPATIBILITY.zh-TW.md) · [简体中文](COMPATIBILITY.zh-CN.md)

> **リリース候補。** このポリシーは `1.0.0` から有効になります。`1.0.0rcN` のリリース候補は
> すでに以下のインターフェースを提供していますが、テストで問題が見つかった場合は後続の候補で
> 変わる可能性があり、そうした変更はすべて `CHANGELOG.md` に記録されます。本書は英語版
> `COMPATIBILITY.md` の翻訳であり、内容に食い違いがある場合は英語版が優先されます。

GordonKit Document Converter は [Semantic Versioning](https://semver.org/) に従います。
`1.0.0` 以降、以下の公開契約を破るリリースでは major バージョンを上げます。Minor
リリースは互換性を壊さずに機能を追加し、patch リリースはバグとセキュリティ問題を修正します。

## 公開契約

### Python ライブラリ

公開 Python API は、`gordon_doc_converter.__all__` がエクスポートする名前と、そのドキュメント
に記載された引数、フィールド、メソッド、戻り値の型に限られます。

- 変換のエントリーポイント：`convert`、`convert_batch`、`probe_engines`、
  `DocumentConversionService`
- リクエストと結果のモデル：`ConversionRequest`、`ConversionOptions`、`ConversionResult`、
  `ArtifactResult`、`ArtifactItem`、`EngineProbeResult`、`PdfValidationResult`、
  `NormalizedAnnotation`、`AnnotationAnchor`、`PageImageArtifact`
- 列挙型：`SourceFormat`、`ArtifactType`、`ArtifactStatus`、`EngineName`、`DeploymentMode`、
  `RevisionMode`、`CommentMode`、`AnnotationKind`、`PageImageFormat`、`ErrorCode`
- エラー：`ConversionError`
- ページ画像と比較：`PdfRasterizer`、`PdfiumPageRenderer`、`RasterOptions`、
  `PdfComparisonService`、`PdfComparisonReport`、`PillowImageDiffer`

`gordon_doc_converter.engines`、`content`、`process`、`api`、`cli` を含むそれ以外の
モジュールと、アンダースコアで始まる名前はすべて内部実装であり、どのリリースでも変わる
可能性があります。

互換性のある変更には、`__all__` への名前の追加、既定値付きの keyword 引数の追加、モデルへの
任意フィールドの追加、列挙型へのメンバーの追加が含まれます。列挙値で分岐する呼び出し側は、
未知のメンバーにも対処してください。

### コマンドラインインターフェース

- `doctor`、`engines`、`template`、`convert`、`compare`、`batch`、`version` の各コマンドと、
  ドキュメントに記載されたオプションおよび引数。
- Exit code：`0` 成功、`2` 無効な入力または既存の出力、`3` エンジンまたは機能が利用不可、
  `4` 変換の失敗・タイムアウト・出力なし、`5` PDF 検証の失敗。新しい失敗の種類には新しい
  code を割り当て、既存の code の意味は変えません。
- `--json` が出力するドキュメント。フィールドは追加されることがありますが、既存のフィールドが
  削除、改名、型変更されることはありません。

人が読むためのテキスト出力、stderr への進捗表示、ヘルプテキストは契約に含まれません。

### エラーコードと警告コード

- `ErrorCode` の値は安定しています。Minor リリースで新しいコードが追加されることがあります。
- `ENGINE_FALLBACK` や `LAYOUT_NOT_PRESERVED` などの警告の `code` 値は、一度リリースされれば
  安定します。Minor リリースで警告が追加されることがあるため、呼び出し側は認識できない
  コードを無視してください。
- エラーと警告の `message` は人が読むためのものであり、どのリリースでも変わる可能性があります。

### 構造化 YAML、JSON、JSON Lines artifact

構造化スキーマは、パッケージのバージョンとは独立した独自の `schema_version` を持ちます。

- スキーマの minor バージョン（`1.5` から `1.6` など）では、任意フィールド、ブロックの種類、
  locator の種類、レコードの種類の追加だけを行います。それらを使わないドキュメントは、以前と
  まったく同じようにシリアライズされます。
- フィールドの削除、改名、型や意味の変更には、スキーマの major バージョン（`1.x` から
  `2.0`）の更新が必要であり、パッケージの major リリースでのみ行います。
- 任意フィールドは `null` としてシリアライズせず、省略します。読み取り側は未知のフィールドと
  ブロックの種類を無視してください。
- バイトオフセットは locator の契約に含まれません。理由は README を参照してください。

### レンダリング出力

PDF、DOCX、ODT、HTML、Markdown、ページ画像の出力は、バイト単位の一致を保証しません。エンジンの
バージョン、フォント、writer の修正によって、正確なバイト列やレイアウトは変わります。これらの
ファイル名とディレクトリ構成（`<stem>.pages/0001.png`、`<stem>.assets/`、注釈の sidecar）は
契約に含まれます。

### HTTP API

バージョン付きのルートは `POST /v1/conversions`、`GET /v1/engines`、`GET /v1/version` です。
プローブの `GET /live` と `GET /ready` はバージョンなしのままなので、コンテナのヘルスチェックを
変更する必要はありません。

- エクスポートされた OpenAPI 契約（`docs/openapi.json`）に記載されたパス、リクエストヘッダー、
  クエリパラメーター、ステータスコード、エラー本文がこのポリシーの対象です。
- 互換性を壊す変更は `/v2/` などの新しいプレフィックスで提供し、少なくとも 1 つの minor
  リリースの間は `/v1/` と並行して提供したうえで、major リリースで `/v1/` を削除します。
- `GORDON_DOC_API_KEY` と `GORDON_DOC_GOTENBERG_URL` は安定した設定名です。
- `0.12.0` で非推奨になったプレフィックスなしのエイリアス `/conversions`、`/engines`、
  `/version` は、`1.0.0rc1` から削除されています。

### コンテナイメージ

- イメージ名、タグの規則（`X.Y.Z`、`X.Y`、`latest`）、公開プラットフォーム（`linux/amd64` と
  `linux/arm64`）、既定の CLI entrypoint、`api` 引数、Compose profile 名は契約に含まれます。
- `1.0.0rc1` のようなリリース候補は完全なバージョンのタグだけで公開され、`X.Y` と `latest` は
  最後の正式リリースを指したままです。
- Minor リリースでイメージ内のエンジンが増えることがあります。エンジンや、イメージが提供する
  変換経路を削除することは、互換性を壊す変更です。
- ベースイメージと、LibreOffice やその他のシステムパッケージのバージョンは契約に含まれません。

## サポートするプラットフォーム

`.github/workflows/ci.yml` の `quality` job は、以下のすべての組み合わせで単体テスト一式を
実行します。この一覧はその設定と一致させる必要があります。

- Python：3.12、3.13、3.14。ある Python バージョンのサポートは minor リリースでのみ終了し、
  そのバージョンのサポート期限が切れた後に限ります。
- OS：Linux、Windows、macOS。Microsoft Word COM は Windows でのみ利用できます。実際の
  エンジンを使う統合テストは、Linux（LibreOffice）と管理された Windows ホスト（Word）で
  実行します。
- エンジン：各エンジンのバージョンへの対応はベストエフォートです。Microsoft Word と
  LibreOffice の組版結果が同一になることは決して保証しません。

## 非推奨化の手順

1. 公開契約は minor リリースで非推奨とし、`CHANGELOG.md` に `Deprecated` の項目を追加します。
   Python API の場合は、代替手段を示す `DeprecationWarning` も発行します。
2. 非推奨となった契約は、少なくとも次の minor リリースまでは動作し続け、次の major リリースで
   のみ削除されます。
3. 唯一の例外はセキュリティ修正です。契約を維持するとユーザーが危険にさらされる場合は、minor
   または patch リリースで変更することがあり、その変更は `Security` に明記します。
