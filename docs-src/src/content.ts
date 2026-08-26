export type Locale = "en" | "zh-TW" | "ja";

export type Section = {
  id: string;
  title: Record<Locale, string>;
  body: Record<Locale, string>;
  bodyLink?: {
    label: Record<Locale, string>;
    href: string;
  };
  code?: string;
  bullets?: Record<Locale, string[]>;
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
  { id: "getting-started", label: { en: "Getting Started", "zh-TW": "快速開始", ja: "はじめに" } },
  { id: "development", label: { en: "Development", "zh-TW": "開發指南", ja: "開発" } },
  { id: "operations", label: { en: "Operations", "zh-TW": "維運部署", ja: "運用" } },
  { id: "project", label: { en: "Project", "zh-TW": "專案資訊", ja: "プロジェクト" } },
] as const;

export const pages: Page[] = [
  {
    id: "overview",
    category: "getting-started",
    title: { en: "Overview", "zh-TW": "總覽", ja: "概要" },
    heading: { en: "GordonKit Document Converter", "zh-TW": "GordonKit 文件轉換器", ja: "GordonKit ドキュメントコンバーター" },
    summary: {
      en: "Convert DOCX and other document formats to PDF, HTML, Markdown, images, and more through a Python library, CLI, or HTTP API.",
      "zh-TW": "將 DOCX 與其他文件格式轉換為 PDF、HTML、Markdown、圖片等格式，並可透過 Python 函式庫、CLI 或 HTTP API 使用。",
      ja: "DOCX をはじめとするドキュメント形式を、Python ライブラリ、CLI、HTTP API から PDF、HTML、Markdown、画像などへ変換します。",
    },
    sections: [
      {
        id: "about-project",
        title: { en: "About this project", "zh-TW": "關於此專案", ja: "このプロジェクトについて" },
        body: {
          en: "This open-source GordonKit project orchestrates Microsoft Word, LibreOffice, Gotenberg, or Pandoc for document rendering. It keeps engine selection, validation, fallback reporting, and conversion results explicit and diagnosable.",
          "zh-TW": "此 GordonKit 開源專案負責協調 Microsoft Word、LibreOffice、Gotenberg 或 Pandoc 進行文件排版，並讓引擎選擇、驗證、fallback 報告與轉換結果保持明確且可診斷。",
          ja: "この GordonKit オープンソースプロジェクトは、Microsoft Word、LibreOffice、Gotenberg、Pandoc を組み合わせてドキュメントを組版します。エンジンの選択、検証、フォールバックの報告、変換結果を明示的で診断しやすい状態に保ちます。",
        },
        bodyLink: {
          label: { en: "open-source GordonKit project", "zh-TW": "GordonKit 開源專案", ja: "GordonKit オープンソースプロジェクト" },
          href: "https://github.com/gordonkit/gordon-doc-converter",
        },
      },
      {
        id: "interfaces",
        title: { en: "Ways to use it", "zh-TW": "使用介面", ja: "利用方法" },
        body: {
          en: "Choose the interface that fits your workflow. Every interface enters through the same application service and preserves structured results, engine policy, and diagnostics.",
          "zh-TW": "依工作流程選擇適合的介面。所有介面都透過同一個 application service，並保留結構化結果、引擎政策與診斷資訊。",
          ja: "ワークフローに合った利用方法を選べます。どの方法も同じ application service を経由し、構造化された結果、エンジンポリシー、診断情報を保持します。",
        },
        interfaces: [
          {
            title: { en: "Python Library", "zh-TW": "Python 函式庫", ja: "Python ライブラリ" },
            label: { en: "Application integration", "zh-TW": "應用程式整合", ja: "アプリケーション統合" },
            body: {
              en: "Use typed public contracts for single conversions, isolated batches, engine probes, and service injection.",
              "zh-TW": "使用具型別的公開契約，執行單檔轉換、隔離式批次、引擎探測與 service injection。",
              ja: "型付きの公開契約を使って、単一変換、独立したバッチ処理、エンジン調査、service injection を実行します。",
            },
            example: "from gordon_doc_converter import convert",
          },
          {
            title: { en: "CLI", "zh-TW": "CLI", ja: "CLI" },
            label: { en: "Terminal and automation", "zh-TW": "終端機與自動化", ja: "ターミナルと自動化" },
            body: {
              en: "Convert, compare, inspect engines, and emit stable JSON results for scripts and CI workflows.",
              "zh-TW": "執行轉換、比較與引擎檢查，並輸出穩定 JSON 結果供 script 與 CI 流程使用。",
              ja: "変換、比較、エンジン確認を実行し、スクリプトや CI ワークフロー向けに安定した JSON 結果を出力します。",
            },
            example: "gordon-doc convert report.docx --to pdf",
          },
          {
            title: { en: "HTTP API", "zh-TW": "HTTP API", ja: "HTTP API" },
            label: { en: "Optional private adapter", "zh-TW": "選用的私有 Adapter", ja: "任意のプライベート Adapter" },
            body: {
              en: "Install the FastAPI extra for private deployments with authentication hooks, rate limits, and bounded concurrency.",
              "zh-TW": "安裝 FastAPI extra，建立具認證 hooks、流量限制與有限並行能力的私有部署。",
              ja: "FastAPI extra をインストールし、認証 hook、レート制限、上限付き並行実行を備えたプライベート配備を構築します。",
            },
            example: "POST /conversions",
          },
        ],
      },
      {
        id: "format-support",
        title: { en: "Format support", "zh-TW": "格式支援", ja: "対応フォーマット" },
        body: {
          en: "Use this matrix to see the project's primary conversion capabilities. Some routes require an optional engine or output package as noted.",
          "zh-TW": "下表整理本專案的主要轉換能力；部分路徑需安裝選用引擎或輸出套件，條件標示於表格中。",
          ja: "この表でプロジェクトの主な変換機能を確認できます。一部の変換経路では、表に記載のとおり任意のエンジンまたは出力パッケージが必要です。",
        },
        table: {
          caption: { en: "Supported input and output formats", "zh-TW": "支援的輸入與輸出格式", ja: "対応する入力および出力フォーマット" },
          headers: {
            en: ["Input", "DOCX", "PDF", "ODT", "HTML", "Markdown", "YAML", "JSON", "Images"],
            "zh-TW": ["輸入", "DOCX", "PDF", "ODT", "HTML", "Markdown", "YAML", "JSON", "頁圖"],
            ja: ["入力", "DOCX", "PDF", "ODT", "HTML", "Markdown", "YAML", "JSON", "ページ画像"],
          },
          rows: {
            en: [
              ["DOCX", "", "Auto", "LO", "✓", "✓", "✓", "✓", "PDF"],
              ["PDF", "—", "", "—", "✓", "✓", "✓", "✓", "✓"],
              ["ODT", "LO", "LO", "", "—", "—", "—", "—", "—"],
              ["HTML", "P", "P+", "—", "", "—", "—", "—", "—"],
              ["Markdown", "P", "P+", "—", "—", "", "—", "—", "—"],
            ],
            "zh-TW": [
              ["DOCX", "", "Auto", "LO", "✓", "✓", "✓", "✓", "PDF"],
              ["PDF", "—", "", "—", "✓", "✓", "✓", "✓", "✓"],
              ["ODT", "LO", "LO", "", "—", "—", "—", "—", "—"],
              ["HTML", "P", "P+", "—", "", "—", "—", "—", "—"],
              ["Markdown", "P", "P+", "—", "—", "", "—", "—", "—"],
            ],
            ja: [
              ["DOCX", "", "Auto", "LO", "✓", "✓", "✓", "✓", "PDF"],
              ["PDF", "—", "", "—", "✓", "✓", "✓", "✓", "✓"],
              ["ODT", "LO", "LO", "", "—", "—", "—", "—", "—"],
              ["HTML", "P", "P+", "—", "", "—", "—", "—", "—"],
              ["Markdown", "P", "P+", "—", "—", "", "—", "—", "—"],
            ],
          },
          legend: {
            en: ["Auto Policy-based engine selection", "✓ Built in", "LO LibreOffice", "P Pandoc", "P+ Pandoc with PDF backend", "PDF Via intermediate PDF", "— Not supported", "Gray × Same format; disabled"],
            "zh-TW": ["Auto 依環境政策自動選擇引擎", "✓ 內建支援", "LO LibreOffice", "P Pandoc", "P+ Pandoc 與 PDF backend", "PDF 經由中間 PDF", "— 不支援", "灰底 × 相同格式，停用"],
            ja: ["Auto ポリシーに基づくエンジン選択", "✓ 標準対応", "LO LibreOffice", "P Pandoc", "P+ Pandoc と PDF backend", "PDF 中間 PDF 経由", "— 非対応", "グレー × 同一フォーマットのため無効"],
          },
        },
        bullets: {
          en: [
            "DOCX to PDF on interactive Windows: automatic mode prefers Word COM.",
            "DOCX to PDF on servers: automatic mode prefers Gotenberg, then LibreOffice.",
            "DOCX to PDF on other hosts: automatic mode prefers LibreOffice.",
            "DOCX to HTML: semantic extraction is the default. On a Windows desktop with Word COM available, Word rendering provides higher visual fidelity.",
            "Use --engine word-com to force Word COM HTML, or --mode server to force semantic extraction.",
            "Explicit engine and strict modes never fall back.",
            "Rendering may differ between engines.",
          ],
          "zh-TW": [
            "互動式 Windows 的 DOCX 轉 PDF：自動模式優先使用 Word COM。",
            "伺服器的 DOCX 轉 PDF：自動模式依序優先使用 Gotenberg、LibreOffice。",
            "其他主機的 DOCX 轉 PDF：自動模式優先使用 LibreOffice。",
            "DOCX 轉 HTML：預設使用語意萃取。在 Windows 桌面環境且 Word COM 可用時，透過 Word 排版可獲得更高的視覺忠實度。",
            "使用 --engine word-com 可強制使用 Word COM 輸出 HTML，使用 --mode server 則可強制使用語意萃取。",
            "明確指定引擎與 strict 模式絕不 fallback。",
            "不同引擎的排版結果可能有差異。",
          ],
          ja: [
            "対話的な Windows での DOCX から PDF：自動モードは Word COM を優先します。",
            "サーバーでの DOCX から PDF：自動モードは Gotenberg、次に LibreOffice を優先します。",
            "その他のホストでの DOCX から PDF：自動モードは LibreOffice を優先します。",
            "DOCX から HTML：既定はセマンティック抽出です。Word COM が利用できる Windows デスクトップでは、Word による組版のほうが視覚的な忠実度が高くなります。",
            "--engine word-com で Word COM による HTML 出力を強制でき、--mode server ではセマンティック抽出を強制できます。",
            "エンジンの明示指定と strict モードでは決してフォールバックしません。",
            "エンジンによって組版結果が異なる場合があります。",
          ],
        },
      },
      {
        id: "install",
        title: { en: "Install", "zh-TW": "安裝", ja: "インストール" },
        body: {
          en: "Install the core package, then add only the optional capabilities required by your deployment.",
          "zh-TW": "先安裝核心套件，再依部署需求加入選用能力。",
          ja: "まずコアパッケージをインストールし、配備に必要な任意機能だけを追加します。",
        },
        code: "uv add gordon-doc-converter\nuv add 'gordon-doc-converter[images,gotenberg]'",
      },
      {
        id: "first-conversion",
        title: { en: "First conversion", "zh-TW": "第一次轉換", ja: "最初の変換" },
        body: {
          en: "Create a request from a source path. The service selects an allowed engine, validates staged output, and publishes only after validation succeeds.",
          "zh-TW": "從來源路徑建立請求。服務會選擇政策允許的引擎、驗證暫存輸出，並只在驗證成功後發布。",
          ja: "ソースパスからリクエストを作成します。サービスはポリシーが許可するエンジンを選択し、一時出力を検証し、検証に成功した場合のみ結果を公開します。",
        },
        code: "from pathlib import Path\nfrom gordon_doc_converter import ConversionRequest, convert\n\nrequest = ConversionRequest.from_source(Path(\"report.docx\"))\nresult = convert(request)\nprint(result.artifacts[0].path)",
        note: {
          en: "Explicit engine selection is strict and never silently falls back.",
          "zh-TW": "明確指定引擎時採嚴格模式，絕不會靜默 fallback。",
          ja: "エンジンを明示指定した場合は strict 動作となり、暗黙のフォールバックは行いません。",
        },
      },
    ],
  },
  {
    id: "cli",
    category: "getting-started",
    title: { en: "CLI reference", "zh-TW": "CLI 指令參考", ja: "CLI リファレンス" },
    heading: { en: "Document conversion CLI reference", "zh-TW": "文件轉換 CLI 指令參考", ja: "ドキュメント変換 CLI リファレンス" },
    summary: { en: "Convert DOCX, PDF, ODT, HTML, and Markdown from the terminal with the gordon-doc CLI. Learn engine selection, batch conversion, JSON output, and PDF comparison.", "zh-TW": "使用 gordon-doc CLI 從終端機轉換 DOCX、PDF、ODT、HTML 與 Markdown，並了解引擎選擇、批次轉換、JSON 輸出及 PDF 比較。", ja: "gordon-doc CLI を使ってターミナルから DOCX、PDF、ODT、HTML、Markdown を変換し、エンジン選択、バッチ変換、JSON 出力、PDF 比較を学べます。" },
    sections: [
      { id: "cli-overview", title: { en: "Command overview", "zh-TW": "指令總覽", ja: "コマンド一覧" }, body: { en: "Start here to choose the command for your task. All commands support --json for machine-readable output.", "zh-TW": "請先從此表選擇適合工作的指令。所有指令都支援 --json，以輸出機器可讀的結果。", ja: "まずこの表からタスクに合ったコマンドを選びます。すべてのコマンドは機械可読な出力のための --json に対応しています。" }, table: { caption: { en: "CLI command overview", "zh-TW": "CLI 指令總覽", ja: "CLI コマンド一覧" }, headers: { en: ["Command", "Use it for"], "zh-TW": ["指令", "適用情境"], ja: ["コマンド", "用途"] }, rows: { en: [["doctor", "Check runtime health and renderer availability"], ["engines", "Inspect configured engines and capabilities"], ["convert", "Convert one DOCX, ODT, PDF, HTML, or Markdown file"], ["template", "Create an editable A4 HTML starter"], ["compare", "Compare two PDFs and optionally write visual diffs"], ["batch", "Convert multiple DOCX files with isolated failures"], ["version", "Print the installed package version"]], "zh-TW": [["doctor", "檢查執行環境健康狀態與 renderer 可用性"], ["engines", "查看已設定引擎及其能力"], ["convert", "轉換單一 DOCX、ODT、PDF、HTML 或 Markdown 檔案"], ["template", "建立可編輯的 A4 HTML 起始範本"], ["compare", "比較兩個 PDF，並可輸出視覺差異檔"], ["batch", "批次轉換多個 DOCX，且各檔案失敗互相隔離"], ["version", "印出已安裝套件版本"]], ja: [["doctor", "実行環境の健全性と renderer の利用可否を確認する"], ["engines", "設定済みエンジンとその機能を確認する"], ["convert", "DOCX、ODT、PDF、HTML、Markdown を 1 ファイル変換する"], ["template", "編集可能な A4 HTML の雛形を作成する"], ["compare", "2 つの PDF を比較し、必要に応じて差分画像を出力する"], ["batch", "複数の DOCX を変換し、失敗を個別に隔離する"], ["version", "インストール済みパッケージのバージョンを表示する"]] }, legend: { en: ["Run gordon-doc <command> --help for the installed command contract."], "zh-TW": ["請以 gordon-doc <command> --help 檢視目前安裝版本的指令契約。"], ja: ["インストール済みバージョンのコマンド契約は gordon-doc <command> --help で確認してください。"] }, alignLeft: true } },
      { id: "cli-install", title: { en: "Install and command shape", "zh-TW": "安裝與指令形式", ja: "インストールとコマンドの形式" }, body: { en: "The gordon-doc command is installed with the package. Run gordon-doc --help or gordon-doc <command> --help to view the option values accepted by the installed version. Commands print a concise human result by default; add --json whenever another program consumes the output.", "zh-TW": "安裝套件時會一併安裝 gordon-doc。可用 gordon-doc --help 或 gordon-doc <command> --help 檢視目前安裝版本接受的選項值。預設輸出簡潔的人類可讀結果；若由其他程式處理輸出，請加入 --json。", ja: "gordon-doc コマンドはパッケージと一緒にインストールされます。gordon-doc --help または gordon-doc <command> --help で、インストール済みバージョンが受け付けるオプション値を確認できます。既定では人間向けの簡潔な結果を表示します。出力を他のプログラムが処理する場合は --json を付けてください。" }, code: "python -m pip install gordon-doc-converter\ngordon-doc version\ngordon-doc convert --help" },
      { id: "diagnostics", title: { en: "Diagnostics and version", "zh-TW": "環境診斷與版本", ja: "診断とバージョン" }, body: { en: "Use doctor before a production run: it reports the detected platform, whether the session is interactive, and the availability of each renderer. engines lists renderer capabilities without determining overall health. version returns the installed package version. doctor exits with code 3 when no engine is available.", "zh-TW": "正式轉換前可先使用 doctor：它會回報偵測到的平台、是否為互動式工作階段，以及各 renderer 的可用性。engines 只列出 renderer 能力，不判定整體健康狀態。version 回傳已安裝套件版本。若沒有可用引擎，doctor 會以 exit code 3 結束。", ja: "本番実行の前に doctor を使ってください。検出したプラットフォーム、対話的セッションかどうか、各 renderer の利用可否を報告します。engines は renderer の機能だけを一覧し、全体の健全性は判定しません。version はインストール済みパッケージのバージョンを返します。利用可能なエンジンがない場合、doctor は exit code 3 で終了します。" }, code: "gordon-doc doctor\ngordon-doc engines --json\ngordon-doc version --json" },
      { id: "convert", title: { en: "Convert one document", "zh-TW": "轉換單一文件", ja: "単一ドキュメントの変換" }, body: { en: "convert accepts DOCX, ODT, PDF, HTML, and Markdown input. With no --to it creates PDF for DOCX, ODT, HTML, or Markdown; PDF input always requires --to. Repeat --to to request several artifacts. --output is appropriate for one single-file artifact; without it, the service derives a safe sibling output name and refuses to replace an existing file unless --overwrite is present. For DOCX-to-HTML, --engine word-com renders through Word COM on Windows; omit it or use --mode server for semantic extraction.", "zh-TW": "convert 接受 DOCX、ODT、PDF、HTML 與 Markdown 輸入。未指定 --to 時，DOCX、ODT、HTML、Markdown 會輸出 PDF；PDF 輸入則必須指定 --to。可重複使用 --to 取得多個 artifact。--output 適用於單一檔案 artifact；省略時服務會在來源旁推導安全的輸出名稱，除非提供 --overwrite，否則不會覆寫既有檔案。DOCX 轉 HTML 時，--engine word-com 在 Windows 上透過 Word COM 排版；省略或改用 --mode server 則使用語意萃取。", ja: "convert は DOCX、ODT、PDF、HTML、Markdown の入力を受け付けます。--to を指定しない場合、DOCX、ODT、HTML、Markdown は PDF を生成します。PDF 入力では常に --to が必要です。--to を繰り返すと複数の artifact を要求できます。--output は単一ファイルの artifact に適しています。省略した場合、サービスはソースと同じ場所に安全な出力名を導出し、--overwrite がない限り既存ファイルを置き換えません。DOCX から HTML では、--engine word-com が Windows 上の Word COM で組版します。省略するか --mode server を使うとセマンティック抽出になります。" }, code: "gordon-doc convert report.docx --output report.pdf\ngordon-doc convert report.docx --to markdown --to html --to yaml --to json\ngordon-doc convert report.docx --to html --engine word-com\ngordon-doc convert report.pdf --to yaml --to json\ngordon-doc convert report.odt --to docx --engine libreoffice\ngordon-doc convert report.pdf --to images --dpi 144" },
      { id: "conversion-options", title: { en: "Conversion policy and output options", "zh-TW": "轉換政策與輸出選項", ja: "変換ポリシーと出力オプション" }, body: { en: "--engine word-com, libreoffice, or gotenberg requires that exact DOCX-to-PDF engine; explicit selection never falls back. For DOCX-to-HTML, --engine word-com renders through Word COM; omit it or use --mode server for semantic extraction. --mode selects automatic policy: desktop, server, container, strict-word, or strict-libreoffice. Tracked changes use --revisions final, original, or markup; comments use --comments omit, appendix, or markup, subject to engine support. --timeout is in seconds. For HTML and Markdown, --orientation portrait or landscape chooses A4 layout. --gotenberg-url supplies the Gotenberg base URL for this invocation.", "zh-TW": "--engine word-com、libreoffice 或 gotenberg 會要求使用指定的 DOCX 轉 PDF 引擎；明確指定時絕不 fallback。DOCX 轉 HTML 時，--engine word-com 透過 Word COM 排版；省略或改用 --mode server 則使用語意萃取。--mode 選擇自動政策：desktop、server、container、strict-word 或 strict-libreoffice。修訂模式可用 --revisions final、original 或 markup；註解模式可用 --comments omit、appendix 或 markup，但仍取決於引擎支援。--timeout 單位為秒。HTML 與 Markdown 可用 --orientation portrait 或 landscape 選擇 A4 版面。--gotenberg-url 為本次呼叫提供 Gotenberg base URL。", ja: "--engine word-com、libreoffice、gotenberg は、その DOCX から PDF エンジンの使用を要求します。明示指定した場合はフォールバックしません。DOCX から HTML では、--engine word-com が Word COM で組版し、省略または --mode server ではセマンティック抽出になります。--mode は自動ポリシーを選びます：desktop、server、container、strict-word、strict-libreoffice。変更履歴は --revisions final、original、markup、コメントは --comments omit、appendix、markup で指定しますが、いずれもエンジンの対応状況に依存します。--timeout の単位は秒です。HTML と Markdown では --orientation portrait または landscape で A4 レイアウトを選べます。--gotenberg-url はこの呼び出しで使う Gotenberg の base URL を指定します。" }, code: "gordon-doc convert contract.docx --engine word-com --revisions final --comments appendix\ngordon-doc convert report.docx --to html --engine word-com\ngordon-doc convert report.html --to pdf --orientation landscape\ngordon-doc convert report.docx --mode server --gotenberg-url http://renderer:3000" },
      { id: "structured-artifacts", title: { en: "Structured YAML and JSON artifacts", "zh-TW": "結構化 YAML 與 JSON Artifact", ja: "構造化 YAML および JSON Artifact" }, body: { en: "--to yaml and --to json serialize the same versioned semantic document. Schema 1.3 keeps Markdown-like heading, paragraph, list, and table text while preserving meaningful links, images, revisions, annotations, source order, metadata, and reverse locators. Repeat --to to extract once and write both formats. --metadata accepts none, basic, or layout; optional values with no data are omitted rather than written as null. --to json writes a document artifact, while the separate --json flag writes the CLI result contract to stdout.", "zh-TW": "--to yaml 與 --to json 會序列化同一份具版本的語意文件。Schema 1.3 保留接近 Markdown 的標題、段落、清單及表格文字，同時保存有意義的連結、圖片、修訂、註解、來源順序、metadata 與反向 locator。重複使用 --to 可只擷取一次並同時寫出兩種格式。--metadata 接受 none、basic 或 layout；沒有資料的選用值會直接省略，不會輸出 null。--to json 產生文件 artifact；不同用途的 --json 則將 CLI 執行結果寫到 stdout。", ja: "--to yaml と --to json は、同じバージョン付きセマンティックドキュメントをシリアライズします。Schema 1.3 は Markdown に近い見出し、段落、リスト、表のテキストを保ちながら、意味のあるリンク、画像、変更履歴、注釈、ソース順序、metadata、逆引き locator を保持します。--to を繰り返せば、抽出は 1 回で両方の形式を書き出せます。--metadata は none、basic、layout を受け付けます。データのない任意の値は null ではなく省略されます。--to json はドキュメント artifact を書き出し、これとは別の --json フラグは CLI の結果契約を stdout に書き出します。" }, code: "gordon-doc convert report.docx --to yaml --to json --metadata basic\ngordon-doc convert report.pdf --to yaml --to json --metadata layout\ngordon-doc convert report.docx --to json --json" },
      { id: "source-anchors", title: { en: "Reverse location and source verification", "zh-TW": "反向定位與來源驗證", ja: "逆引き位置指定とソース検証" }, body: { en: "Structured artifacts identify the exact input with source.sha256 and verify each normalized block or table cell with source_anchor.content_sha256. DOCX anchors use the OOXML part and element path, with a native paragraph ID when Word supplies one; table cells extend the path with row and cell indexes. PDF anchors use the one-based physical page. PDF page coordinates are not yet available and can be added by a future layout provider. File offsets are not stable locators: DOCX recompression and PDF optimization or incremental saves change them without changing the visible content.", "zh-TW": "結構化 artifact 以 source.sha256 識別完全相同的輸入檔，並以 source_anchor.content_sha256 驗證每個正規化 block 或表格儲存格。DOCX anchor 使用 OOXML part 與 element path；Word 有提供時另含原生段落 ID，表格儲存格則在 path 加上 row/cell 索引。PDF anchor 使用從 1 起算的實體頁。PDF 頁內座標目前尚未提供，未來可由 layout provider 擴充。file offset 並非穩定 locator：DOCX 重新壓縮，以及 PDF 最佳化或增量儲存，都可能在可見內容不變時改變 offset。", ja: "構造化 artifact は source.sha256 で入力ファイルを厳密に特定し、正規化された各 block や表セルを source_anchor.content_sha256 で検証します。DOCX の anchor は OOXML の part と element path を使い、Word が提供する場合はネイティブの段落 ID も含みます。表セルでは path に行と列のインデックスが追加されます。PDF の anchor は 1 起点の物理ページを使います。PDF のページ内座標は現時点では提供されておらず、将来の layout provider で追加できます。ファイルオフセットは安定した locator ではありません。DOCX の再圧縮や PDF の最適化・増分保存は、表示される内容を変えずにオフセットを変えてしまいます。" }, table: { caption: { en: "Reverse locator fields", "zh-TW": "反向定位欄位", ja: "逆引き locator のフィールド" }, headers: { en: ["Field", "Purpose"], "zh-TW": ["欄位", "用途"], ja: ["フィールド", "用途"] }, rows: { en: [["source.sha256", "Confirm the exact source file version"], ["source_anchor.locator", "Select ooxml-element, ooxml-table-cell, or pdf-page"], ["part + element_path", "Locate a DOCX element inside word/document.xml"], ["native_id", "Use Word paraId when the source provides it"], ["page_number", "Locate a PDF block on a one-based physical page"], ["content_sha256", "Verify normalized text after locating the source"]], "zh-TW": [["source.sha256", "確認完全相同的來源檔案版本"], ["source_anchor.locator", "選擇 ooxml-element、ooxml-table-cell 或 pdf-page"], ["part + element_path", "定位 word/document.xml 內的 DOCX element"], ["native_id", "來源有提供時使用 Word paraId"], ["page_number", "以從 1 起算的實體頁定位 PDF block"], ["content_sha256", "定位來源後驗證正規化文字"]], ja: [["source.sha256", "ソースファイルのバージョンを厳密に確認する"], ["source_anchor.locator", "ooxml-element、ooxml-table-cell、pdf-page から選ぶ"], ["part + element_path", "word/document.xml 内の DOCX element を特定する"], ["native_id", "ソースが提供する場合に Word の paraId を使う"], ["page_number", "1 起点の物理ページで PDF block を特定する"], ["content_sha256", "ソース特定後に正規化テキストを検証する"]] }, legend: { en: ["Optional locator fields appear only when they apply to the source format."], "zh-TW": ["選用定位欄位只會在適用於來源格式時出現。"], ja: ["任意の locator フィールドは、ソース形式に該当する場合のみ出力されます。"] }, alignLeft: true, firstColumnWidth: "wide" } },
      { id: "progress", title: { en: "Conversion progress", "zh-TW": "轉換進度", ja: "変換の進捗表示" }, body: { en: "convert and batch show phase-based progress automatically on interactive terminals. Progress is emitted only on stderr, so redirected stdout and machine-readable results remain clean. --json disables automatic progress; use --progress to force it or --no-progress to suppress it. Batch progress reports completed files over total files rather than an invented time percentage.", "zh-TW": "convert 與 batch 在互動終端會自動顯示階段式進度。進度只寫入 stderr，因此重導向的 stdout 與機器可讀結果不會被污染。--json 會關閉自動進度；可用 --progress 強制顯示，或用 --no-progress 關閉。batch 顯示已完成檔案數／總檔案數，而非虛構的時間百分比。", ja: "convert と batch は、対話的なターミナルで自動的に段階別の進捗を表示します。進捗は stderr にのみ出力されるため、リダイレクトした stdout や機械可読な結果は汚れません。--json は自動進捗を無効にします。--progress で強制表示、--no-progress で抑制できます。バッチの進捗は、根拠のない時間の百分率ではなく、完了ファイル数と総ファイル数を報告します。" }, code: "gordon-doc convert report.docx --to yaml --progress\ngordon-doc convert report.docx --to json --no-progress\ngordon-doc batch one.docx two.docx --output-dir converted --progress" },
      { id: "images-template", title: { en: "Page images and HTML template", "zh-TW": "頁面影像與 HTML 範本", ja: "ページ画像と HTML テンプレート" }, body: { en: "Use --to images to rasterize a PDF source or the PDF produced from a DOCX source. --dpi accepts 1 through 600; --image-format is png or jpeg; --quality applies to JPEG; repeat --page with one-based page numbers to select pages; --background sets the image background colour. Image output is a directory named <stem>.pages containing numbered files. template writes an editable A4 HTML starting point and protects existing files unless --overwrite is supplied.", "zh-TW": "使用 --to images 將 PDF 來源，或由 DOCX 產生的 PDF，轉為頁面影像。--dpi 可設 1 至 600；--image-format 為 png 或 jpeg；--quality 套用於 JPEG；可重複使用 --page（從 1 起算）選擇頁面；--background 設定影像背景色。影像輸出為名為 <stem>.pages 的目錄，內含連號檔案。template 會建立可編輯的 A4 HTML 起始範本；除非提供 --overwrite，否則會保護既有檔案。", ja: "--to images は PDF ソース、または DOCX から生成した PDF をラスタライズします。--dpi は 1 から 600、--image-format は png または jpeg、--quality は JPEG に適用されます。--page を 1 起点のページ番号で繰り返すとページを選択でき、--background は画像の背景色を設定します。画像出力は <stem>.pages という名前のディレクトリで、連番のファイルを含みます。template は編集可能な A4 HTML の出発点を書き出し、--overwrite がない限り既存ファイルを保護します。" }, code: "gordon-doc convert report.pdf --to images --image-format jpeg --quality 85 --page 1 --page 3\ngordon-doc template report.html --orientation landscape" },
      { id: "compare-batch", title: { en: "Compare PDFs and convert batches", "zh-TW": "比較 PDF 與批次轉換", ja: "PDF の比較とバッチ変換" }, body: { en: "compare examines PDF structure, fonts, sizes, and rendered pixels. Set --diff-dir to save PNGs for pages that differ, and use --dpi to control comparison raster resolution. batch converts one or more DOCX files sequentially, isolating each file failure; it always targets PDF. --output-dir stores each generated PDF in the chosen directory. The batch exit code is non-zero when any item fails, while --json retains every item result for CI reporting.", "zh-TW": "compare 會檢查 PDF 結構、字型、大小與渲染後的像素。可設定 --diff-dir 儲存不同頁面的 PNG，並以 --dpi 控制比較的點陣解析度。batch 會依序轉換一或多個 DOCX，並隔離各檔案失敗；其輸出固定為 PDF。--output-dir 將每個產生的 PDF 放進指定目錄。只要任何項目失敗，batch 的 exit code 就會是非零；--json 則保留完整的逐項結果供 CI 報告使用。", ja: "compare は PDF の構造、フォント、サイズ、レンダリング後のピクセルを調べます。--diff-dir を設定すると差異のあるページを PNG で保存でき、--dpi で比較時のラスター解像度を制御します。batch は 1 つ以上の DOCX を順番に変換し、各ファイルの失敗を隔離します。出力は常に PDF です。--output-dir は生成した各 PDF を指定ディレクトリに保存します。いずれかの項目が失敗すると batch の exit code は非ゼロになり、--json は CI レポート用にすべての項目の結果を保持します。" }, code: "gordon-doc compare expected.pdf actual.pdf --diff-dir differences --json\ngordon-doc batch one.docx two.docx --output-dir converted --mode server --json" },
      { id: "automation", title: { en: "JSON results and exit codes", "zh-TW": "JSON 結果與 Exit Code", ja: "JSON 結果と Exit Code" }, body: { en: "All commands accept --json. Successful conversion payloads include the selected and attempted engines, artifact paths and metadata, duration, effective annotation modes, warnings, and fallback information. Failures include a stable error code, safe message, engine when known, and retryable flag. Exit code 0 means success; 2 means invalid input or output already exists; 3 means engine/capability unavailable; 4 means conversion failed, timed out, or produced no output; and 5 means PDF validation failed.", "zh-TW": "所有指令均接受 --json。成功轉換的 payload 包含選用與嘗試過的引擎、artifact 路徑與中繼資料、耗時、實際採用的註解模式、warning 與 fallback 資訊。失敗結果包含穩定的錯誤碼、安全訊息、可得時的引擎名稱與 retryable 旗標。exit code 0 表示成功；2 表示輸入無效或輸出已存在；3 表示引擎／能力不可用；4 表示轉換失敗、逾時或無輸出；5 表示 PDF 驗證失敗。", ja: "すべてのコマンドが --json を受け付けます。変換成功時の payload には、選択されたエンジンと試行したエンジン、artifact のパスと metadata、所要時間、実際に適用された注釈モード、warning、フォールバック情報が含まれます。失敗時には安定した error code、安全なメッセージ、判明していればエンジン名、retryable フラグが含まれます。exit code 0 は成功、2 は入力が無効または出力が既に存在、3 はエンジンや機能が利用不可、4 は変換の失敗・タイムアウト・出力なし、5 は PDF 検証の失敗を表します。" }, code: "gordon-doc convert report.docx --json\n# PowerShell: stop a script if conversion fails\ngordon-doc convert report.docx --output report.pdf\nif ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }" },
    ],
  },
  {
    id: "library",
    category: "getting-started",
    title: { en: "Python library", "zh-TW": "Python 函式庫", ja: "Python ライブラリ" },
    heading: { en: "Python document conversion library", "zh-TW": "Python 文件轉換函式庫", ja: "Python ドキュメント変換ライブラリ" },
    summary: { en: "Add typed DOCX, PDF, HTML, Markdown, YAML, JSON, and image conversion to Python applications with engine-neutral requests, results, batches, and diagnostics.", "zh-TW": "在 Python 應用程式加入具型別的 DOCX、PDF、HTML、Markdown、YAML、JSON 與圖片轉換，並使用引擎中立的請求、結果、批次及診斷。", ja: "エンジン非依存のリクエスト、結果、バッチ、診断を使って、型付きの DOCX、PDF、HTML、Markdown、YAML、JSON、画像変換を Python アプリケーションに追加します。" },
    sections: [
      { id: "library-overview", title: { en: "Library overview", "zh-TW": "函式庫總覽", ja: "ライブラリ概要" }, body: { en: "The public API uses engine-neutral typed models. Choose the smallest entry point that meets the integration need.", "zh-TW": "公開 API 使用引擎中立的具型別模型。請依整合需求選擇最精簡的入口。", ja: "公開 API はエンジン非依存の型付きモデルを使います。統合の要件を満たす最小の入口を選んでください。" }, table: { caption: { en: "Python library entry points", "zh-TW": "Python 函式庫入口", ja: "Python ライブラリの入口" }, headers: { en: ["Entry point", "Use it for"], "zh-TW": ["入口", "適用情境"], ja: ["入口", "用途"] }, rows: { en: [["ConversionRequest.from_source", "Infer and validate source format from a path"], ["convert(request)", "Run one conversion and receive ConversionResult"], ["DocumentConversionService", "Inject engines or use service methods directly"], ["convert_batch(requests)", "Run sequential, failure-isolated conversions"], ["probe_engines()", "Discover renderer availability and annotation capabilities"], ["result.to_dict()", "Produce stable JSON-compatible result data"]], "zh-TW": [["ConversionRequest.from_source", "由路徑推斷並驗證來源格式"], ["convert(request)", "執行單一轉換並取得 ConversionResult"], ["DocumentConversionService", "注入引擎，或直接使用 service 方法"], ["convert_batch(requests)", "執行依序且失敗隔離的轉換"], ["probe_engines()", "探索 renderer 可用性與註解能力"], ["result.to_dict()", "產生穩定、JSON 相容的結果資料"]], ja: [["ConversionRequest.from_source", "パスからソース形式を推定して検証する"], ["convert(request)", "1 件の変換を実行し ConversionResult を受け取る"], ["DocumentConversionService", "エンジンを注入する、または service メソッドを直接使う"], ["convert_batch(requests)", "逐次かつ失敗を隔離した変換を実行する"], ["probe_engines()", "renderer の利用可否と注釈機能を調べる"], ["result.to_dict()", "安定した JSON 互換の結果データを生成する"]] }, legend: { en: ["Use ConversionOptions to set policy and output behaviour."], "zh-TW": ["使用 ConversionOptions 設定政策與輸出行為。"], ja: ["ポリシーと出力動作の設定には ConversionOptions を使ってください。"] }, alignLeft: true, firstColumnWidth: "wide" } },
      { id: "library-single", title: { en: "Single conversion", "zh-TW": "單檔轉換", ja: "単一変換" }, body: { en: "ConversionRequest.from_source validates the allowlisted extension and infers the source format. convert returns a ConversionResult rather than raising for ordinary conversion failures, so inspect success and error before reading artifacts. ConversionError is reserved for invalid requests and related contract errors.", "zh-TW": "ConversionRequest.from_source 會驗證允許的副檔名並推斷來源格式。convert 對一般轉換失敗會回傳 ConversionResult，而非直接拋出例外，因此讀取 artifacts 前請先檢查 success 與 error。ConversionError 用於無效請求及相關契約錯誤。", ja: "ConversionRequest.from_source は許可リストの拡張子を検証し、ソース形式を推定します。convert は通常の変換失敗では例外を送出せず ConversionResult を返すため、artifacts を読む前に success と error を確認してください。ConversionError は無効なリクエストと関連する契約エラーのために予約されています。" }, code: "from pathlib import Path\nfrom gordon_doc_converter import ConversionRequest, convert\n\nresult = convert(ConversionRequest.from_source(Path('report.docx')))\nif not result.success:\n    raise RuntimeError(result.error.message if result.error else 'conversion failed')\nprint(result.artifacts[0].path)" },
      { id: "library-options", title: { en: "Options and strict policy", "zh-TW": "選項與嚴格政策", ja: "オプションと strict ポリシー" }, body: { en: "Use ConversionOptions to choose output paths, overwrite behaviour, timeout, deployment mode, an explicit engine, annotation handling, metadata detail, and image settings. EngineName is strict: an unavailable explicitly chosen engine produces a diagnosable failure rather than a silent alternative. ArtifactType can request PDF, DOCX, ODT, HTML, Markdown, YAML, JSON, or page images where the route supports it.", "zh-TW": "使用 ConversionOptions 設定輸出路徑、覆寫行為、逾時、部署模式、明確引擎、註解處理、metadata detail 與影像設定。EngineName 是嚴格選擇：指定的引擎不可用時，會得到可診斷的失敗，而不是靜默改用其他引擎。若轉換路徑支援，ArtifactType 可要求 PDF、DOCX、ODT、HTML、Markdown、YAML、JSON 或頁面影像。", ja: "ConversionOptions では、出力パス、上書き動作、タイムアウト、配備モード、明示的なエンジン、注釈の扱い、metadata detail、画像設定を指定できます。EngineName は厳密です。明示指定したエンジンが利用できない場合、暗黙に別のエンジンへ切り替えるのではなく、診断可能な失敗になります。ArtifactType は、変換経路が対応していれば PDF、DOCX、ODT、HTML、Markdown、YAML、JSON、ページ画像を要求できます。" }, code: "from pathlib import Path\nfrom gordon_doc_converter import (\n    ArtifactType, ConversionOptions, ConversionRequest, convert,\n)\n\nrequest = ConversionRequest.from_source(\n    Path('report.docx'),\n    artifacts=(ArtifactType.YAML, ArtifactType.JSON),\n    options=ConversionOptions(output_path=Path('report')),\n)\nresult = convert(request)" },
      { id: "library-service", title: { en: "Batches, probes, and result handling", "zh-TW": "批次、探測與結果處理", ja: "バッチ、プローブ、結果の扱い" }, body: { en: "DocumentConversionService supports dependency injection for engines and environment-aware orchestration. convert_batch processes requests sequentially and keeps failures isolated. probe_engines returns EngineProbeResult entries with availability, version, supported revision modes, and comment modes. Results serialize through to_dict() to stable JSON-compatible primitives for logs or APIs; do not log document contents or sensitive paths.", "zh-TW": "DocumentConversionService 支援引擎的 dependency injection 與依環境執行的 orchestration。convert_batch 會依序處理請求並隔離失敗。probe_engines 回傳 EngineProbeResult，包含可用性、版本、支援的修訂模式與註解模式。結果可透過 to_dict() 序列化為穩定、JSON 相容的基本型別，適合日誌或 API；請勿記錄文件內容或敏感路徑。", ja: "DocumentConversionService はエンジンの dependency injection と、環境に応じた orchestration に対応します。convert_batch はリクエストを順番に処理し、失敗を隔離します。probe_engines は、利用可否、バージョン、対応する変更履歴モード、コメントモードを含む EngineProbeResult を返します。結果は to_dict() でログや API 向けの安定した JSON 互換のプリミティブにシリアライズできます。ドキュメントの内容や機微なパスは記録しないでください。" }, code: "from gordon_doc_converter import DocumentConversionService\n\nservice = DocumentConversionService()\nfor probe in service.probe_engines():\n    print(probe.engine, probe.available, probe.version)\n\nresults = service.convert_batch(requests)\npayload = [result.to_dict() for result in results]" },
    ],
  },
  {
    id: "api",
    category: "getting-started",
    title: { en: "HTTP API", "zh-TW": "HTTP API", ja: "HTTP API" },
    heading: { en: "DOCX to PDF HTTP API", "zh-TW": "DOCX 轉 PDF HTTP API", ja: "DOCX から PDF への HTTP API" },
    summary: { en: "Deploy an authenticated FastAPI service for private DOCX-to-PDF conversion with LibreOffice or Gotenberg, health endpoints, limits, and an OpenAPI 3.1 contract.", "zh-TW": "部署具認證的 FastAPI 私有 DOCX 轉 PDF 服務，搭配 LibreOffice 或 Gotenberg、健康檢查、流量限制與 OpenAPI 3.1 契約。", ja: "LibreOffice または Gotenberg、ヘルスエンドポイント、各種制限、OpenAPI 3.1 契約を備えた認証付き FastAPI サービスを、プライベートな DOCX から PDF への変換のために配備します。" },
    sections: [
      { id: "api-overview", title: { en: "API overview", "zh-TW": "API 總覽", ja: "API 概要" }, body: { en: "The private HTTP adapter exposes a deliberately small DOCX-to-PDF surface. Use the endpoints below for conversion, diagnostics, and deployment health checks.", "zh-TW": "私有 HTTP adapter 刻意提供精簡的 DOCX 轉 PDF 介面。請使用下表端點執行轉換、診斷與部署健康檢查。", ja: "プライベート HTTP adapter は、意図的に小さい DOCX から PDF へのインターフェースだけを公開します。変換、診断、配備のヘルスチェックには次のエンドポイントを使ってください。" }, table: { caption: { en: "HTTP API endpoints", "zh-TW": "HTTP API 端點", ja: "HTTP API エンドポイント" }, headers: { en: ["Endpoint", "Authentication", "Purpose"], "zh-TW": ["端點", "認證", "用途"], ja: ["エンドポイント", "認証", "用途"] }, rows: { en: [["POST /conversions", "Bearer token", "Convert uploaded DOCX bytes to a PDF"], ["GET /engines", "Bearer token", "List configured renderer capabilities"], ["GET /live", "None", "Confirm the process is alive"], ["GET /ready", "None", "Check that the default renderer is ready"], ["GET /version", "None", "Return the package version"]], "zh-TW": [["POST /conversions", "Bearer token", "將上傳的 DOCX 位元組轉換為 PDF"], ["GET /engines", "Bearer token", "列出已設定 renderer 的能力"], ["GET /live", "無", "確認程序仍在運行"], ["GET /ready", "無", "確認預設 renderer 是否就緒"], ["GET /version", "無", "回傳套件版本"]], ja: [["POST /conversions", "Bearer token", "アップロードされた DOCX を PDF に変換する"], ["GET /engines", "Bearer token", "設定済み renderer の機能を一覧する"], ["GET /live", "なし", "プロセスが稼働していることを確認する"], ["GET /ready", "なし", "既定の renderer が準備できているか確認する"], ["GET /version", "なし", "パッケージのバージョンを返す"]] }, legend: { en: ["Protected endpoints require Authorization: Bearer <api-key> when an API key is configured."], "zh-TW": ["設定 API key 時，受保護端點必須提供 Authorization: Bearer <api-key>。"], ja: ["API key を設定している場合、保護されたエンドポイントには Authorization: Bearer <api-key> が必要です。"] }, alignLeft: true, firstColumnWidth: "w48", secondColumnWidth: "w40" } },
      {
        id: "start-api",
        title: { en: "Start the API", "zh-TW": "啟動 API", ja: "API の起動" },
        body: {
          en: "Install the optional API dependencies, set a strong API key, and run the application factory on port 8000.",
          "zh-TW": "安裝選用的 API 相依套件、設定高強度 API key，並在 8000 port 啟動 application factory。",
          ja: "任意の API 依存パッケージをインストールし、強度の高い API key を設定して、ポート 8000 で application factory を起動します。",
        },
        code: "uv sync --extra api\n$env:GORDON_DOC_API_KEY = \"replace-me\"\nuv run uvicorn gordon_doc_converter.api.app:create_app --factory --host 127.0.0.1 --port 8000",
        note: {
          en: "The environment-variable example uses PowerShell. Keep this API private and do not commit API keys.",
          "zh-TW": "環境變數範例使用 PowerShell。此 API 應維持私有部署，且請勿提交 API key。",
          ja: "環境変数の例は PowerShell です。この API はプライベートな配備に保ち、API key はコミットしないでください。",
        },
      },
      {
        id: "api-convert",
        title: { en: "Convert a document", "zh-TW": "轉換文件", ja: "ドキュメントの変換" },
        body: {
          en: "POST /conversions accepts only a DOCX request body and returns application/pdf. Send the original basename in X-Filename, the DOCX OOXML MIME type in Content-Type, and a Bearer token when an API key is configured. The optional engine query parameter accepts libreoffice or gotenberg; Word COM is deliberately unavailable through the API. The server stages the upload in a temporary directory, validates the OOXML package and limits, calls the configured malware-scan hook, and deletes temporary files before the response returns.",
          "zh-TW": "POST /conversions 只接受 DOCX request body，並回傳 application/pdf。請在 X-Filename 傳送原始檔名、在 Content-Type 傳送 DOCX 的 OOXML MIME type；設定 API key 時另須 Bearer token。選用的 engine query parameter 接受 libreoffice 或 gotenberg；API 刻意不提供 Word COM。伺服器會將上傳暫存於臨時目錄、驗證 OOXML package 與限制、呼叫設定的惡意程式掃描 hook，並在回應前刪除暫存檔。",
          ja: "POST /conversions は DOCX の request body のみを受け付け、application/pdf を返します。X-Filename に元のファイル名、Content-Type に DOCX の OOXML MIME type を指定し、API key を設定している場合は Bearer token も送ってください。任意の engine query parameter は libreoffice または gotenberg を受け付けます。Word COM は API では意図的に提供されません。サーバーはアップロードを一時ディレクトリに置き、OOXML package と各種制限を検証し、設定されたマルウェアスキャン hook を呼び出し、応答を返す前に一時ファイルを削除します。",
        },
        code: "curl --fail-with-body \\\n  -H \"Authorization: Bearer replace-me\" \\\n  -H \"Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\" \\\n  -H \"X-Filename: report.docx\" \\\n  --data-binary @report.docx \\\n  \"http://127.0.0.1:8000/conversions?engine=libreoffice\" \\\n  --output report.pdf",
        note: {
          en: "The HTTP adapter is intentionally narrower than the library and CLI: it exposes authenticated DOCX-to-PDF conversion only. Keep it behind private network controls and TLS in production.",
          "zh-TW": "HTTP adapter 刻意比函式庫與 CLI 窄：只提供經認證的 DOCX 轉 PDF。正式環境請將它放在私有網路控制與 TLS 後方。",
          ja: "HTTP adapter はライブラリや CLI より意図的に狭く、認証付きの DOCX から PDF への変換のみを公開します。本番ではプライベートネットワークの制御と TLS の内側に置いてください。",
        },
      },
      {
        id: "api-documentation",
        title: { en: "Interactive API documentation", "zh-TW": "互動式 API 文件", ja: "インタラクティブな API ドキュメント" },
        body: {
          en: "The documentation site publishes the generated OpenAPI 3.1 contract and a bundled, read-only Swagger UI. You can inspect the JSON in your browser or download it for code generation and validation tools.",
          "zh-TW": "文件站會發布產生的 OpenAPI 3.1 契約與內建的唯讀 Swagger UI。你可以在瀏覽器檢視 JSON，或下載後交由程式碼產生與驗證工具使用。",
          ja: "ドキュメントサイトは、生成された OpenAPI 3.1 契約と、同梱の読み取り専用 Swagger UI を公開しています。ブラウザーで JSON を確認したり、コード生成や検証ツール用にダウンロードしたりできます。",
        },
        links: [
          {
            label: { en: "View OpenAPI JSON", "zh-TW": "檢視 OpenAPI JSON", ja: "OpenAPI JSON を表示" },
            href: "/openapi.json",
          },
          {
            label: { en: "Download OpenAPI JSON", "zh-TW": "下載 OpenAPI JSON", ja: "OpenAPI JSON をダウンロード" },
            href: "/openapi.json",
            download: true,
          },
          {
            label: { en: "Open Swagger UI", "zh-TW": "開啟 Swagger UI", ja: "Swagger UI を開く" },
            href: "/swagger/",
          },
        ],
        note: {
          en: "The hosted Swagger UI is read-only. Use the API server's /docs page when you need Try it out against a configured private deployment.",
          "zh-TW": "託管的 Swagger UI 採唯讀模式。如需對已設定的私有部署使用 Try it out，請開啟 API server 本身的 /docs。",
          ja: "ホストされた Swagger UI は読み取り専用です。設定済みのプライベート配備に対して Try it out を使う場合は、API サーバー自身の /docs を開いてください。",
        },
      },
      {
        id: "api-endpoints",
        title: { en: "Available endpoints", "zh-TW": "可用端點", ja: "利用可能なエンドポイント" },
        body: {
          en: "The specification describes document conversion, engine discovery, health, readiness, and version endpoints. Protected requests use a Bearer token.",
          "zh-TW": "規格包含文件轉換、引擎探索、存活檢查、就緒檢查與版本端點。受保護的 request 使用 Bearer token。",
          ja: "仕様にはドキュメント変換、エンジン探索、liveness、readiness、バージョンのエンドポイントが含まれます。保護されたリクエストは Bearer token を使います。",
        },
        code: "# Protected: requires Authorization: Bearer <api-key>\nPOST /conversions?engine=libreoffice|gotenberg\nGET  /engines\n\n# Unprotected operational metadata\nGET  /live     # {\"status\": \"ok\"}\nGET  /ready    # 200 ready, 503 not-ready\nGET  /version  # {\"version\": \"0.6.0\"}",
      },
      {
        id: "api-status-errors",
        title: { en: "Status codes and operational limits", "zh-TW": "狀態碼與作業限制", ja: "ステータスコードと運用上の制限" },
        body: {
          en: "A successful conversion returns 200 with a PDF attachment. Invalid engine choices or input return 400; missing or invalid credentials return 401; an oversized source returns 413; renderer failures return 422; exhausted rate or concurrency capacity returns 429; internal staging or service faults return 500; and unavailable authentication or malware scanning returns 503. /ready checks the configured default engine rather than merely reporting that the process is alive. The built-in fixed-window rate limit and concurrency limit are process-local, so production deployments with multiple replicas must enforce distributed limits at the ingress or gateway too.",
          "zh-TW": "成功轉換會以 200 回傳 PDF attachment。無效引擎或輸入回傳 400；缺少或無效憑證回傳 401；來源超過大小限制回傳 413；renderer 失敗回傳 422；速率或並行容量耗盡回傳 429；內部暫存或服務錯誤回傳 500；認證或惡意程式掃描服務不可用回傳 503。/ready 會檢查設定的預設引擎，而非只確認程序仍存活。內建的固定視窗速率限制與並行限制只在單一 process 內有效，因此多副本的正式部署還須在 ingress 或 gateway 提供分散式限制。",
          ja: "変換に成功すると 200 と PDF の attachment を返します。無効なエンジン指定や入力は 400、認証情報の欠落や不正は 401、サイズ超過のソースは 413、renderer の失敗は 422、レートや並行数の上限到達は 429、内部の一時保存やサービス障害は 500、認証やマルウェアスキャンの利用不可は 503 を返します。/ready はプロセスが稼働していることを確認するだけでなく、設定された既定エンジンを検査します。組み込みの固定ウィンドウ方式のレート制限と並行数制限はプロセス単位でのみ有効なため、複数レプリカの本番配備では ingress や gateway でも分散型の制限を適用する必要があります。",
        },
      },
      {
        id: "api-configuration", title: { en: "Configuration and integration hooks", "zh-TW": "設定與整合 Hooks", ja: "設定と統合 Hooks" }, body: { en: "create_app accepts ApiSettings or environment defaults. GORDON_DOC_API_KEY enables the default constant-time Bearer-token comparison. GORDON_DOC_GOTENBERG_URL configures a Gotenberg adapter and makes Gotenberg the default engine; otherwise LibreOffice is used. ApiSettings also controls conversion timeout, maximum concurrent conversions, fixed-window request rate, and input limits. Supply auth_hook, malware_scan_hook, and telemetry_hook when integrating private identity, scanning, or observability systems. Telemetry receives content-free fields only; never emit document contents, credentials, or customer paths.", "zh-TW": "create_app 可接受 ApiSettings 或使用環境預設值。GORDON_DOC_API_KEY 會啟用預設的常數時間 Bearer-token 比對。GORDON_DOC_GOTENBERG_URL 會設定 Gotenberg adapter，並令其成為預設引擎；否則使用 LibreOffice。ApiSettings 也控制轉換逾時、最大並行轉換數、固定視窗請求速率與輸入限制。整合私有身分、掃描或可觀測性系統時，請提供 auth_hook、malware_scan_hook 與 telemetry_hook。Telemetry 僅接收不含內容的欄位；切勿輸出文件內容、憑證或客戶路徑。", ja: "create_app は ApiSettings または環境変数の既定値を受け付けます。GORDON_DOC_API_KEY は既定の定数時間 Bearer token 比較を有効にします。GORDON_DOC_GOTENBERG_URL は Gotenberg adapter を設定し、Gotenberg を既定エンジンにします。設定しない場合は LibreOffice を使います。ApiSettings は変換のタイムアウト、最大同時変換数、固定ウィンドウのリクエストレート、入力の制限も制御します。プライベートな認証、スキャン、可観測性システムと統合する場合は、auth_hook、malware_scan_hook、telemetry_hook を指定してください。Telemetry には内容を含まないフィールドのみが渡されます。ドキュメントの内容、認証情報、顧客のパスは決して出力しないでください。" }, code: "from gordon_doc_converter.api.app import ApiSettings, create_app\n\napp = create_app(settings=ApiSettings(\n    api_key='read-from-a-secret-store',\n    timeout_seconds=120,\n    max_concurrent_conversions=2,\n    rate_limit_requests=30,\n    rate_limit_window_seconds=60,\n))" },
    ],
  },
  {
    id: "architecture",
    category: "development",
    title: { en: "Architecture", "zh-TW": "系統架構", ja: "アーキテクチャ" },
    heading: { en: "Document converter architecture", "zh-TW": "文件轉換器系統架構", ja: "ドキュメントコンバーターのアーキテクチャ" },
    summary: { en: "Understand GordonKit's portable document conversion architecture, including the application service, engine protocol, policy orchestration, adapters, and PDF validation.", "zh-TW": "了解 GordonKit 可攜式文件轉換架構，包括 application service、引擎協定、政策協調、adapter 與 PDF 驗證。", ja: "application service、engine protocol、ポリシーの orchestration、adapter、PDF 検証を含む、GordonKit の可搬なドキュメント変換アーキテクチャを理解します。" },
    sections: [
      { id: "dependency-flow", title: { en: "Dependency flow", "zh-TW": "相依流向", ja: "依存の流れ" }, body: { en: "Library and CLI callers enter through the application service. The orchestrator applies policy before invoking a shared engine protocol and validating the resulting PDF.", "zh-TW": "函式庫與 CLI 呼叫皆進入 application service，由 orchestrator 套用政策後，再呼叫共用 engine protocol 並驗證產出的 PDF。", ja: "ライブラリと CLI の呼び出しはどちらも application service から入ります。orchestrator がポリシーを適用してから共有の engine protocol を呼び出し、生成された PDF を検証します。" }, code: "Library / CLI\n  -> Application service\n  -> Orchestrator and policy\n  -> Engine protocol\n  -> PDF validation" },
      { id: "adapter-rules", title: { en: "Adapter rules", "zh-TW": "Adapter 規則", ja: "Adapter のルール" }, body: { en: "Platform APIs and subprocesses stay inside engine adapters. Windows-only dependencies are imported lazily so the core package remains portable.", "zh-TW": "平台 API 與 subprocess 限制在引擎 adapter 內。Windows 專用相依套件採延遲匯入，確保核心套件維持跨平台。", ja: "プラットフォーム API と subprocess はエンジン adapter の内側に留めます。Windows 専用の依存パッケージは遅延インポートされるため、コアパッケージは可搬性を保ちます。" } },
    ],
  },
  {
    id: "contributing",
    category: "development",
    title: { en: "Contributing", "zh-TW": "參與開發", ja: "コントリビュート" },
    heading: { en: "Contribute to GordonKit", "zh-TW": "參與 GordonKit 開發", ja: "GordonKit へのコントリビュート" },
    summary: { en: "Set up the GordonKit Document Converter development environment with uv, then format, lint, type-check, and test Python contributions before opening a pull request.", "zh-TW": "使用 uv 設定 GordonKit 文件轉換器開發環境，並在提出 Pull Request 前完成 Python 格式化、lint、型別檢查與測試。", ja: "uv で GordonKit ドキュメントコンバーターの開発環境を構築し、Pull Request を出す前に Python の書式整形、lint、型チェック、テストを実行します。" },
    sections: [
      { id: "setup", title: { en: "Local setup", "zh-TW": "本機設定", ja: "ローカル環境の構築" }, body: { en: "The project uses uv for reproducible Python dependency management.", "zh-TW": "專案使用 uv 管理可重現的 Python 相依套件。", ja: "本プロジェクトは再現性のある Python 依存管理のために uv を使います。" }, code: "uv sync --dev --all-extras" },
      { id: "quality", title: { en: "Quality checks", "zh-TW": "品質檢查", ja: "品質チェック" }, body: { en: "Format, lint, type-check, and test before opening a pull request.", "zh-TW": "提出 Pull Request 前，請完成格式化、lint、型別檢查與測試。", ja: "Pull Request を出す前に、書式整形、lint、型チェック、テストを実行してください。" }, code: "uv run ruff format --check .\nuv run ruff check .\nuv run mypy src\nuv run pytest" },
    ],
  },
  {
    id: "deployment",
    category: "operations",
    title: { en: "Deployment modes", "zh-TW": "部署模式", ja: "配備モード" },
    heading: { en: "Document conversion deployment modes", "zh-TW": "文件轉換部署模式", ja: "ドキュメント変換の配備モード" },
    summary: { en: "Choose Word COM, LibreOffice, or Gotenberg conversion policies for interactive Windows desktops, servers, and containers without silent engine fallback.", "zh-TW": "為互動式 Windows 桌面、伺服器與容器選擇 Word COM、LibreOffice 或 Gotenberg 文件轉換政策，且不會靜默切換引擎。", ja: "対話的な Windows デスクトップ、サーバー、コンテナー向けに、Word COM、LibreOffice、Gotenberg の変換ポリシーを選択します。暗黙のエンジンフォールバックは行いません。" },
    sections: [
      { id: "desktop", title: { en: "Desktop", "zh-TW": "桌面模式", ja: "デスクトップ" }, body: { en: "Interactive Windows desktops may automatically select Word COM when licensed Word is available. This applies to both DOCX-to-PDF and DOCX-to-HTML conversion; HTML output through Word COM produces higher visual fidelity than semantic extraction.", "zh-TW": "互動式 Windows 桌面在具備合法授權 Word 時，可自動選用 Word COM。此規則同時適用於 DOCX 轉 PDF 與 DOCX 轉 HTML；透過 Word COM 輸出的 HTML 比語意萃取具有更高的視覺忠實度。", ja: "対話的な Windows デスクトップでは、正規ライセンスの Word が利用できる場合に Word COM を自動選択することがあります。これは DOCX から PDF と DOCX から HTML の両方に適用され、Word COM 経由の HTML 出力はセマンティック抽出より視覚的な忠実度が高くなります。" } },
      { id: "server-container", title: { en: "Server and container", "zh-TW": "伺服器與容器", ja: "サーバーとコンテナー" }, body: { en: "Server mode prefers Gotenberg then LibreOffice. The container includes LibreOffice and can use an external Gotenberg service; it never auto-selects Word COM.", "zh-TW": "伺服器模式依序偏好 Gotenberg、LibreOffice。容器內含 LibreOffice，也可使用外部 Gotenberg service，且絕不自動選用 Word COM。", ja: "サーバーモードは Gotenberg、次に LibreOffice を優先します。コンテナーは LibreOffice を同梱し、外部の Gotenberg service も利用できますが、Word COM を自動選択することはありません。" }, note: { en: "Rendering may differ between Word and LibreOffice. Test representative documents before rollout.", "zh-TW": "Word 與 LibreOffice 的排版可能不同，正式上線前應以代表性文件測試。", ja: "Word と LibreOffice では組版結果が異なる場合があります。展開前に代表的なドキュメントでテストしてください。" } },
    ],
  },
  {
    id: "containers",
    category: "operations",
    title: { en: "Containers", "zh-TW": "容器化", ja: "コンテナー" },
    heading: { en: "Docker document conversion", "zh-TW": "Docker 文件轉換", ja: "Docker でのドキュメント変換" },
    summary: { en: "Run document conversion in Docker Compose with a hardened GordonKit image, bundled LibreOffice, an authenticated API, or an isolated Gotenberg renderer.", "zh-TW": "透過 Docker Compose 與強化的 GordonKit 映像執行文件轉換，可使用內建 LibreOffice、具認證 API 或隔離的 Gotenberg renderer。", ja: "強化された GordonKit イメージ、同梱の LibreOffice、認証付き API、分離した Gotenberg renderer を使って、Docker Compose でドキュメント変換を実行します。" },
    sections: [
      { id: "profiles", title: { en: "Choose a profile", "zh-TW": "選擇 Profile", ja: "Profile の選択" }, body: { en: "Every Compose service is opt-in and uses the same GordonKit image. Use cli for local commands, standalone-lo for the API with included LibreOffice, or gateway-gotenberg for the API backed by a separate renderer.", "zh-TW": "所有 Compose service 都必須明確選用，且共用同一個 GordonKit 映像。cli 適合本機命令；standalone-lo 使用內建 LibreOffice；gateway-gotenberg 則讓 API 搭配獨立排版服務。", ja: "すべての Compose service は明示的な選択制で、同じ GordonKit イメージを使います。ローカルのコマンドには cli、同梱 LibreOffice を使う API には standalone-lo、別の renderer を後段に置く API には gateway-gotenberg を使ってください。" }, note: { en: "Always pass --profile. Running compose up without a profile starts no services.", "zh-TW": "務必傳入 --profile；未指定 profile 時，compose up 不會啟動任何服務。", ja: "必ず --profile を指定してください。profile を指定せずに compose up を実行しても、サービスは起動しません。" } },
      { id: "cli-profile", title: { en: "CLI profile", "zh-TW": "CLI Profile", ja: "CLI Profile" }, body: { en: "CLI mode uses included LibreOffice, mounts the current directory at /work, and does not require an API key. The same one-line command works in Bash and PowerShell.", "zh-TW": "CLI 模式使用內建 LibreOffice、將目前目錄掛載至 /work，且不需要 API 金鑰；相同的單行指令可用於 Bash 與 PowerShell。", ja: "CLI モードは同梱の LibreOffice を使い、カレントディレクトリを /work にマウントします。API key は不要です。同じ 1 行のコマンドが Bash でも PowerShell でも動作します。" }, code: "docker compose -f docker/compose.yaml --profile cli run --rm --build cli convert /work/report.docx --output /work/report.pdf --engine libreoffice --overwrite" },
      { id: "standalone-profile", title: { en: "Standalone LibreOffice API", "zh-TW": "單體 LibreOffice API", ja: "単体構成の LibreOffice API" }, body: { en: "Run the authenticated API and LibreOffice in one container when simple deployment and local rendering matter more than independent renderer scaling.", "zh-TW": "需要簡單部署與本機排版，且不需獨立擴展 renderer 時，可在同一容器執行具認證的 API 與 LibreOffice。", ja: "renderer を個別にスケールさせることよりも、シンプルな配備とローカル組版を重視する場合は、認証付き API と LibreOffice を 1 つのコンテナーで実行します。" }, code: "# .env\nGORDON_DOC_API_KEY=replace-me\n\ndocker compose -f docker/compose.yaml --env-file .env --profile standalone-lo up --build" },
      { id: "gateway-profile", title: { en: "Gotenberg gateway", "zh-TW": "Gotenberg Gateway", ja: "Gotenberg Gateway" }, body: { en: "Run the API with a separate Gotenberg service when renderer isolation and independent service health are preferred. Compose connects both services to the gordon-doc network and waits for Gotenberg to become healthy. Configuring the Gotenberg URL explicitly selects that engine; failures do not silently fall back to LibreOffice.", "zh-TW": "偏好 renderer 隔離與獨立服務健康狀態時，可讓 API 搭配個別 Gotenberg service；Compose 會將兩者連至 gordon-doc network，並等待 Gotenberg 健康後再啟動 API。設定 Gotenberg URL 代表明確選用該引擎；失敗時不會靜默改用 LibreOffice。", ja: "renderer の分離と独立したサービス健全性を重視する場合は、API を別の Gotenberg service と組み合わせて実行します。Compose は両サービスを gordon-doc network に接続し、Gotenberg が healthy になるまで待機します。Gotenberg URL を設定することはそのエンジンの明示選択を意味し、失敗しても暗黙に LibreOffice へフォールバックすることはありません。" }, code: "docker compose -f docker/compose.yaml --env-file .env --profile gateway-gotenberg up --build" },
      { id: "container-bash", title: { en: "Bash API request", "zh-TW": "Bash API 請求", ja: "Bash からの API リクエスト" }, body: { en: "Load the deployer-managed key from .env, then select the engine explicitly and save the PDF response.", "zh-TW": "從 .env 載入部署者管理的金鑰，明確指定引擎並儲存 PDF 回應。", ja: ".env から配備者が管理する key を読み込み、エンジンを明示的に指定して PDF の応答を保存します。" }, code: "set -a; . ./.env; set +a\ncurl --fail-with-body -H \"Authorization: Bearer $GORDON_DOC_API_KEY\" -H \"Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\" -H \"X-Filename: report.docx\" --data-binary @report.docx \"http://127.0.0.1:8000/conversions?engine=gotenberg\" --output report-gb.pdf" },
      { id: "container-powershell", title: { en: "PowerShell API request", "zh-TW": "PowerShell API 請求", ja: "PowerShell からの API リクエスト" }, body: { en: "PowerShell can read the same .env file and save the binary response with Invoke-WebRequest. Use engine=libreoffice with the standalone profile.", "zh-TW": "PowerShell 可讀取相同的 .env，並以 Invoke-WebRequest 儲存二進位回應；使用 standalone profile 時請改為 engine=libreoffice。", ja: "PowerShell でも同じ .env を読み込み、Invoke-WebRequest でバイナリ応答を保存できます。standalone profile では engine=libreoffice を使ってください。" }, code: "$env:GORDON_DOC_API_KEY = ((Get-Content .env | Where-Object { $_ -match '^GORDON_DOC_API_KEY=' }) -replace '^GORDON_DOC_API_KEY=', '')\n$headers = @{ Authorization = \"Bearer $env:GORDON_DOC_API_KEY\"; 'X-Filename' = 'report.docx' }\nInvoke-WebRequest -Uri 'http://127.0.0.1:8000/conversions?engine=gotenberg' -Method Post -Headers $headers -ContentType 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' -InFile .\\report.docx -OutFile .\\report-gb.pdf" },
      { id: "container-stop", title: { en: "Stop the services", "zh-TW": "停止服務", ja: "サービスの停止" }, body: { en: "Stop the profile after local testing. The generated PDF remains on the host.", "zh-TW": "本機測試後停止對應 profile；已產生的 PDF 會保留在主機。", ja: "ローカルでの確認後は profile を停止します。生成された PDF はホストに残ります。" }, code: "docker compose -f docker/compose.yaml --profile standalone-lo down\ndocker compose -f docker/compose.yaml --profile gateway-gotenberg down" },
      { id: "published-image", title: { en: "Published image", "zh-TW": "正式發布映像", ja: "公開イメージ" }, body: { en: "Tagged releases publish one linux/amd64 image at gordonkit/gordon-doc-converter. The default entrypoint runs the CLI; pass api to start the HTTP service. Prefer an explicit version tag for reproducible deployments.", "zh-TW": "正式版本會發布單一 linux/amd64 映像至 gordonkit/gordon-doc-converter。預設 entrypoint 執行 CLI；傳入 api 則啟動 HTTP service。需要可重現部署時，請使用明確版本 tag。", ja: "タグ付きリリースでは、gordonkit/gordon-doc-converter に linux/amd64 のイメージを 1 つ公開します。既定の entrypoint は CLI を実行し、api を渡すと HTTP service が起動します。再現性のある配備には明示的なバージョンタグを使ってください。" }, code: "docker run --rm gordonkit/gordon-doc-converter:0.6.0 version\ndocker run --rm -p 8000:8000 -e GORDON_DOC_API_KEY=replace-me gordonkit/gordon-doc-converter:0.6.0 api" },
      { id: "health", title: { en: "Operations and security", "zh-TW": "維運與安全", ja: "運用とセキュリティ" }, body: { en: "All profiles run as a non-root user with a read-only root filesystem, a bounded temporary filesystem, and no-new-privileges. API profiles require a strong key; production ingress must also enforce request-size and distributed rate limits.", "zh-TW": "所有 profile 都以非 root 使用者、唯讀 root filesystem、有限 tmpfs 與 no-new-privileges 執行。API profile 必須使用高強度 key；正式環境 ingress 也應限制 request 大小並提供分散式 rate limit。", ja: "すべての profile は非 root ユーザー、読み取り専用の root filesystem、上限付きの一時ファイルシステム、no-new-privileges で実行されます。API profile には強度の高い key が必要で、本番の ingress ではリクエストサイズ制限と分散型のレート制限も適用してください。" }, code: "python docker/smoke.py --token replace-me --docx sample.docx", note: { en: "Do not commit the .env file or customer documents. The smoke client checks liveness, authenticated engine discovery, and optionally an end-to-end PDF conversion.", "zh-TW": "請勿提交 .env 或客戶文件。Smoke client 會檢查存活狀態、經認證的引擎探索，以及選用的端到端 PDF 轉換。", ja: ".env や顧客のドキュメントはコミットしないでください。Smoke client は liveness、認証付きのエンジン探索、および任意でエンドツーエンドの PDF 変換を確認します。" } },
    ],
  },
  {
    id: "roadmap",
    category: "project",
    title: { en: "Roadmap", "zh-TW": "產品藍圖", ja: "ロードマップ" },
    heading: { en: "GordonKit project roadmap", "zh-TW": "GordonKit 專案藍圖", ja: "GordonKit プロジェクトのロードマップ" },
    summary: { en: "Review the GordonKit Document Converter roadmap, current Python library, CLI, API, container, semantic artifact, and document comparison capabilities.", "zh-TW": "查看 GordonKit 文件轉換器藍圖，以及目前 Python 函式庫、CLI、API、容器、語意 artifact 與文件比較能力。", ja: "GordonKit ドキュメントコンバーターのロードマップと、現在の Python ライブラリ、CLI、API、コンテナー、セマンティック artifact、ドキュメント比較の機能を確認します。" },
    sections: [
      { id: "current", title: { en: "Current scope", "zh-TW": "目前範圍", ja: "現在の範囲" }, body: { en: "The core library, CLI, conversion adapters, semantic artifacts, comparison tools, authenticated API adapter, and container profiles are available.", "zh-TW": "目前已提供核心函式庫、CLI、轉換 adapters、語意 artifacts、比較工具、具認證的 API adapter 與容器 profiles。", ja: "コアライブラリ、CLI、変換 adapter、セマンティック artifact、比較ツール、認証付き API adapter、コンテナー profile を提供しています。" } },
      { id: "principles", title: { en: "Project principles", "zh-TW": "專案原則", ja: "プロジェクトの原則" }, body: { en: "GordonKit favors explicit policy, portable contracts, isolated external processes, and diagnostic results over hidden convenience.", "zh-TW": "GordonKit 重視明確政策、可攜契約、隔離外部程序與可診斷結果，不以隱藏行為換取表面便利。", ja: "GordonKit は、見えない便利さよりも、明示的なポリシー、可搬な契約、外部プロセスの分離、診断可能な結果を重視します。" } },
    ],
  },
  {
    id: "security",
    category: "project",
    title: { en: "Security", "zh-TW": "安全性", ja: "セキュリティ" },
    heading: { en: "Secure document conversion", "zh-TW": "安全文件轉換", ja: "安全なドキュメント変換" },
    summary: { en: "Secure untrusted document conversion with extension, MIME, OOXML, file-size, and decompression validation, isolated execution, and private vulnerability reporting.", "zh-TW": "透過副檔名、MIME、OOXML、檔案大小與解壓縮驗證、隔離執行及私密漏洞回報，安全處理不受信任的文件轉換。", ja: "拡張子、MIME、OOXML、ファイルサイズ、解凍の検証、分離した実行、非公開の脆弱性報告により、信頼できないドキュメントの変換を安全に行います。" },
    sections: [
      { id: "input", title: { en: "Input handling", "zh-TW": "輸入處理", ja: "入力の扱い" }, body: { en: "Validate extensions, MIME types, and OOXML structure. Apply size and decompression limits before processing untrusted documents.", "zh-TW": "驗證副檔名、MIME type 與 OOXML 結構；處理不受信任文件前套用大小與解壓縮限制。", ja: "拡張子、MIME type、OOXML 構造を検証します。信頼できないドキュメントを処理する前に、サイズと解凍の制限を適用してください。" } },
      { id: "reporting", title: { en: "Report a vulnerability", "zh-TW": "回報漏洞", ja: "脆弱性の報告" }, body: { en: "Use the private reporting process described in SECURITY.md. Do not disclose sensitive document samples in public issues.", "zh-TW": "請依 SECURITY.md 的私密流程回報，勿在公開 issue 揭露敏感文件樣本。", ja: "SECURITY.md に記載された非公開の報告手順に従ってください。公開 issue に機微なドキュメントのサンプルを載せないでください。" } },
    ],
  },
];
