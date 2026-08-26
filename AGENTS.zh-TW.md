# Repository 開發指引（繁體中文版）

> 本檔是根目錄 `AGENTS.md` 的人工閱讀翻譯，不會取代 Codex 自動載入的
> `AGENTS.md`。如兩份內容有歧義，以 `AGENTS.md` 為準；修改規則時應同步更新。

## 專案目的與目前範圍

GordonKit Document Converter 是 Python 3.12+ 的 DOCX 轉 PDF 協調 Library，透過
外部排版引擎完成轉換，本身不實作文件 renderer。v0.1 以核心 Python Library 與
CLI 為交付範圍；除非任務明確調整 roadmap，API 與 Container 屬於後續階段。

套件名稱為 `gordon-doc-converter`，Python import package 為
`gordon_doc_converter`，CLI 指令為 `gordon-doc`。

## 工具與標準指令

- 使用 `uv` 管理依賴與執行開發指令。
- 以 `uv sync --dev` 安裝或同步環境。
- 以 `uv run ruff format .` 格式化程式碼。
- 以 `uv run ruff check .` 執行 lint。
- `src/` 建立後，以 `uv run mypy src` 執行型別檢查。
- `tests/` 建立後，以 `uv run pytest` 執行測試。
- 交付程式碼變更前，執行所有相關檢查。若對應的 source 或 test 目錄尚未建立，
  應清楚說明，不要只為讓指令通過而建立空白檔案。

不得手動編輯 `uv.lock`；獲准變更依賴時，透過 `uv` 更新 lockfile。

## 架構邊界

- 核心 Library 必須獨立於 CLI 與 API framework。
- CLI command 與未來的 API route 必須呼叫 application service，不得直接呼叫
  轉換引擎。
- 所有轉換引擎實作同一個共用 engine protocol。
- 引擎選擇、部署模式、fallback 與 orchestration 不得放入個別 adapter。
- 公開核心 API 不得暴露 Word COM、LibreOffice 或 Gotenberg 專用 response type。
- 作業系統偵測與引擎執行必須分離。
- Windows-only 依賴必須 lazy import，確保核心套件可在 Windows、Linux 與 macOS
  匯入。
- 優先使用職責單一的小型函式與組合；避免過早抽象與隱藏的全域狀態。

預期的依賴方向為：

```text
Library / CLI / future API
          -> application service and orchestrator
          -> shared engine protocol
          -> Word COM / LibreOffice / optional Gotenberg adapters
          -> PDF validation and structured conversion result
```

## 轉換與平台規則

- 只有互動式 Windows desktop 可自動使用 Word COM。
- Server 與 Container 模式絕對不得自動選用 Word COM。
- Server 模式優先 Gotenberg，其次 LibreOffice；Container 模式依 image profile
  使用 LibreOffice 或 Gotenberg。
- 明確指定引擎與 strict 模式時，絕對不得靜默 fallback。
- 自動 fallback 的結果必須包含嘗試的引擎、失敗原因、最終引擎與 warning。
- 不得宣稱 Microsoft Word 與 LibreOffice 的排版結果完全一致。
- 不得下載、封裝或散布 Microsoft 字型及 Office 元件。

## Python 與 Process 安全

- 遵循 `pyproject.toml` 的 Ruff 與 strict mypy 設定。
- 公開 API 必須具備完整型別註記與英文 docstring。
- 內部檔案操作使用 `pathlib.Path`，文字檔使用 UTF-8。
- 必須支援繁體中文檔名及包含空格的路徑。
- 除非呼叫端明確要求，不得覆寫既有輸出。
- 只有 engine adapter 或專用 process utility 可以使用 subprocess。
- subprocess 參數必須以 sequence 傳入，禁止 `shell=True`，必須設定 timeout，
  並捕捉 stdout 與 stderr。
- 每次轉換必須隔離 temp directory 與 LibreOffice profile；成功、錯誤及 timeout
  都要完成清理，必要時也要終止 child process。
- 將錯誤轉換為專案例外時，必須保留原始例外為 cause；不得吞掉廣泛例外。
- 引擎失敗後絕對不得在未告知的情況下切換引擎。

## 安全與隱私

- 將檔名、路徑、文件 metadata 與內容視為不可信輸入。
- 不得記錄文件內容、認證資料、token、客戶文件、敏感完整路徑，或不可再散布的
  字型。
- 對外 API response 不得暴露敏感本機路徑或原始 traceback。
- Fixture 只能使用公開或自行產生的內容；不得提交客戶資料或授權文件。
- 當任務包含輸入驗證時，需檢查副檔名、MIME 與 OOXML ZIP 結構，並防範過大
  輸入、解壓炸彈、損毀及加密文件。

## 測試要求

- 每項新的公開行為都要有測試；每個 bug fix 都要有 regression test。
- 單元測試不得要求 Microsoft Word、LibreOffice 或 Gotenberg，應 mock 外部工具
  與平台 API。
- Integration 與平台限定測試必須使用明確的 pytest marker。
- 視變更範圍涵蓋 policy 分支、穩定錯誤映射、JSON serialization、fallback、
  strict behavior、timeout、cleanup 與 PDF validation。
- 真實 Word 整合測試只能在具合法 Office 的受控 Windows 環境執行；不得假設
  hosted CI runner 已安裝 Word。

## 文件與變更紀律

- 公開 API 名稱及 docstring 使用英文；使用者文件可提供繁中、簡中與日文翻譯。
- 行為、CLI option、error code 與文件範例必須保持同步。
- 優先進行符合目前階段的最小變更，並維持公開 contract 相容性。
- 新增 production dependency 前，必須檢查必要性、授權、維護狀態及安全影響。
- Commit message 遵循 Conventional Commits：
  `<type>(<scope>): <imperative summary>`，使用簡潔英文且不超過 72 字元。
