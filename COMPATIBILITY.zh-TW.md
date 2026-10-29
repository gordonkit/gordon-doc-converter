# 相容性政策

[English](COMPATIBILITY.md) · [简体中文](COMPATIBILITY.zh-CN.md) · [日本語](COMPATIBILITY.ja.md)

> **草稿。** 本政策自 `1.0.0` 起生效。在此之前，依 Semantic Versioning 的規定，任何 `0.x`
> minor 版本仍可能變動下列介面，每項變動都會記錄在 `CHANGELOG.md`。本文為英文版
> `COMPATIBILITY.md` 的翻譯，兩者有出入時以英文版為準。

GordonKit Document Converter 遵循 [Semantic Versioning](https://semver.org/)。自 `1.0.0`
起，破壞下列公開契約的版本會提升 major 版本號。Minor 版本只新增行為而不破壞相容性；
patch 版本修正錯誤與安全問題。

## 公開契約

### Python Library

公開的 Python API 恰好是 `gordon_doc_converter.__all__` 匯出的名稱，以及其文件記載的參數、
欄位、方法與回傳型別：

- 轉換進入點：`convert`、`convert_batch`、`probe_engines` 與 `DocumentConversionService`；
- 請求與結果模型：`ConversionRequest`、`ConversionOptions`、`ConversionResult`、
  `ArtifactResult`、`ArtifactItem`、`EngineProbeResult`、`PdfValidationResult`、
  `NormalizedAnnotation`、`AnnotationAnchor` 與 `PageImageArtifact`；
- 列舉：`SourceFormat`、`ArtifactType`、`ArtifactStatus`、`EngineName`、`DeploymentMode`、
  `RevisionMode`、`CommentMode`、`AnnotationKind`、`PageImageFormat` 與 `ErrorCode`；
- 錯誤：`ConversionError`；
- 逐頁圖片與比較：`PdfRasterizer`、`PdfiumPageRenderer`、`RasterOptions`、
  `PdfComparisonService`、`PdfComparisonReport` 與 `PillowImageDiffer`。

其他所有模組，包括 `gordon_doc_converter.engines`、`content`、`process`、`api` 與 `cli`，
以及任何以底線開頭的名稱，都屬於內部實作，任何版本都可能變動。

相容的變動包括：在 `__all__` 新增名稱、新增具預設值的 keyword 參數、在模型新增選用欄位，
以及在列舉新增成員。比對列舉值的呼叫端應能處理未知的成員。

### 命令列介面

- `doctor`、`engines`、`template`、`convert`、`compare`、`batch` 與 `version` 命令，以及其
  文件記載的選項與引數。
- Exit code：`0` 成功；`2` 輸入無效或輸出已存在；`3` 引擎或能力不可用；`4` 轉換失敗、
  逾時或未產生輸出；`5` PDF 驗證失敗。新的失敗類別會取得新的 code，既有 code 的意義永不改變。
- `--json` 輸出的文件。可新增欄位；既有欄位不會被移除、改名或變更型別。

給人閱讀的文字輸出、stderr 上的進度輸出與說明文字不屬於契約。

### 錯誤與警告代碼

- `ErrorCode` 的值是穩定的。Minor 版本可能新增代碼。
- 警告的 `code` 值（例如 `ENGINE_FALLBACK` 與 `LAYOUT_NOT_PRESERVED`）一經發布即為穩定。
  Minor 版本可能新增警告，因此呼叫端應忽略無法辨識的代碼。
- 錯誤與警告的 `message` 文字是給人閱讀的，任何版本都可能變動。

### 結構化 YAML、JSON 與 JSON Lines Artifact

結構化 schema 帶有自己的 `schema_version`，與套件版本無關。

- Schema 的 minor 版本（例如 `1.5` 到 `1.6`）只會新增選用欄位、區塊種類、locator 種類或
  record 類型。未使用這些新項目的文件，序列化結果與先前完全相同。
- 移除、改名、變更欄位型別或欄位意義，必須提升 schema 的 major 版本（`1.x` 到 `2.0`），
  而且只會在套件的 major 版本中發布。
- 選用欄位會直接省略，而不是序列化為 `null`。讀取端應忽略未知的欄位與區塊種類。
- 位元組位移不屬於 locator 契約，原因請見 README。

### 排版輸出

PDF、DOCX、ODT、HTML、Markdown 與逐頁圖片輸出不保證逐位元組相同。引擎版本、字型與 writer
的修正都會改變其確切位元組與版面。這些輸出的檔名與目錄結構（`<stem>.pages/0001.png`、
`<stem>.assets/` 與註解 sidecar）屬於契約。

### HTTP API

有版本前綴的路由為 `POST /v1/conversions`、`GET /v1/engines` 與 `GET /v1/version`。
探測端點 `GET /live` 與 `GET /ready` 不加版本前綴，因此容器的健康檢查永遠不需要更改。

- 匯出的 OpenAPI 契約（`docs/openapi.json`）所記載的路徑、請求標頭、query 參數、狀態碼
  與錯誤內容都受本政策保障。
- 破壞性變更會在新的前綴（例如 `/v2/`）下發布，並與 `/v1/` 並存至少一個 minor 版本，
  之後才會在 major 版本中移除 `/v1/`。
- `GORDON_DOC_API_KEY` 與 `GORDON_DOC_GOTENBERG_URL` 是穩定的設定名稱。
- 沒有前綴的 `/conversions`、`/engines` 與 `/version` 是為 `0.12.0` 之前的用戶端保留的
  已棄用別名。它們在 OpenAPI 契約中標示為 `deprecated`，並會在 `1.0.0` 移除。

### 容器映像

- 映像名稱、tag 規則（`X.Y.Z`、`X.Y`、`latest`）、發布平台（`linux/amd64` 與
  `linux/arm64`）、預設的 CLI entrypoint、`api` 引數與 Compose profile 名稱都屬於契約。
- Minor 版本可能增加映像內的引擎。移除引擎或映像提供的轉換路徑屬於破壞性變更。
- 基底映像，以及 LibreOffice 與其他系統套件的版本，不屬於契約。

## 支援平台

`.github/workflows/ci.yml` 中的 `quality` job 會在下列每種組合上執行完整的單元測試，本清單
必須與其保持一致。

- Python：3.12、3.13 與 3.14。對某個 Python 版本的支援只會在 minor 版本中停止，而且必須在
  該版本終止維護之後。
- 作業系統：Linux、Windows 與 macOS。Microsoft Word COM 只能在 Windows 上使用；實際引擎的
  整合測試在 Linux（LibreOffice）與受控的 Windows 主機（Word）上執行。
- 引擎：對各引擎版本的支援為盡力而為。本專案絕不保證 Microsoft Word 與 LibreOffice 的
  排版結果相同。

## 棄用流程

1. 公開契約在 minor 版本中標示為棄用，並在 `CHANGELOG.md` 加入 `Deprecated` 紀錄；Python
   API 另會發出指出替代方案的 `DeprecationWarning`。
2. 已棄用的契約至少會在下一個 minor 版本中繼續運作，並且只會在下一個 major 版本中移除。
3. 安全修正是唯一的例外。若保留某項契約會讓使用者暴露於風險，該契約可能在 minor 或 patch
   版本中變更，並在 `Security` 段落中特別說明。
