# GordonKit 文件轉換器

GordonKit Document Converter 是適用於 Python 3.12 以上的可診斷、多引擎
DOCX 轉 PDF 協調函式庫。實際排版會委派給 Microsoft Word、LibreOffice，或後續版本的
Gotenberg；本專案本身不實作文書排版引擎。

目前的開發迭代先建立跨平台請求／結果契約、引擎選擇政策及 PDF 驗證。Word COM、
LibreOffice 執行、完整協調服務與 `gordon-doc` CLI 將在後續 v0.1 迭代提供，目前尚不可用。

## 開發環境

```console
uv sync --dev
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
uv build
```

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
