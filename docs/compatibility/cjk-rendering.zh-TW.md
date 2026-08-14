# CJK 渲染相容性矩陣

第 7 階段 fixtures 是由 `scripts/generate_cjk_fixtures.py` 產生的合成公開測試資料。
其中不包含客戶文件、個人資料或內含字型。產生的圖片是原創雙色 PNG；fixture set 以
CC0-1.0 授權供測試重複使用。

## Fixture 涵蓋範圍

| Fixture | 版面功能 | 自動化 gate |
| --- | --- | --- |
| `a4-portrait.docx` | A4 直式頁面 | OOXML 與 LibreOffice PDF 驗證 |
| `a4-landscape.docx` | A4 橫式頁面 | OOXML 與 LibreOffice PDF 驗證 |
| `mixed-sections.docx` | 直式與橫式 section | OOXML 與 LibreOffice PDF 驗證 |
| `chinese-toc.docx` | 中文標題與 TOC field | OOXML 與 LibreOffice PDF 驗證 |
| `multi-page-table.docx` | 120 列中文表格 | PDF 必須至少包含兩頁 |
| `headers-footers.docx` | 中文頁首／頁尾與 PAGE field | OOXML 與 LibreOffice PDF 驗證 |
| `text-box.docx` | VML text box 中的中文文字 | OOXML 與 LibreOffice PDF 驗證 |
| `floating-image.docx` | 搭配文字環繞的錨定 PNG | OOXML 與 LibreOffice PDF 驗證 |
| `fields.docx` | PAGE、NUMPAGES 與 DATE field | OOXML 與 LibreOffice PDF 驗證 |
| `special-symbols.docx` | 繁體中文、CJK、注音與符號 | OOXML 與 LibreOffice PDF 驗證 |

## 解讀方式

CI gate 證明 LibreOffice 可以開啟每個 package 並產生可解析、非空的 PDF。它不保證不同
LibreOffice 版本、作業系統、Microsoft Word 或已安裝字型集合之間的像素完全一致。Word
COM coverage 仍在受控 Windows runner 上執行，因為 hosted runner 不包含具授權的
Microsoft Office。

CI 會從 Linux 發行版套件庫安裝 Noto CJK；本專案不下載、打包或重新散布 Microsoft
字型。當分頁或字形外觀很重要時，請在測試結果中記錄 renderer 版本與已安裝的字型集合。
