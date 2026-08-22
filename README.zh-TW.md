# GordonKit 文件轉換器

[![CI](https://github.com/gordonkit/gordon-doc-converter/actions/workflows/ci.yml/badge.svg)](https://github.com/gordonkit/gordon-doc-converter/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![授權：Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![開發狀態：Pre-Alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](https://pypi.org/classifiers/)

[English](https://github.com/gordonkit/gordon-doc-converter/blob/main/README.md)

[線上文件](https://docs.gordonkit.com/)

GordonKit Document Converter 可將 DOCX 與其他文件格式轉換為 PDF、HTML、Markdown、
圖片等格式。它提供 Python 函式庫、命令列介面與 HTTP API，並使用 Microsoft Word、
LibreOffice、Pandoc 或 Gotenberg 進行排版轉換。

## 支援的格式轉換

| 輸入格式 | DOCX | PDF | ODT | HTML | Markdown | YAML | JSON | 圖片 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DOCX | × | Auto | LO | ✓ | ✓ | ✓ | ✓ | PDF |
| PDF | — | × | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| ODT | LO | LO | × | — | — | — | — | — |
| HTML | P | P+ | — | × | — | — | — | — |
| Markdown | P | P+ | — | — | × | — | — | — |

`Auto` 依政策自動選擇引擎 · `✓` 內建支援 · `LO` LibreOffice · `P` Pandoc ·
`P+` Pandoc 搭配 PDF 後端 · `PDF` 先轉為 PDF · `—` 不支援 ·
`×` 相同格式，不執行轉換

逐頁圖片可輸出為 PNG 或 JPEG。DOCX 與 PDF 可產生 Markdown、HTML、YAML、JSON
及圖片；Markdown 與 HTML 也可轉換為 PDF 或 DOCX，但兩者無法直接互轉。

DOCX 轉 ODT、ODT 轉 DOCX，以及 ODT 轉 PDF 均使用 LibreOffice。DOCX 轉換採用以下
引擎政策：

- 互動式 Windows 的 DOCX 轉 PDF：自動模式優先使用 Word COM。
- 伺服器的 DOCX 轉 PDF：自動模式依序優先使用 Gotenberg、LibreOffice。
- 其他主機的 DOCX 轉 PDF：自動模式優先使用 LibreOffice。
- DOCX 轉 HTML：預設使用語意萃取。在 Windows 桌面環境且 Word COM 可用時，透過 Word
    排版可獲得更高的視覺忠實度。
- 使用 `--engine word-com` 可強制使用 Word COM 輸出 HTML，使用 `--mode server` 則可強制
    使用語意萃取。
- 明確指定引擎與 strict 模式絕不 fallback。
- 不同引擎的排版結果可能有差異。

ODT 支援以 ODF-CNS 15251／ISO/IEC 26300 Writer 文件為目標，會驗證封裝結構與內容是否
可讀，但不保證來回轉換後版面完全相同。

HTML／Markdown 轉換需要 Pandoc；輸出 PDF 時還需要 `wkhtmltopdf` 等 Pandoc PDF
後端。可先執行 `gordon-doc template 報告.html` 建立可編輯、適合列印的 A4 範本，
再執行 `gordon-doc convert 報告.html --to pdf` 或 `--to docx`。若要使用 A4 橫式版面，
請加上 `--orientation landscape`。

## 使用介面

| 介面 | 適用情境 |
| --- | --- |
| Python 函式庫 | 在 Python 應用程式中使用具型別的轉換、批次處理與引擎診斷功能 |
| `gordon-doc` 命令列工具 | 從終端機、指令碼或 CI 工作執行本機轉換 |
| HTTP API | 將需驗證身分的轉換要求傳送至內部服務 |
| 容器執行模式 | 在隔離映像中執行命令列工具或 HTTP API 及其排版引擎相依套件 |

各種轉換介面皆使用相同的應用服務，並保留結構化結果、引擎政策與診斷資訊。

## 安裝

| 介面 | 安裝方式 |
| --- | --- |
| Python 函式庫 | `python -m pip install gordon-doc-converter` |
| `gordon-doc` 命令列工具 | 隨 `gordon-doc-converter` 安裝；可執行 `gordon-doc version` 確認 |
| HTTP API | `python -m pip install "gordon-doc-converter[api]"` |
| 容器執行模式 | 安裝 Docker Engine 或 Docker Desktop 與 Compose v2；不需安裝本機 Python 套件 |

部分排版與輸出功能需要安裝 `gordon-doc-converter[images]`、
`gordon-doc-converter[gotenberg]` 或 `gordon-doc-converter[word]`。各引擎與平台需求請參閱
[線上文件](https://docs.gordonkit.com/)。

## 快速開始

### Python 函式庫

在 Python 應用程式中執行轉換：

```python
from pathlib import Path

from gordon_doc_converter import ConversionRequest, convert

request = ConversionRequest.from_source(Path("範例.docx"))
result = convert(request)
if not result.success:
    raise RuntimeError(result.error.message if result.error else "conversion failed")
print(result.artifacts[0].path)
```

`convert()` 會依部署政策選擇引擎、驗證暫存輸出，並只在驗證成功後發布 PDF。
需要注入引擎時使用 `DocumentConversionService`；依序執行且各項失敗互不影響的批次轉換
使用 `convert_batch()`；能力診斷則使用 `probe_engines()`。

### 命令列工具

```console
gordon-doc convert 範例.docx --output 範例.pdf
```

### 容器

若不想在主機安裝 Python 或 LibreOffice，可使用單一容器映像。`cli` 執行模式會將目前
目錄掛載至 `/work`，且不需要 API 金鑰。以下單行指令可同時用於 Bash 與 PowerShell：

```console
docker compose -f docker/compose.yaml --profile cli run --rm cli convert /work/範例.docx --output /work/範例.pdf
```

若要啟動內含 LibreOffice 的內部 HTTP 服務，請設定 API 金鑰並啟動 `standalone-lo`：

```dotenv
GORDON_DOC_API_KEY=replace-with-a-strong-random-value
```

```console
docker compose -f docker/compose.yaml --env-file .env --profile standalone-lo up --build
```

若要使用獨立的 Gotenberg 排版服務，請改用 `gateway-gotenberg`；相同的 API 映像會透過
共用 Docker network 連線 Gotenberg。設定 `GORDON_DOC_GOTENBERG_URL` 後，API 會明確以
Gotenberg 為預設引擎；Gotenberg 請求失敗時不會靜默改用 LibreOffice。容器執行模式、
安全性說明與基本檢查請參閱[繁中容器文件](docker/README.zh-TW.md)。正式版本 tag 會將
`gordonkit/gordon-doc-converter` 單一映像發布至 Docker Hub；所需 repository 變數、
secrets 與發行步驟也記錄於該文件。

### HTTP API

API 啟動後，請傳送 DOCX 內容、原始檔名與 Bearer Token：

```sh
curl --fail -H "Authorization: Bearer replace-me" \
    -H "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document" \
    -H "X-Filename: 範例.docx" --data-binary @範例.docx \
    http://localhost:8000/conversions --output 範例.pdf
```

PowerShell 請使用 `Invoke-WebRequest -InFile ... -OutFile ...`。LibreOffice 與 Gotenberg
profiles 的 Bash、PowerShell 完整啟動、轉換及停止服務範例，請參閱
[繁中容器文件](docker/README.zh-TW.md)。

PDFium／Pillow 點陣化功能使用 `.[images]`；遠端配接器使用 `.[gotenberg]`；FastAPI
使用 `.[api]`；Windows COM 使用 `.[word]`。

## 命令列介面

```console
gordon-doc doctor
gordon-doc engines --json
gordon-doc template 報告.html --orientation portrait
gordon-doc convert 範例.docx --output 範例.pdf
gordon-doc convert 報告.odt --to docx
gordon-doc convert 範例.docx --to odt --engine libreoffice
gordon-doc convert 報告.html --to pdf --orientation landscape
gordon-doc convert 報告.html --to docx
gordon-doc convert 範例.pdf --to images --dpi 144
gordon-doc convert 範例.docx --to markdown --to html --to yaml --to json
gordon-doc convert 範例.docx --to html --engine word-com
gordon-doc convert 範例.docx --to yaml --metadata layout --progress
gordon-doc compare 預期.pdf 實際.pdf --diff-dir 差異 --json
gordon-doc batch 文件一.docx 文件二.docx --output-dir 已轉換 --json
gordon-doc version
```

使用 `--engine word-com`、`--engine libreoffice` 或已設定的 `--engine gotenberg` 可嚴格
指定引擎。DOCX 轉 HTML 時，`--engine word-com` 會透過 Word COM 排版；省略或改用
`--mode server` 則使用語意萃取。轉換選項也包含 `--mode`、`--revisions`、`--comments`、
`--metadata`、`--timeout`、`--overwrite`、圖片格式／品質／頁碼，以及選用的
`--gotenberg-url`。
逐頁圖片使用 `<stem>.pages/0001.png`；語意產出檔案使用 `.md`、`.html`、`.yaml`、
`.json`、共用 `.assets/`，有註解時另建附屬檔案。YAML 與 JSON 共用具版本的章節、
段落、清單及表格結構，可供後續索引使用。`--to json` 產生文件內容；不同用途的
`--json` 則輸出命令列執行結果，便於自動化整合。

中繼資料等級可選 `none`、`basic`（預設允許清單中的文件屬性）或 `layout`。PDF 實體
頁碼從 1 起算，提供者為 `pypdf`。DOCX 在尚未設定版面資訊提供者時，會省略實體頁碼
與文件顯示頁碼，並明確標示為無法取得，不會將推定頁碼當成精確資料。

結構化產出檔案支援跨格式反向定位。`source.sha256` 用來確認完全相同的來源檔案；
每個 `source_anchor` 另有正規化內容的 SHA-256，可供定位後驗證。DOCX 區塊可定位至
`word/document.xml` 元素，表格儲存格再以列與儲存格定位；PDF 區塊則定位至從 1 起算的
實體頁。目前 PDF 錨點定位到頁面而非頁內座標；未來可由版面資訊提供者加入座標，且不會
破壞 DOCX 定位契約。沒有值的選用定位欄位不會輸出為 null。

```yaml
schema_version: "1.3"
source: {format: "pdf", sha256: "<來源檔案-sha256>"}
root_blocks: [{
    id: "block-000001",
    source_order: 0,
    kind: "paragraph",
    physical_page_number: 1,
    text: "頁面文字",
    source_anchor: {
        locator: "pdf-page",
        page_number: 1,
        content_sha256: "<正規化內容-sha256>"
    }
}]
```

位元組位移刻意不納入穩定的定位契約。DOCX 位移指向 ZIP 內的壓縮資料，Office 重新儲存
或調整壓縮方式後就會改變；PDF 位移指向序列化物件或資料流，經過最佳化、線性化或增量
儲存後也會改變。請使用來源指紋搭配 OOXML 元素路徑或 PDF 頁面錨點。未來若加入位元組
位移，也只會作為非權威的診斷提示。

`convert` 與 `batch` 在互動終端會自動顯示轉換階段。進度只寫入 stderr，使用 `--json`
或重導向時會自動關閉；可用 `--progress` 或 `--no-progress` 覆寫自動判斷。

固定結束代碼為：`0` 成功；`2` 輸入無效或輸出已存在；`3` 引擎或能力不可用；`4` 轉換
失敗、逾時或未產生輸出；`5` PDF 驗證失敗。

Microsoft Word 與 LibreOffice 對同一文件可能產生不同版面。本專案會揭露實際引擎及
備援原因；明確指定引擎時，不會在未告知的情況下切換引擎。

## 開發環境

```console
uv sync --dev
uv sync --dev --all-extras
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
uv build
```

系統找不到 `soffice` 時，LibreOffice 整合測試會略過。已安裝 LibreOffice 的環境可執行
`uv run pytest -m integration tests/integration/libreoffice`。

Microsoft Word 整合測試需要 Windows、合法授權的 Microsoft Word 及 `word` 選用相依
套件。請只在受控的互動式環境中執行：先執行 `uv sync --dev --extra word --locked`，
再執行 `uv run pytest -m integration tests/integration/word_com`。

靜態文件網站使用 React、Vite、Tailwind CSS、隨附的 Heroicons 與 Swagger UI 建置。
重新建置 `docs/` 前，請先安裝 API 與前端相依套件；建置時會自動將目前的 FastAPI 契約
匯出至 `openapi.json`：

```console
uv sync --dev --extra api --locked
npm ci
npm run build
```

產生的網站位於 `docs/`，並發布於 [docs.gordonkit.com](https://docs.gordonkit.com/)。建置會在
`/en/<topic>/` 與 `/zh-TW/<topic>/` 產生可索引頁面，包含在地化 metadata、canonical、語言
alternate、結構化資料、sitemap 與 robots 指示。網站也支援雙語導覽、搜尋、響應式版面及
亮色／暗色主題。API 契約位於 `docs/openapi.json`，唯讀 Swagger UI 位於
`docs/swagger/index.html`。可執行 `npm run openapi:check` 檢查匯出內容是否已過期。

請從[英文文件](https://docs.gordonkit.com/en/overview/)或
[繁體中文文件](https://docs.gordonkit.com/zh-TW/overview/)瀏覽技術參考、使用指南、相容性說明與開發規範。

## 授權

採用 Apache License 2.0，詳見 [LICENSE](LICENSE)、[NOTICE](NOTICE) 與
[THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt)。
