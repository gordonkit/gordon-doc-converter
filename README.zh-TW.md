# GordonKit 文件轉換器

GordonKit Document Converter 是適用於 Python 3.12 以上的可診斷、多引擎
DOCX 轉 PDF 協調函式庫。實際排版會委派給 Microsoft Word、LibreOffice，或選用的
Gotenberg；本專案本身不實作文書排版引擎。

目前已完成跨平台請求／結果契約、引擎選擇政策、PDF 驗證、具隔離機制的 LibreOffice
與 Microsoft Word COM adapter、DOCX/PDF 語意擷取、Markdown/HTML 與逐頁圖片 artifact、
PDF 渲染比對、私有 FastAPI adapter、強化容器 profiles，以及 `gordon-doc` CLI。

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

## 命令列介面

```console
gordon-doc doctor
gordon-doc engines --json
gordon-doc convert 範例.docx --output 範例.pdf
gordon-doc convert 範例.pdf --to images --dpi 144
gordon-doc convert 範例.docx --to markdown --to html
gordon-doc compare 預期.pdf 實際.pdf --diff-dir 差異 --json
gordon-doc batch 文件一.docx 文件二.docx --output-dir 已轉換 --json
gordon-doc version
```

使用 `--engine word-com`、`--engine libreoffice` 或已設定的 `--engine gotenberg` 可嚴格
指定引擎。轉換選項也包含 `--mode`、`--revisions`、`--comments`、`--timeout`、
`--overwrite`、圖片格式／品質／頁碼，以及選用的 `--gotenberg-url`。逐頁圖片使用
`<stem>.pages/0001.png`；語意產物使用 `.md`、`.html`、共用 `.assets/`，有註解時另建
sidecar。所有指令都支援 `--json`，便於自動化整合。

PDFium/Pillow rasterization 使用 `.[images]`；遠端 adapter 使用 `.[gotenberg]`；FastAPI
使用 `.[api]`；Windows COM 使用 `.[word]`。容器及私有 API 說明見
[docker/README.md](docker/README.md)。

固定退出碼為：`0` 成功；`2` 輸入無效或輸出已存在；`3` 引擎或能力不可用；`4` 轉換
失敗、逾時或未產生輸出；`5` PDF 驗證失敗。

Microsoft Word 與 LibreOffice 對同一文件可能產生不同版面。本專案會揭露實際引擎及
fallback 原因，且明確指定引擎時絕不靜默切換。

## 授權

採用 Apache License 2.0，詳見 [LICENSE](LICENSE) 與 [NOTICE](NOTICE)。
