# Python 程式碼規範

Python 原始碼以 3.12 以上為目標，且必須通過 Ruff 格式／lint 與 strict mypy。公開 API
需有完整型別註記及英文 docstring。優先使用具型別且不可變的 dataclass、列舉、Protocol、
`pathlib.Path`、小型單一職責函式、相依性注入與組合。

核心模組不得依賴呈現框架或引擎專屬回應型別；平台專屬相依套件必須延遲載入。子行程
只能存在於引擎 adapter 或專用 process utility，參數必須是序列、禁止 `shell=True`、必須
設定 timeout 並擷取輸出，且所有結果都要清除轉換流程擁有的暫存資料。

除非明確允許，不得覆寫輸出。路徑及文件資料一律視為不可信任輸入。不得記錄文件內容、
憑證、敏感中繼資料或敏感完整路徑。跨越例外邊界轉換為專案錯誤時，必須保留原始例外鏈。

每個公開行為與錯誤修正都需要測試。單元測試應模擬外部 renderer，不得要求 Word、
LibreOffice 或 Gotenberg；整合及平台專屬測試需使用明確的 pytest marker。
