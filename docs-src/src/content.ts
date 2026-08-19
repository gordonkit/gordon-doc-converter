export type Locale = "en" | "zh-TW";

export type Section = {
  id: string;
  title: Record<Locale, string>;
  body: Record<Locale, string>;
  code?: string;
  note?: Record<Locale, string>;
  links?: Array<{
    label: Record<Locale, string>;
    href: string;
    download?: boolean;
  }>;
  interfaces?: Array<{
    title: Record<Locale, string>;
    label: Record<Locale, string>;
    body: Record<Locale, string>;
    example: string;
  }>;
  table?: {
    caption: Record<Locale, string>;
    headers: Record<Locale, string[]>;
    rows: Record<Locale, string[][]>;
    legend: Record<Locale, string[]>;
    alignLeft?: boolean;
    firstColumnWidth?: "standard" | "wide" | "w48" | "w50";
    secondColumnWidth?: "standard" | "w40" | "w48" | "w50";
  };
};

export type Page = {
  id: string;
  category: "getting-started" | "development" | "operations" | "project";
  title: Record<Locale, string>;
  heading?: Record<Locale, string>;
  summary: Record<Locale, string>;
  sections: Section[];
};

export const categories = [
  { id: "getting-started", label: { en: "Getting Started", "zh-TW": "快速開始" } },
  { id: "development", label: { en: "Development", "zh-TW": "開發指南" } },
  { id: "operations", label: { en: "Operations", "zh-TW": "維運部署" } },
  { id: "project", label: { en: "Project", "zh-TW": "專案資訊" } },
] as const;

