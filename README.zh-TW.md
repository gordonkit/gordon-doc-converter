# GordonKit 文件轉換器

[![CI](https://github.com/gordonkit/gordon-doc-converter/actions/workflows/ci.yml/badge.svg)](https://github.com/gordonkit/gordon-doc-converter/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![授權：Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![開發狀態：Pre-Alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](https://pypi.org/classifiers/)

GordonKit Document Converter 是適用於 Python 3.12 以上的可診斷、多引擎
文件轉換協調函式庫。實際排版會委派給 Microsoft Word、LibreOffice，或選用的
Gotenberg；本專案本身不實作文書排版引擎。

目前已完成跨平台請求／結果契約、引擎選擇政策、PDF 驗證、具隔離機制的 LibreOffice
與 Microsoft Word COM adapter、DOCX/PDF 語意擷取、Markdown/HTML 與逐頁圖片 artifact、
PDF 渲染比對、具認證的 FastAPI adapter、強化容器 profiles，以及 `gordon-doc` CLI。

## 安裝

從 PyPI 安裝核心函式庫與 CLI：

```console
python -m pip install gordon-doc-converter
gordon-doc version
```

選用功能可透過 `gordon-doc-converter[images]`、`gordon-doc-converter[gotenberg]`、
`gordon-doc-converter[api]` 與 `gordon-doc-converter[word]` 安裝。各引擎與平台需求請參閱
[線上文件](https://docs.gordonkit.com/)。

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

系統找不到 `soffice` 時，真實 LibreOffice 整合測試會略過。已安裝 LibreOffice 的環境可用
`uv run pytest -m integration tests/integration/libreoffice` 執行該測試。

Microsoft Word 整合測試需要 Windows、合法授權的 Microsoft Word 及 `word` optional
dependency。僅在受控互動式環境先執行 `uv sync --dev --extra word --locked`，再執行
`uv run pytest -m integration tests/integration/word_com`。

靜態文件網站以 React、Vite、Tailwind CSS、bundled Heroicons 與內建 Swagger UI 建置。
發布 `docs/` 前先安裝 API 與前端相依套件；建置時會自動將目前的 FastAPI 契約匯出為
`openapi.json`：

```console
uv sync --dev --extra api --locked
npm ci
npm run build
```

產生後的網站資源都位於 `docs/`，且連結使用相對路徑。網站發布於
[docs.gordonkit.com](https://docs.gordonkit.com/)。單一文件索引支援 English／繁體中文導覽、搜尋、響應式版面，以及
亮色／暗色主題偏好。產生的 API 契約位於 `docs/openapi.json`，唯讀 Swagger UI 位於
`docs/swagger/index.html`。可執行 `npm run openapi:check` 檢查匯出規格是否過期。

## 轉換範例

```python
from pathlib import Path

from gordon_doc_converter import ConversionRequest, convert

request = ConversionRequest.from_source(Path("範例.docx"))
result = convert(request)
if not result.success:
    raise RuntimeError(result.error.message if result.error else "conversion failed")
print(result.artifacts[0].path)
```

`convert()` 會依 deployment policy 選擇引擎、驗證 staging 輸出，並只在驗證成功後發布
PDF。需要注入引擎時使用 `DocumentConversionService`；依序執行且個別失敗互不影響的批次
轉換使用 `convert_batch()`；能力診斷則使用 `probe_engines()`。

## 支援的格式轉換

| 輸入格式 | PDF | DOCX | ODT | Markdown | HTML | YAML | JSON | 逐頁圖片 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DOCX | 可以 | 可以，使用 LibreOffice | 可以，使用 LibreOffice | 可以 | 可以 | 可以 | 可以 | 可以，會先經過中間 PDF |
| ODT | 可以，使用 LibreOffice | 可以，使用 LibreOffice | 可以 | 不支援 | 不支援 | 不支援 | 不支援 | 不支援 |
| PDF | 可以，驗證後發布副本 | 不支援 | 不支援 | 可以 | 可以 | 可以 | 可以 | 可以 |
| HTML | 可以，需要 Pandoc 及 PDF backend | 可以，需要 Pandoc | 不支援 | 不適用 | 不適用 | 不支援 | 不支援 | 不支援 |
| Markdown | 可以，需要 Pandoc 及 PDF backend | 可以，需要 Pandoc | 不支援 | 不適用 | 不適用 | 不支援 | 不支援 | 不支援 |

逐頁圖片可輸出為 PNG 或 JPEG。Markdown、HTML、YAML、JSON 及圖片是 DOCX/PDF 的輸出
artifact；Markdown 與 HTML 也可作為輸入，轉換為 PDF 或 DOCX，但目前不支援 Markdown
與 HTML 彼此直接互轉。PDF 轉 PDF 只會驗證並發布來源檔案，不會重新排版；DOCX 轉 PDF 則使用
選定的 Word、LibreOffice 或 Gotenberg 引擎。ODT 以 ODF-CNS 15251／ISO/IEC 26300 Writer
文件為相容目標；目前驗證 package 結構與內容可讀性，不保證往返轉換後像素完全一致。

使用 `gordon-doc template 報告.html` 建立可編輯、適合列印的 A4 HTML 起始範本。使用
`--orientation landscape` 可建立 A4 橫式範本，編輯完成後可用
`gordon-doc convert 報告.html --to pdf` 或 `--to docx` 轉換。HTML/Markdown 轉換需要
Pandoc；PDF 輸出另外需要 `wkhtmltopdf` 等 Pandoc PDF backend。

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
gordon-doc convert 範例.docx --to yaml --metadata layout --progress
gordon-doc compare 預期.pdf 實際.pdf --diff-dir 差異 --json
gordon-doc batch 文件一.docx 文件二.docx --output-dir 已轉換 --json
gordon-doc version
```

使用 `--engine word-com`、`--engine libreoffice` 或已設定的 `--engine gotenberg` 可嚴格
指定引擎。轉換選項也包含 `--mode`、`--revisions`、`--comments`、`--metadata`、
`--timeout`、`--overwrite`、圖片格式／品質／頁碼，以及選用的 `--gotenberg-url`。
逐頁圖片使用 `<stem>.pages/0001.png`；語意產物使用 `.md`、`.html`、`.yaml`、`.json`、
共用 `.assets/`，有註解時另建 sidecar。YAML 與 JSON 共用具版本的章節、段落、清單及
表格 schema，可供後續索引使用。`--to json` 產生文件 artifact；不同用途的 `--json`
則輸出 CLI 執行結果，便於自動化整合。

metadata 等級可選 `none`、`basic`（預設的 allowlist 文件屬性）或 `layout`。PDF 實體
頁碼從 1 起算，provider 為 `pypdf`。DOCX 在尚未配置 layout provider 時，實體頁碼與
文件顯示頁碼欄位會省略並明確標示 unavailable，不會將推定頁碼宣稱為精確資料。

結構化 artifact 提供跨格式反向定位。`source.sha256` 用來確認完全相同的來源檔案；
每個 `source_anchor` 另有正規化內容 SHA-256 供定位後驗證。DOCX block 可定位至
`word/document.xml` element，表格儲存格再以 row/cell 定位；PDF block 則定位至從 1
起算的實體頁。目前 PDF anchor 定位到頁面而非頁內座標；未來可由 layout provider
加入座標而不破壞 DOCX locator 契約。無值的選用 locator 欄位不會輸出為 null。

```yaml
schema_version: "1.3"
source:
    format: pdf
    sha256: <來源檔案-sha256>
root_blocks:
    - id: block-000001
        source_order: 0
        kind: paragraph
        physical_page_number: 1
        text: 頁面文字
        source_anchor:
            locator: pdf-page
            page_number: 1
            content_sha256: <正規化內容-sha256>
```

byte offset 刻意不納入穩定 locator 契約。DOCX offset 指向 ZIP 內的壓縮資料，Office
重新儲存或調整壓縮方式後就會改變；PDF offset 指向序列化 object 或 stream，經過最佳化、
linearization 或增量儲存後也會改變。請使用來源指紋搭配 OOXML element path 或 PDF page
anchor。未來若加入 byte offset，也只會作為非權威的診斷提示。

`convert` 與 `batch` 在互動終端會自動顯示轉換階段。進度只寫入 stderr，使用 `--json`
或重導向時會自動關閉；可用 `--progress` 或 `--no-progress` 覆寫自動判斷。

PDFium/Pillow rasterization 使用 `.[images]`；遠端 adapter 使用 `.[gotenberg]`；FastAPI
使用 `.[api]`；Windows COM 使用 `.[word]`。容器及具認證 API 的說明見
[docker/README.md](docker/README.md)。

固定退出碼為：`0` 成功；`2` 輸入無效或輸出已存在；`3` 引擎或能力不可用；`4` 轉換
失敗、逾時或未產生輸出；`5` PDF 驗證失敗。

Microsoft Word 與 LibreOffice 對同一文件可能產生不同版面。本專案會揭露實際引擎及
fallback 原因，且明確指定引擎時絕不靜默切換。

請從[文件索引](docs/index.html)瀏覽技術參考、操作手冊、相容性說明與開發規範，並使用
右上角的語系控制切換 English／繁體中文。

## 授權

採用 Apache License 2.0，詳見 [LICENSE](LICENSE)、[NOTICE](NOTICE) 與
[THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt)。
