# GordonKit 文件轉換器

GordonKit Document Converter 是適用於 Python 3.12 以上的可診斷、多引擎
DOCX 轉 PDF 協調函式庫。實際排版會委派給 Microsoft Word、LibreOffice，或後續版本的
Gotenberg；本專案本身不實作文書排版引擎。

目前已完成跨平台請求／結果契約、引擎選擇政策、PDF 驗證，以及具隔離機制的 LibreOffice
與 Microsoft Word COM adapter。安裝對應的外部應用程式後，可將 adapter 當作底層 Library
元件使用；完整協調服務與 `gordon-doc` CLI 尚未提供。

## 開發環境

```console
uv sync --dev
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

## 契約範例

```python
from pathlib import Path

from gordon_doc_converter import ConversionRequest

request = ConversionRequest.from_source(Path("範例.docx"))
assert request.to_dict()["artifacts"] == ["pdf"]
```

Microsoft Word 與 LibreOffice 對同一文件可能產生不同版面。本專案會揭露實際引擎及
fallback 原因，且明確指定引擎時絕不靜默切換。

## 授權

採用 Apache License 2.0，詳見 [LICENSE](LICENSE) 與 [NOTICE](NOTICE)。