export const pages: Page[] = [
  {
    id: "overview",
    category: "getting-started",
    title: { en: "Overview", "zh-TW": "總覽" },
    heading: { en: "GordonKit Document Converter", "zh-TW": "GordonKit 文件轉換器" },
    summary: {
      en: "An open-source project in the GordonKit ecosystem for diagnosable, multi-engine document conversion on Python 3.12+.",
      "zh-TW": "GordonKit 生態系中的開源專案，為 Python 3.12+ 提供可診斷的多引擎文件轉換能力。",
    },
    sections: [
      {
        id: "about-project",
        title: { en: "About this project", "zh-TW": "關於此專案" },
        body: {
          en: "Document Converter is one project within GordonKit, not the entire GordonKit platform. It provides a stable Python library and CLI contract while delegating document rendering to Microsoft Word, LibreOffice, Gotenberg, or Pandoc. Engine policy, fallback reporting, validation, and publishing remain explicit and observable.",
          "zh-TW": "Document Converter 是 GordonKit 旗下的一個專案，並不代表完整的 GordonKit 平台。它提供穩定的 Python 函式庫與 CLI 契約，並將文件排版委派給 Microsoft Word、LibreOffice、Gotenberg 或 Pandoc；引擎政策、fallback 報告、驗證與發布流程皆明確且可觀測。",
        },
      },
      {
        id: "interfaces",
        title: { en: "Ways to use it", "zh-TW": "使用介面" },
        body: {
          en: "Choose the interface that fits your workflow. Every interface enters through the same application service and preserves structured results, engine policy, and diagnostics.",
          "zh-TW": "依工作流程選擇適合的介面。所有介面都透過同一個 application service，並保留結構化結果、引擎政策與診斷資訊。",
        },
        interfaces: [
          {
            title: { en: "Python Library", "zh-TW": "Python 函式庫" },
            label: { en: "Application integration", "zh-TW": "應用程式整合" },
            body: {
              en: "Use typed public contracts for single conversions, isolated batches, engine probes, and service injection.",
              "zh-TW": "使用具型別的公開契約，執行單檔轉換、隔離式批次、引擎探測與 service injection。",
            },
            example: "from gordon_doc_converter import convert",
          },
          {
            title: { en: "CLI", "zh-TW": "CLI" },
            label: { en: "Terminal and automation", "zh-TW": "終端機與自動化" },
            body: {
              en: "Convert, compare, inspect engines, and emit stable JSON results for scripts and CI workflows.",
              "zh-TW": "執行轉換、比較與引擎檢查，並輸出穩定 JSON 結果供 script 與 CI 流程使用。",
            },
            example: "gordon-doc convert report.docx --to pdf",
          },
          {
            title: { en: "HTTP API", "zh-TW": "HTTP API" },
            label: { en: "Optional private adapter", "zh-TW": "選用的私有 Adapter" },
            body: {
              en: "Install the FastAPI extra for private deployments with authentication hooks, rate limits, and bounded concurrency.",
              "zh-TW": "安裝 FastAPI extra，建立具認證 hooks、流量限制與有限並行能力的私有部署。",
            },
            example: "POST /conversions",
          },
        ],
      },
      {
        id: "format-support",
        title: { en: "Format support", "zh-TW": "格式支援" },
        body: {
          en: "Use this matrix to see the project's primary conversion capabilities. Some routes require an optional engine or output package as noted.",
          "zh-TW": "下表整理本專案的主要轉換能力；部分路徑需安裝選用引擎或輸出套件，條件標示於表格中。",
        },
        table: {
          caption: { en: "Supported input and output formats", "zh-TW": "支援的輸入與輸出格式" },
          headers: {
            en: ["Input", "DOCX", "PDF", "HTML", "Markdown", "YAML", "JSON", "ODT", "Images"],
            "zh-TW": ["輸入", "DOCX", "PDF", "HTML", "Markdown", "YAML", "JSON", "ODT", "頁圖"],
          },
          rows: {
            en: [
              ["DOCX", "", "Auto", "✓", "✓", "✓", "✓", "LO", "PDF"],
              ["PDF", "—", "", "✓", "✓", "✓", "✓", "—", "✓"],
              ["HTML", "P", "P+", "", "—", "—", "—", "—", "—"],
              ["Markdown", "P", "P+", "—", "", "—", "—", "—", "—"],
              ["ODT", "LO", "LO", "—", "—", "—", "—", "", "—"],
            ],
            "zh-TW": [
              ["DOCX", "", "Auto", "✓", "✓", "✓", "✓", "LO", "PDF"],
              ["PDF", "—", "", "✓", "✓", "✓", "✓", "—", "✓"],
              ["HTML", "P", "P+", "", "—", "—", "—", "—", "—"],
              ["Markdown", "P", "P+", "—", "", "—", "—", "—", "—"],
              ["ODT", "LO", "LO", "—", "—", "—", "—", "", "—"],
            ],
          },
          legend: {
            en: ["Auto Policy-based engine selection", "✓ Built in", "LO LibreOffice", "P Pandoc", "P+ Pandoc with PDF backend", "PDF Via intermediate PDF", "— Not supported", "Gray × Same format; disabled"],
            "zh-TW": ["Auto 依環境政策自動選擇引擎", "✓ 內建支援", "LO LibreOffice", "P Pandoc", "P+ Pandoc 與 PDF backend", "PDF 經由中間 PDF", "— 不支援", "灰底 × 相同格式，停用"],
          },
        },
        note: {
          en: "For DOCX to PDF, automatic mode selects capable engines by environment: interactive Windows prefers Word COM, servers prefer Gotenberg then LibreOffice, and other hosts prefer LibreOffice. Explicit engine and strict modes never fall back. Rendering may differ between engines.",
          "zh-TW": "DOCX 轉 PDF 的自動模式會依環境選擇可用引擎：互動式 Windows 優先使用 Word COM，伺服器依序使用 Gotenberg、LibreOffice，其他主機則優先使用 LibreOffice。明確指定引擎與 strict 模式絕不 fallback；不同引擎的排版結果可能有差異。",
        },
      },
      {
        id: "install",
        title: { en: "Install", "zh-TW": "安裝" },
        body: {
          en: "Install the core package, then add only the optional capabilities required by your deployment.",
          "zh-TW": "先安裝核心套件，再依部署需求加入選用能力。",
        },
        code: "uv add gordon-doc-converter\nuv add 'gordon-doc-converter[images,gotenberg]'",
      },
      {
        id: "first-conversion",
        title: { en: "First conversion", "zh-TW": "第一次轉換" },
        body: {
          en: "Create a request from a source path. The service selects an allowed engine, validates staged output, and publishes only after validation succeeds.",
          "zh-TW": "從來源路徑建立請求。服務會選擇政策允許的引擎、驗證暫存輸出，並只在驗證成功後發布。",
        },
        code: "from pathlib import Path\nfrom gordon_doc_converter import ConversionRequest, convert\n\nrequest = ConversionRequest.from_source(Path(\"report.docx\"))\nresult = convert(request)\nprint(result.artifacts[0].path)",
        note: {
          en: "Explicit engine selection is strict and never silently falls back.",
          "zh-TW": "明確指定引擎時採嚴格模式，絕不會靜默 fallback。",
        },
      },
    ],
  },
  {
    id: "cli",
    category: "getting-started",
    title: { en: "CLI reference", "zh-TW": "CLI 指令參考" },
    summary: { en: "Convert, inspect, compare, and automate from the terminal.", "zh-TW": "從終端機執行轉換、檢查、比較與自動化。" },
    sections: [
      { id: "cli-overview", title: { en: "Command overview", "zh-TW": "指令總覽" }, body: { en: "Start here to choose the command for your task. All commands support --json for machine-readable output.", "zh-TW": "請先從此表選擇適合工作的指令。所有指令都支援 --json，以輸出機器可讀的結果。" }, table: { caption: { en: "CLI command overview", "zh-TW": "CLI 指令總覽" }, headers: { en: ["Command", "Use it for"], "zh-TW": ["指令", "適用情境"] }, rows: { en: [["doctor", "Check runtime health and renderer availability"], ["engines", "Inspect configured engines and capabilities"], ["convert", "Convert one DOCX, ODT, PDF, HTML, or Markdown file"], ["template", "Create an editable A4 HTML starter"], ["compare", "Compare two PDFs and optionally write visual diffs"], ["batch", "Convert multiple DOCX files with isolated failures"], ["version", "Print the installed package version"]], "zh-TW": [["doctor", "檢查執行環境健康狀態與 renderer 可用性"], ["engines", "查看已設定引擎及其能力"], ["convert", "轉換單一 DOCX、ODT、PDF、HTML 或 Markdown 檔案"], ["template", "建立可編輯的 A4 HTML 起始範本"], ["compare", "比較兩個 PDF，並可輸出視覺差異檔"], ["batch", "批次轉換多個 DOCX，且各檔案失敗互相隔離"], ["version", "印出已安裝套件版本"]] }, legend: { en: ["Run gordon-doc <command> --help for the installed command contract."], "zh-TW": ["請以 gordon-doc <command> --help 檢視目前安裝版本的指令契約。"] }, alignLeft: true } },
      { id: "cli-install", title: { en: "Install and command shape", "zh-TW": "安裝與指令形式" }, body: { en: "The gordon-doc command is installed with the package. Run gordon-doc --help or gordon-doc <command> --help to view the option values accepted by the installed version. Commands print a concise human result by default; add --json whenever another program consumes the output.", "zh-TW": "安裝套件時會一併安裝 gordon-doc。可用 gordon-doc --help 或 gordon-doc <command> --help 檢視目前安裝版本接受的選項值。預設輸出簡潔的人類可讀結果；若由其他程式處理輸出，請加入 --json。" }, code: "python -m pip install gordon-doc-converter\ngordon-doc version\ngordon-doc convert --help" },
      { id: "diagnostics", title: { en: "Diagnostics and version", "zh-TW": "環境診斷與版本" }, body: { en: "Use doctor before a production run: it reports the detected platform, whether the session is interactive, and the availability of each renderer. engines lists renderer capabilities without determining overall health. version returns the installed package version. doctor exits with code 3 when no engine is available.", "zh-TW": "正式轉換前可先使用 doctor：它會回報偵測到的平台、是否為互動式工作階段，以及各 renderer 的可用性。engines 只列出 renderer 能力，不判定整體健康狀態。version 回傳已安裝套件版本。若沒有可用引擎，doctor 會以 exit code 3 結束。" }, code: "gordon-doc doctor\ngordon-doc engines --json\ngordon-doc version --json" },
      { id: "convert", title: { en: "Convert one document", "zh-TW": "轉換單一文件" }, body: { en: "convert accepts DOCX, ODT, PDF, HTML, and Markdown input. With no --to it creates PDF for DOCX, ODT, HTML, or Markdown; PDF input always requires --to. Repeat --to to request several artifacts. --output is appropriate for one single-file artifact; without it, the service derives a safe sibling output name and refuses to replace an existing file unless --overwrite is present.", "zh-TW": "convert 接受 DOCX、ODT、PDF、HTML 與 Markdown 輸入。未指定 --to 時，DOCX、ODT、HTML、Markdown 會輸出 PDF；PDF 輸入則必須指定 --to。可重複使用 --to 取得多個 artifact。--output 適用於單一檔案 artifact；省略時服務會在來源旁推導安全的輸出名稱，除非提供 --overwrite，否則不會覆寫既有檔案。" }, code: "gordon-doc convert report.docx --output report.pdf\ngordon-doc convert report.docx --to markdown --to html --to yaml --to json\ngordon-doc convert report.pdf --to yaml --to json\ngordon-doc convert report.odt --to docx --engine libreoffice\ngordon-doc convert report.pdf --to images --dpi 144" },
      { id: "conversion-options", title: { en: "Conversion policy and output options", "zh-TW": "轉換政策與輸出選項" }, body: { en: "--engine word-com, libreoffice, or gotenberg requires that exact DOCX-to-PDF engine; explicit selection never falls back. --mode selects automatic policy: desktop, server, container, strict-word, or strict-libreoffice. Tracked changes use --revisions final, original, or markup; comments use --comments omit, appendix, or markup, subject to engine support. --timeout is in seconds. For HTML and Markdown, --orientation portrait or landscape chooses A4 layout. --gotenberg-url supplies the Gotenberg base URL for this invocation.", "zh-TW": "--engine word-com、libreoffice 或 gotenberg 會要求使用指定的 DOCX 轉 PDF 引擎；明確指定時絕不 fallback。--mode 選擇自動政策：desktop、server、container、strict-word 或 strict-libreoffice。修訂模式可用 --revisions final、original 或 markup；註解模式可用 --comments omit、appendix 或 markup，但仍取決於引擎支援。--timeout 單位為秒。HTML 與 Markdown 可用 --orientation portrait 或 landscape 選擇 A4 版面。--gotenberg-url 為本次呼叫提供 Gotenberg base URL。" }, code: "gordon-doc convert contract.docx --engine word-com --revisions final --comments appendix\ngordon-doc convert report.html --to pdf --orientation landscape\ngordon-doc convert report.docx --mode server --gotenberg-url http://renderer:3000" },
      { id: "structured-artifacts", title: { en: "Structured YAML and JSON artifacts", "zh-TW": "結構化 YAML 與 JSON Artifact" }, body: { en: "--to yaml and --to json serialize the same versioned semantic document. Schema 1.3 keeps Markdown-like heading, paragraph, list, and table text while preserving meaningful links, images, revisions, annotations, source order, metadata, and reverse locators. Repeat --to to extract once and write both formats. --metadata accepts none, basic, or layout; optional values with no data are omitted rather than written as null. --to json writes a document artifact, while the separate --json flag writes the CLI result contract to stdout.", "zh-TW": "--to yaml 與 --to json 會序列化同一份具版本的語意文件。Schema 1.3 保留接近 Markdown 的標題、段落、清單及表格文字，同時保存有意義的連結、圖片、修訂、註解、來源順序、metadata 與反向 locator。重複使用 --to 可只擷取一次並同時寫出兩種格式。--metadata 接受 none、basic 或 layout；沒有資料的選用值會直接省略，不會輸出 null。--to json 產生文件 artifact；不同用途的 --json 則將 CLI 執行結果寫到 stdout。" }, code: "gordon-doc convert report.docx --to yaml --to json --metadata basic\ngordon-doc convert report.pdf --to yaml --to json --metadata layout\ngordon-doc convert report.docx --to json --json" },
      { id: "source-anchors", title: { en: "Reverse location and source verification", "zh-TW": "反向定位與來源驗證" }, body: { en: "Structured artifacts identify the exact input with source.sha256 and verify each normalized block or table cell with source_anchor.content_sha256. DOCX anchors use the OOXML part and element path, with a native paragraph ID when Word supplies one; table cells extend the path with row and cell indexes. PDF anchors use the one-based physical page. PDF page coordinates are not yet available and can be added by a future layout provider. File offsets are not stable locators: DOCX recompression and PDF optimization or incremental saves change them without changing the visible content.", "zh-TW": "結構化 artifact 以 source.sha256 識別完全相同的輸入檔，並以 source_anchor.content_sha256 驗證每個正規化 block 或表格儲存格。DOCX anchor 使用 OOXML part 與 element path；Word 有提供時另含原生段落 ID，表格儲存格則在 path 加上 row/cell 索引。PDF anchor 使用從 1 起算的實體頁。PDF 頁內座標目前尚未提供，未來可由 layout provider 擴充。file offset 並非穩定 locator：DOCX 重新壓縮，以及 PDF 最佳化或增量儲存，都可能在可見內容不變時改變 offset。" }, table: { caption: { en: "Reverse locator fields", "zh-TW": "反向定位欄位" }, headers: { en: ["Field", "Purpose"], "zh-TW": ["欄位", "用途"] }, rows: { en: [["source.sha256", "Confirm the exact source file version"], ["source_anchor.locator", "Select ooxml-element, ooxml-table-cell, or pdf-page"], ["part + element_path", "Locate a DOCX element inside word/document.xml"], ["native_id", "Use Word paraId when the source provides it"], ["page_number", "Locate a PDF block on a one-based physical page"], ["content_sha256", "Verify normalized text after locating the source"]], "zh-TW": [["source.sha256", "確認完全相同的來源檔案版本"], ["source_anchor.locator", "選擇 ooxml-element、ooxml-table-cell 或 pdf-page"], ["part + element_path", "定位 word/document.xml 內的 DOCX element"], ["native_id", "來源有提供時使用 Word paraId"], ["page_number", "以從 1 起算的實體頁定位 PDF block"], ["content_sha256", "定位來源後驗證正規化文字"]] }, legend: { en: ["Optional locator fields appear only when they apply to the source format."], "zh-TW": ["選用定位欄位只會在適用於來源格式時出現。"] }, alignLeft: true, firstColumnWidth: "wide" } },
      { id: "progress", title: { en: "Conversion progress", "zh-TW": "轉換進度" }, body: { en: "convert and batch show phase-based progress automatically on interactive terminals. Progress is emitted only on stderr, so redirected stdout and machine-readable results remain clean. --json disables automatic progress; use --progress to force it or --no-progress to suppress it. Batch progress reports completed files over total files rather than an invented time percentage.", "zh-TW": "convert 與 batch 在互動終端會自動顯示階段式進度。進度只寫入 stderr，因此重導向的 stdout 與機器可讀結果不會被污染。--json 會關閉自動進度；可用 --progress 強制顯示，或用 --no-progress 關閉。batch 顯示已完成檔案數／總檔案數，而非虛構的時間百分比。" }, code: "gordon-doc convert report.docx --to yaml --progress\ngordon-doc convert report.docx --to json --no-progress\ngordon-doc batch one.docx two.docx --output-dir converted --progress" },
      { id: "images-template", title: { en: "Page images and HTML template", "zh-TW": "頁面影像與 HTML 範本" }, body: { en: "Use --to images to rasterize a PDF source or the PDF produced from a DOCX source. --dpi accepts 1 through 600; --image-format is png or jpeg; --quality applies to JPEG; repeat --page with one-based page numbers to select pages; --background sets the image background colour. Image output is a directory named <stem>.pages containing numbered files. template writes an editable A4 HTML starting point and protects existing files unless --overwrite is supplied.", "zh-TW": "使用 --to images 將 PDF 來源，或由 DOCX 產生的 PDF，轉為頁面影像。--dpi 可設 1 至 600；--image-format 為 png 或 jpeg；--quality 套用於 JPEG；可重複使用 --page（從 1 起算）選擇頁面；--background 設定影像背景色。影像輸出為名為 <stem>.pages 的目錄，內含連號檔案。template 會建立可編輯的 A4 HTML 起始範本；除非提供 --overwrite，否則會保護既有檔案。" }, code: "gordon-doc convert report.pdf --to images --image-format jpeg --quality 85 --page 1 --page 3\ngordon-doc template report.html --orientation landscape" },
      { id: "compare-batch", title: { en: "Compare PDFs and convert batches", "zh-TW": "比較 PDF 與批次轉換" }, body: { en: "compare examines PDF structure, fonts, sizes, and rendered pixels. Set --diff-dir to save PNGs for pages that differ, and use --dpi to control comparison raster resolution. batch converts one or more DOCX files sequentially, isolating each file failure; it always targets PDF. --output-dir stores each generated PDF in the chosen directory. The batch exit code is non-zero when any item fails, while --json retains every item result for CI reporting.", "zh-TW": "compare 會檢查 PDF 結構、字型、大小與渲染後的像素。可設定 --diff-dir 儲存不同頁面的 PNG，並以 --dpi 控制比較的點陣解析度。batch 會依序轉換一或多個 DOCX，並隔離各檔案失敗；其輸出固定為 PDF。--output-dir 將每個產生的 PDF 放進指定目錄。只要任何項目失敗，batch 的 exit code 就會是非零；--json 則保留完整的逐項結果供 CI 報告使用。" }, code: "gordon-doc compare expected.pdf actual.pdf --diff-dir differences --json\ngordon-doc batch one.docx two.docx --output-dir converted --mode server --json" },
      { id: "automation", title: { en: "JSON results and exit codes", "zh-TW": "JSON 結果與 Exit Code" }, body: { en: "All commands accept --json. Successful conversion payloads include the selected and attempted engines, artifact paths and metadata, duration, effective annotation modes, warnings, and fallback information. Failures include a stable error code, safe message, engine when known, and retryable flag. Exit code 0 means success; 2 means invalid input or output already exists; 3 means engine/capability unavailable; 4 means conversion failed, timed out, or produced no output; and 5 means PDF validation failed.", "zh-TW": "所有指令均接受 --json。成功轉換的 payload 包含選用與嘗試過的引擎、artifact 路徑與中繼資料、耗時、實際採用的註解模式、warning 與 fallback 資訊。失敗結果包含穩定的錯誤碼、安全訊息、可得時的引擎名稱與 retryable 旗標。exit code 0 表示成功；2 表示輸入無效或輸出已存在；3 表示引擎／能力不可用；4 表示轉換失敗、逾時或無輸出；5 表示 PDF 驗證失敗。" }, code: "gordon-doc convert report.docx --json\n# PowerShell: stop a script if conversion fails\ngordon-doc convert report.docx --output report.pdf\nif ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }" },
    ],
  },
  {
    id: "library",
    category: "getting-started",
    title: { en: "Python library", "zh-TW": "Python 函式庫" },
    summary: { en: "Embed typed conversion requests, results, batches, and diagnostics in Python applications.", "zh-TW": "在 Python 應用程式中整合具型別的轉換請求、結果、批次與診斷。" },
    sections: [
      { id: "library-overview", title: { en: "Library overview", "zh-TW": "函式庫總覽" }, body: { en: "The public API uses engine-neutral typed models. Choose the smallest entry point that meets the integration need.", "zh-TW": "公開 API 使用引擎中立的具型別模型。請依整合需求選擇最精簡的入口。" }, table: { caption: { en: "Python library entry points", "zh-TW": "Python 函式庫入口" }, headers: { en: ["Entry point", "Use it for"], "zh-TW": ["入口", "適用情境"] }, rows: { en: [["ConversionRequest.from_source", "Infer and validate source format from a path"], ["convert(request)", "Run one conversion and receive ConversionResult"], ["DocumentConversionService", "Inject engines or use service methods directly"], ["convert_batch(requests)", "Run sequential, failure-isolated conversions"], ["probe_engines()", "Discover renderer availability and annotation capabilities"], ["result.to_dict()", "Produce stable JSON-compatible result data"]], "zh-TW": [["ConversionRequest.from_source", "由路徑推斷並驗證來源格式"], ["convert(request)", "執行單一轉換並取得 ConversionResult"], ["DocumentConversionService", "注入引擎，或直接使用 service 方法"], ["convert_batch(requests)", "執行依序且失敗隔離的轉換"], ["probe_engines()", "探索 renderer 可用性與註解能力"], ["result.to_dict()", "產生穩定、JSON 相容的結果資料"]] }, legend: { en: ["Use ConversionOptions to set policy and output behaviour."], "zh-TW": ["使用 ConversionOptions 設定政策與輸出行為。"] }, alignLeft: true, firstColumnWidth: "wide" } },
      { id: "library-single", title: { en: "Single conversion", "zh-TW": "單檔轉換" }, body: { en: "ConversionRequest.from_source validates the allowlisted extension and infers the source format. convert returns a ConversionResult rather than raising for ordinary conversion failures, so inspect success and error before reading artifacts. ConversionError is reserved for invalid requests and related contract errors.", "zh-TW": "ConversionRequest.from_source 會驗證允許的副檔名並推斷來源格式。convert 對一般轉換失敗會回傳 ConversionResult，而非直接拋出例外，因此讀取 artifacts 前請先檢查 success 與 error。ConversionError 用於無效請求及相關契約錯誤。" }, code: "from pathlib import Path\nfrom gordon_doc_converter import ConversionRequest, convert\n\nresult = convert(ConversionRequest.from_source(Path('report.docx')))\nif not result.success:\n    raise RuntimeError(result.error.message if result.error else 'conversion failed')\nprint(result.artifacts[0].path)" },
      { id: "library-options", title: { en: "Options and strict policy", "zh-TW": "選項與嚴格政策" }, body: { en: "Use ConversionOptions to choose output paths, overwrite behaviour, timeout, deployment mode, an explicit engine, annotation handling, metadata detail, and image settings. EngineName is strict: an unavailable explicitly chosen engine produces a diagnosable failure rather than a silent alternative. ArtifactType can request PDF, DOCX, ODT, HTML, Markdown, YAML, JSON, or page images where the route supports it.", "zh-TW": "使用 ConversionOptions 設定輸出路徑、覆寫行為、逾時、部署模式、明確引擎、註解處理、metadata detail 與影像設定。EngineName 是嚴格選擇：指定的引擎不可用時，會得到可診斷的失敗，而不是靜默改用其他引擎。若轉換路徑支援，ArtifactType 可要求 PDF、DOCX、ODT、HTML、Markdown、YAML、JSON 或頁面影像。" }, code: "from pathlib import Path\nfrom gordon_doc_converter import (\n    ArtifactType, ConversionOptions, ConversionRequest, convert,\n)\n\nrequest = ConversionRequest.from_source(\n    Path('report.docx'),\n    artifacts=(ArtifactType.YAML, ArtifactType.JSON),\n    options=ConversionOptions(output_path=Path('report')),\n)\nresult = convert(request)" },
      { id: "library-service", title: { en: "Batches, probes, and result handling", "zh-TW": "批次、探測與結果處理" }, body: { en: "DocumentConversionService supports dependency injection for engines and environment-aware orchestration. convert_batch processes requests sequentially and keeps failures isolated. probe_engines returns EngineProbeResult entries with availability, version, supported revision modes, and comment modes. Results serialize through to_dict() to stable JSON-compatible primitives for logs or APIs; do not log document contents or sensitive paths.", "zh-TW": "DocumentConversionService 支援引擎的 dependency injection 與依環境執行的 orchestration。convert_batch 會依序處理請求並隔離失敗。probe_engines 回傳 EngineProbeResult，包含可用性、版本、支援的修訂模式與註解模式。結果可透過 to_dict() 序列化為穩定、JSON 相容的基本型別，適合日誌或 API；請勿記錄文件內容或敏感路徑。" }, code: "from gordon_doc_converter import DocumentConversionService\n\nservice = DocumentConversionService()\nfor probe in service.probe_engines():\n    print(probe.engine, probe.available, probe.version)\n\nresults = service.convert_batch(requests)\npayload = [result.to_dict() for result in results]" },
    ],
  },
  {
    id: "api",
    category: "getting-started",
    title: { en: "HTTP API", "zh-TW": "HTTP API" },
    summary: { en: "Run the authenticated FastAPI adapter and explore its OpenAPI contract.", "zh-TW": "啟動具認證的 FastAPI adapter，並瀏覽其 OpenAPI 契約。" },
    sections: [
      { id: "api-overview", title: { en: "API overview", "zh-TW": "API 總覽" }, body: { en: "The private HTTP adapter exposes a deliberately small DOCX-to-PDF surface. Use the endpoints below for conversion, diagnostics, and deployment health checks.", "zh-TW": "私有 HTTP adapter 刻意提供精簡的 DOCX 轉 PDF 介面。請使用下表端點執行轉換、診斷與部署健康檢查。" }, table: { caption: { en: "HTTP API endpoints", "zh-TW": "HTTP API 端點" }, headers: { en: ["Endpoint", "Authentication", "Purpose"], "zh-TW": ["端點", "認證", "用途"] }, rows: { en: [["POST /conversions", "Bearer token", "Convert uploaded DOCX bytes to a PDF"], ["GET /engines", "Bearer token", "List configured renderer capabilities"], ["GET /live", "None", "Confirm the process is alive"], ["GET /ready", "None", "Check that the default renderer is ready"], ["GET /version", "None", "Return the package version"]], "zh-TW": [["POST /conversions", "Bearer token", "將上傳的 DOCX 位元組轉換為 PDF"], ["GET /engines", "Bearer token", "列出已設定 renderer 的能力"], ["GET /live", "無", "確認程序仍在運行"], ["GET /ready", "無", "確認預設 renderer 是否就緒"], ["GET /version", "無", "回傳套件版本"]] }, legend: { en: ["Protected endpoints require Authorization: Bearer <api-key> when an API key is configured."], "zh-TW": ["設定 API key 時，受保護端點必須提供 Authorization: Bearer <api-key>。"] }, alignLeft: true, firstColumnWidth: "w48", secondColumnWidth: "w40" } },
      {
        id: "start-api",
        title: { en: "Start the API", "zh-TW": "啟動 API" },
        body: {
          en: "Install the optional API dependencies, set a strong API key, and run the application factory on port 8000.",
          "zh-TW": "安裝選用的 API 相依套件、設定高強度 API key，並在 8000 port 啟動 application factory。",
        },
        code: "uv sync --extra api\n$env:GORDON_DOC_API_KEY = \"replace-me\"\nuv run uvicorn gordon_doc_converter.api.app:create_app --factory --host 127.0.0.1 --port 8000",
        note: {
          en: "The environment-variable example uses PowerShell. Keep this API private and do not commit API keys.",
          "zh-TW": "環境變數範例使用 PowerShell。此 API 應維持私有部署，且請勿提交 API key。",
        },
      },
      {
        id: "api-convert",
        title: { en: "Convert a document", "zh-TW": "轉換文件" },
        body: {
          en: "POST /conversions accepts only a DOCX request body and returns application/pdf. Send the original basename in X-Filename, the DOCX OOXML MIME type in Content-Type, and a Bearer token when an API key is configured. The optional engine query parameter accepts libreoffice or gotenberg; Word COM is deliberately unavailable through the API. The server stages the upload in a temporary directory, validates the OOXML package and limits, calls the configured malware-scan hook, and deletes temporary files before the response returns.",
          "zh-TW": "POST /conversions 只接受 DOCX request body，並回傳 application/pdf。請在 X-Filename 傳送原始檔名、在 Content-Type 傳送 DOCX 的 OOXML MIME type；設定 API key 時另須 Bearer token。選用的 engine query parameter 接受 libreoffice 或 gotenberg；API 刻意不提供 Word COM。伺服器會將上傳暫存於臨時目錄、驗證 OOXML package 與限制、呼叫設定的惡意程式掃描 hook，並在回應前刪除暫存檔。",
        },
        code: "curl --fail-with-body \\\n  -H \"Authorization: Bearer replace-me\" \\\n  -H \"Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\" \\\n  -H \"X-Filename: report.docx\" \\\n  --data-binary @report.docx \\\n  \"http://127.0.0.1:8000/conversions?engine=libreoffice\" \\\n  --output report.pdf",
        note: {
          en: "The HTTP adapter is intentionally narrower than the library and CLI: it exposes authenticated DOCX-to-PDF conversion only. Keep it behind private network controls and TLS in production.",
          "zh-TW": "HTTP adapter 刻意比函式庫與 CLI 窄：只提供經認證的 DOCX 轉 PDF。正式環境請將它放在私有網路控制與 TLS 後方。",
        },
      },
      {
        id: "api-documentation",
        title: { en: "Interactive API documentation", "zh-TW": "互動式 API 文件" },
        body: {
          en: "The documentation site publishes the generated OpenAPI 3.1 contract and a bundled, read-only Swagger UI. You can inspect the JSON in your browser or download it for code generation and validation tools.",
          "zh-TW": "文件站會發布產生的 OpenAPI 3.1 契約與內建的唯讀 Swagger UI。你可以在瀏覽器檢視 JSON，或下載後交由程式碼產生與驗證工具使用。",
        },
        links: [
          {
            label: { en: "View OpenAPI JSON", "zh-TW": "檢視 OpenAPI JSON" },
            href: "./openapi.json",
          },
          {
            label: { en: "Download OpenAPI JSON", "zh-TW": "下載 OpenAPI JSON" },
            href: "./openapi.json",
            download: true,
          },
          {
            label: { en: "Open Swagger UI", "zh-TW": "開啟 Swagger UI" },
            href: "./swagger/",
          },
        ],
        note: {
          en: "The hosted Swagger UI is read-only. Use the API server's /docs page when you need Try it out against a configured private deployment.",
          "zh-TW": "託管的 Swagger UI 採唯讀模式。如需對已設定的私有部署使用 Try it out，請開啟 API server 本身的 /docs。",
        },
      },
      {
        id: "api-endpoints",
        title: { en: "Available endpoints", "zh-TW": "可用端點" },
        body: {
          en: "The specification describes document conversion, engine discovery, health, readiness, and version endpoints. Protected requests use a Bearer token.",
          "zh-TW": "規格包含文件轉換、引擎探索、存活檢查、就緒檢查與版本端點。受保護的 request 使用 Bearer token。",
        },
        code: "# Protected: requires Authorization: Bearer <api-key>\nPOST /conversions?engine=libreoffice|gotenberg\nGET  /engines\n\n# Unprotected operational metadata\nGET  /live     # {\"status\": \"ok\"}\nGET  /ready    # 200 ready, 503 not-ready\nGET  /version  # {\"version\": \"0.5.1\"}",
      },
      {
        id: "api-status-errors",
        title: { en: "Status codes and operational limits", "zh-TW": "狀態碼與作業限制" },
        body: {
          en: "A successful conversion returns 200 with a PDF attachment. Invalid engine choices or input return 400; missing or invalid credentials return 401; an oversized source returns 413; renderer failures return 422; exhausted rate or concurrency capacity returns 429; internal staging or service faults return 500; and unavailable authentication or malware scanning returns 503. /ready checks the configured default engine rather than merely reporting that the process is alive. The built-in fixed-window rate limit and concurrency limit are process-local, so production deployments with multiple replicas must enforce distributed limits at the ingress or gateway too.",
          "zh-TW": "成功轉換會以 200 回傳 PDF attachment。無效引擎或輸入回傳 400；缺少或無效憑證回傳 401；來源超過大小限制回傳 413；renderer 失敗回傳 422；速率或並行容量耗盡回傳 429；內部暫存或服務錯誤回傳 500；認證或惡意程式掃描服務不可用回傳 503。/ready 會檢查設定的預設引擎，而非只確認程序仍存活。內建的固定視窗速率限制與並行限制只在單一 process 內有效，因此多副本的正式部署還須在 ingress 或 gateway 提供分散式限制。",
        },
      },
      {
        id: "api-configuration", title: { en: "Configuration and integration hooks", "zh-TW": "設定與整合 Hooks" }, body: { en: "create_app accepts ApiSettings or environment defaults. GORDON_DOC_API_KEY enables the default constant-time Bearer-token comparison. GORDON_DOC_GOTENBERG_URL configures a Gotenberg adapter and makes Gotenberg the default engine; otherwise LibreOffice is used. ApiSettings also controls conversion timeout, maximum concurrent conversions, fixed-window request rate, and input limits. Supply auth_hook, malware_scan_hook, and telemetry_hook when integrating private identity, scanning, or observability systems. Telemetry receives content-free fields only; never emit document contents, credentials, or customer paths.", "zh-TW": "create_app 可接受 ApiSettings 或使用環境預設值。GORDON_DOC_API_KEY 會啟用預設的常數時間 Bearer-token 比對。GORDON_DOC_GOTENBERG_URL 會設定 Gotenberg adapter，並令其成為預設引擎；否則使用 LibreOffice。ApiSettings 也控制轉換逾時、最大並行轉換數、固定視窗請求速率與輸入限制。整合私有身分、掃描或可觀測性系統時，請提供 auth_hook、malware_scan_hook 與 telemetry_hook。Telemetry 僅接收不含內容的欄位；切勿輸出文件內容、憑證或客戶路徑。" }, code: "from gordon_doc_converter.api.app import ApiSettings, create_app\n\napp = create_app(settings=ApiSettings(\n    api_key='read-from-a-secret-store',\n    timeout_seconds=120,\n    max_concurrent_conversions=2,\n    rate_limit_requests=30,\n    rate_limit_window_seconds=60,\n))" },
    ],
  },
  {
    id: "architecture",
    category: "development",
    title: { en: "Architecture", "zh-TW": "系統架構" },
    summary: { en: "Understand the boundaries that keep conversion portable and testable.", "zh-TW": "理解維持轉換流程可攜且可測試的架構邊界。" },
    sections: [
      { id: "dependency-flow", title: { en: "Dependency flow", "zh-TW": "相依流向" }, body: { en: "Library and CLI callers enter through the application service. The orchestrator applies policy before invoking a shared engine protocol and validating the resulting PDF.", "zh-TW": "函式庫與 CLI 呼叫皆進入 application service，由 orchestrator 套用政策後，再呼叫共用 engine protocol 並驗證產出的 PDF。" }, code: "Library / CLI\n  -> Application service\n  -> Orchestrator and policy\n  -> Engine protocol\n  -> PDF validation" },
      { id: "adapter-rules", title: { en: "Adapter rules", "zh-TW": "Adapter 規則" }, body: { en: "Platform APIs and subprocesses stay inside engine adapters. Windows-only dependencies are imported lazily so the core package remains portable.", "zh-TW": "平台 API 與 subprocess 限制在引擎 adapter 內。Windows 專用相依套件採延遲匯入，確保核心套件維持跨平台。" } },
    ],
  },
  {
    id: "contributing",
    category: "development",
    title: { en: "Contributing", "zh-TW": "參與開發" },
    summary: { en: "Set up the repository and run the full quality suite.", "zh-TW": "設定開發環境並執行完整品質檢查。" },
    sections: [
      { id: "setup", title: { en: "Local setup", "zh-TW": "本機設定" }, body: { en: "The project uses uv for reproducible Python dependency management.", "zh-TW": "專案使用 uv 管理可重現的 Python 相依套件。" }, code: "uv sync --dev --all-extras" },
      { id: "quality", title: { en: "Quality checks", "zh-TW": "品質檢查" }, body: { en: "Format, lint, type-check, and test before opening a pull request.", "zh-TW": "提出 Pull Request 前，請完成格式化、lint、型別檢查與測試。" }, code: "uv run ruff format --check .\nuv run ruff check .\nuv run mypy src\nuv run pytest" },
    ],
  },
  {
    id: "deployment",
    category: "operations",
    title: { en: "Deployment modes", "zh-TW": "部署模式" },
    summary: { en: "Choose an engine policy that matches desktop, server, or container execution.", "zh-TW": "依桌面、伺服器或容器環境選擇適合的引擎政策。" },
    sections: [
      { id: "desktop", title: { en: "Desktop", "zh-TW": "桌面模式" }, body: { en: "Interactive Windows desktops may automatically select Word COM when licensed Word is available.", "zh-TW": "互動式 Windows 桌面在具備合法授權 Word 時，可自動選用 Word COM。" } },
      { id: "server-container", title: { en: "Server and container", "zh-TW": "伺服器與容器" }, body: { en: "Server mode prefers Gotenberg then LibreOffice. The container includes LibreOffice and can use an external Gotenberg service; it never auto-selects Word COM.", "zh-TW": "伺服器模式依序偏好 Gotenberg、LibreOffice。容器內含 LibreOffice，也可使用外部 Gotenberg service，且絕不自動選用 Word COM。" }, note: { en: "Rendering may differ between Word and LibreOffice. Test representative documents before rollout.", "zh-TW": "Word 與 LibreOffice 的排版可能不同，正式上線前應以代表性文件測試。" } },
    ],
  },
  {
    id: "containers",
    category: "operations",
    title: { en: "Containers", "zh-TW": "容器化" },
    summary: { en: "Use one hardened image for one-off CLI work, a self-contained API, or remote Gotenberg rendering.", "zh-TW": "以單一強化映像支援單次 CLI 作業、完整單體 API 或遠端 Gotenberg 排版。" },
    sections: [
      { id: "profiles", title: { en: "Choose a profile", "zh-TW": "選擇 Profile" }, body: { en: "Every Compose service is opt-in and uses the same GordonKit image. Use cli for local commands, standalone-lo for the API with included LibreOffice, or gateway-gotenberg for the API backed by a separate renderer.", "zh-TW": "所有 Compose service 都必須明確選用，且共用同一個 GordonKit 映像。cli 適合本機命令；standalone-lo 使用內建 LibreOffice；gateway-gotenberg 則讓 API 搭配獨立排版服務。" }, note: { en: "Always pass --profile. Running compose up without a profile starts no services.", "zh-TW": "務必傳入 --profile；未指定 profile 時，compose up 不會啟動任何服務。" } },
      { id: "cli-profile", title: { en: "CLI profile", "zh-TW": "CLI Profile" }, body: { en: "CLI mode uses included LibreOffice and mounts the current directory at /work. It is suited to local, one-off conversions without running an HTTP service.", "zh-TW": "CLI 模式使用內建 LibreOffice，並將目前目錄掛載至 /work，適合不啟動 HTTP service 的本機單次轉換。" }, code: "docker compose -f docker/compose.yaml --profile cli run --rm cli convert /work/report.docx --output /work/report.pdf" },
      { id: "standalone-profile", title: { en: "Standalone LibreOffice API", "zh-TW": "單體 LibreOffice API" }, body: { en: "Run the authenticated API and LibreOffice in one container when simple deployment and local rendering matter more than independent renderer scaling.", "zh-TW": "需要簡單部署與本機排版，且不需獨立擴展 renderer 時，可在同一容器執行具認證的 API 與 LibreOffice。" }, code: "# .env\nGORDON_DOC_API_KEY=replace-me\n\ndocker compose -f docker/compose.yaml --env-file .env --profile standalone-lo up --build" },
      { id: "gateway-profile", title: { en: "Gotenberg gateway", "zh-TW": "Gotenberg Gateway" }, body: { en: "Run the API with a separate Gotenberg service when renderer isolation and independent service health are preferred. Compose connects both services to the gordon-doc network and waits for Gotenberg to become healthy. Configuring the Gotenberg URL explicitly selects that engine; failures do not silently fall back to LibreOffice.", "zh-TW": "偏好 renderer 隔離與獨立服務健康狀態時，可讓 API 搭配個別 Gotenberg service；Compose 會將兩者連至 gordon-doc network，並等待 Gotenberg 健康後再啟動 API。設定 Gotenberg URL 代表明確選用該引擎；失敗時不會靜默改用 LibreOffice。" }, code: "docker compose -f docker/compose.yaml --env-file .env --profile gateway-gotenberg up --build" },
      { id: "published-image", title: { en: "Published image", "zh-TW": "正式發布映像" }, body: { en: "Tagged releases publish one linux/amd64 image at gordonkit/gordon-doc-converter. The default entrypoint runs the CLI; pass api to start the HTTP service. Prefer an explicit version tag for reproducible deployments.", "zh-TW": "正式版本會發布單一 linux/amd64 映像至 gordonkit/gordon-doc-converter。預設 entrypoint 執行 CLI；傳入 api 則啟動 HTTP service。需要可重現部署時，請使用明確版本 tag。" }, code: "docker run --rm gordonkit/gordon-doc-converter:0.5.1 version\ndocker run --rm -p 8000:8000 -e GORDON_DOC_API_KEY=replace-me gordonkit/gordon-doc-converter:0.5.1 api" },
      { id: "health", title: { en: "Operations and security", "zh-TW": "維運與安全" }, body: { en: "All profiles run as a non-root user with a read-only root filesystem, a bounded temporary filesystem, and no-new-privileges. API profiles require a strong key; production ingress must also enforce request-size and distributed rate limits.", "zh-TW": "所有 profile 都以非 root 使用者、唯讀 root filesystem、有限 tmpfs 與 no-new-privileges 執行。API profile 必須使用高強度 key；正式環境 ingress 也應限制 request 大小並提供分散式 rate limit。" }, code: "python docker/smoke.py --token replace-me --docx sample.docx", note: { en: "Do not commit the .env file or customer documents. The smoke client checks liveness, authenticated engine discovery, and optionally an end-to-end PDF conversion.", "zh-TW": "請勿提交 .env 或客戶文件。Smoke client 會檢查存活狀態、經認證的引擎探索，以及選用的端到端 PDF 轉換。" } },
    ],
  },
  {
    id: "roadmap",
    category: "project",
    title: { en: "Roadmap", "zh-TW": "產品藍圖" },
    summary: { en: "Track the stable core and intentionally staged delivery areas.", "zh-TW": "掌握穩定核心與分階段交付範圍。" },
    sections: [
      { id: "current", title: { en: "Current scope", "zh-TW": "目前範圍" }, body: { en: "The core library, CLI, conversion adapters, semantic artifacts, comparison tools, authenticated API adapter, and container profiles are available.", "zh-TW": "目前已提供核心函式庫、CLI、轉換 adapters、語意 artifacts、比較工具、具認證的 API adapter 與容器 profiles。" } },
      { id: "principles", title: { en: "Project principles", "zh-TW": "專案原則" }, body: { en: "GordonKit favors explicit policy, portable contracts, isolated external processes, and diagnostic results over hidden convenience.", "zh-TW": "GordonKit 重視明確政策、可攜契約、隔離外部程序與可診斷結果，不以隱藏行為換取表面便利。" } },
    ],
  },
  {
    id: "security",
    category: "project",
    title: { en: "Security", "zh-TW": "安全性" },
    summary: { en: "Handle documents and execution environments as untrusted input.", "zh-TW": "將文件與執行環境視為不受信任輸入。" },
    sections: [
      { id: "input", title: { en: "Input handling", "zh-TW": "輸入處理" }, body: { en: "Validate extensions, MIME types, and OOXML structure. Apply size and decompression limits before processing untrusted documents.", "zh-TW": "驗證副檔名、MIME type 與 OOXML 結構；處理不受信任文件前套用大小與解壓縮限制。" } },
      { id: "reporting", title: { en: "Report a vulnerability", "zh-TW": "回報漏洞" }, body: { en: "Use the private reporting process described in SECURITY.md. Do not disclose sensitive document samples in public issues.", "zh-TW": "請依 SECURITY.md 的私密流程回報，勿在公開 issue 揭露敏感文件樣本。" } },
    ],
  },
];
