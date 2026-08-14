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
            en: ["Input", "DOCX", "PDF", "HTML", "Markdown", "ODT", "Images"],
            "zh-TW": ["輸入", "DOCX", "PDF", "HTML", "Markdown", "ODT", "頁圖"],
          },
          rows: {
            en: [
              ["DOCX", "", "Auto", "✓", "✓", "LO", "PDF"],
              ["PDF", "—", "", "✓", "✓", "—", "✓"],
              ["HTML", "P", "P+", "", "—", "—", "—"],
              ["Markdown", "P", "P+", "—", "", "—", "—"],
              ["ODT", "LO", "LO", "—", "—", "", "—"],
            ],
            "zh-TW": [
              ["DOCX", "", "Auto", "✓", "✓", "LO", "PDF"],
              ["PDF", "—", "", "✓", "✓", "—", "✓"],
              ["HTML", "P", "P+", "", "—", "—", "—"],
              ["Markdown", "P", "P+", "—", "", "—", "—"],
              ["ODT", "LO", "LO", "—", "—", "", "—"],
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
    title: { en: "CLI quickstart", "zh-TW": "CLI 快速上手" },
    summary: { en: "Convert, inspect, compare, and automate from the terminal.", "zh-TW": "從終端機執行轉換、檢查、比較與自動化。" },
    sections: [
      { id: "diagnostics", title: { en: "Diagnostics", "zh-TW": "環境診斷" }, body: { en: "Inspect available engines before a production run.", "zh-TW": "正式轉換前先檢查可用引擎。" }, code: "gordon-doc doctor\ngordon-doc engines --json" },
      { id: "convert", title: { en: "Convert files", "zh-TW": "轉換檔案" }, body: { en: "Choose output formats and operational policy from one command.", "zh-TW": "透過單一指令選擇輸出格式與執行政策。" }, code: "gordon-doc convert report.docx --output report.pdf\ngordon-doc convert report.pdf --to images --dpi 144" },
    ],
  },
  {
    id: "api",
    category: "getting-started",
    title: { en: "HTTP API", "zh-TW": "HTTP API" },
    summary: { en: "Run the private FastAPI adapter and explore its OpenAPI contract.", "zh-TW": "啟動私有 FastAPI adapter，並瀏覽其 OpenAPI 契約。" },
    sections: [
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
        code: "POST /conversions\nGET  /engines\nGET  /live\nGET  /ready\nGET  /version\n\nAuthorization: Bearer <api-key>",
      },
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
      { id: "server-container", title: { en: "Server and container", "zh-TW": "伺服器與容器" }, body: { en: "Server mode prefers Gotenberg then LibreOffice. Containers use the engine included by their image profile and never auto-select Word COM.", "zh-TW": "伺服器模式依序偏好 Gotenberg、LibreOffice。容器依 image profile 使用內建引擎，且絕不自動選用 Word COM。" }, note: { en: "Rendering may differ between Word and LibreOffice. Test representative documents before rollout.", "zh-TW": "Word 與 LibreOffice 的排版可能不同，正式上線前應以代表性文件測試。" } },
    ],
  },
  {
    id: "containers",
    category: "operations",
    title: { en: "Containers", "zh-TW": "容器化" },
    summary: { en: "Choose a hardened container profile for one-off CLI work, a self-contained API, or remote Gotenberg rendering.", "zh-TW": "依單次 CLI 作業、完整單體 API 或遠端 Gotenberg 排版需求，選擇強化的容器 profile。" },
    sections: [
      { id: "profiles", title: { en: "Choose a profile", "zh-TW": "選擇 Profile" }, body: { en: "Every Compose service is opt-in. Use cli for local commands, standalone-lo for an API with LibreOffice in one image, or gateway-gotenberg for a smaller API image backed by a separate renderer.", "zh-TW": "所有 Compose service 都必須明確選用。cli 適合本機命令；standalone-lo 將 API 與 LibreOffice 包在同一映像；gateway-gotenberg 則使用較小的 API 映像搭配獨立排版服務。" }, note: { en: "Always pass --profile. Running compose up without a profile starts no services.", "zh-TW": "務必傳入 --profile；未指定 profile 時，compose up 不會啟動任何服務。" } },
      { id: "cli-profile", title: { en: "CLI profile", "zh-TW": "CLI Profile" }, body: { en: "The CLI image includes LibreOffice and mounts the current directory at /work. It is suited to local, one-off conversions without running an HTTP service.", "zh-TW": "CLI 映像內含 LibreOffice，並將目前目錄掛載至 /work，適合不啟動 HTTP service 的本機單次轉換。" }, code: "docker compose -f docker/compose.yaml --profile cli run --rm cli convert /work/report.docx --output /work/report.pdf" },
      { id: "standalone-profile", title: { en: "Standalone LibreOffice API", "zh-TW": "單體 LibreOffice API" }, body: { en: "Run the private API and LibreOffice in one container when simple deployment and local rendering matter more than independent renderer scaling.", "zh-TW": "需要簡單部署與本機排版，且不需獨立擴展 renderer 時，可在同一容器執行私有 API 與 LibreOffice。" }, code: "# .env\nGORDON_DOC_API_KEY=replace-me\n\ndocker compose -f docker/compose.yaml --env-file .env --profile standalone-lo up --build" },
      { id: "gateway-profile", title: { en: "Gotenberg gateway", "zh-TW": "Gotenberg Gateway" }, body: { en: "Run the API gateway with a separate Gotenberg service when renderer isolation and independent service health are preferred. Compose waits for Gotenberg to become healthy before the gateway starts.", "zh-TW": "偏好 renderer 隔離與獨立服務健康狀態時，可讓 API gateway 搭配個別 Gotenberg service；Compose 會等待 Gotenberg 健康後再啟動 gateway。" }, code: "docker compose -f docker/compose.yaml --env-file .env --profile gateway-gotenberg up --build" },
      { id: "health", title: { en: "Operations and security", "zh-TW": "維運與安全" }, body: { en: "All profiles run as a non-root user with a read-only root filesystem, a bounded temporary filesystem, and no-new-privileges. API profiles require a strong key; production ingress must also enforce request-size and distributed rate limits.", "zh-TW": "所有 profile 都以非 root 使用者、唯讀 root filesystem、有限 tmpfs 與 no-new-privileges 執行。API profile 必須使用高強度 key；正式環境 ingress 也應限制 request 大小並提供分散式 rate limit。" }, code: "python docker/smoke.py --token replace-me --docx sample.docx", note: { en: "Do not commit the .env file or customer documents. The smoke client checks liveness, authenticated engine discovery, and optionally an end-to-end PDF conversion.", "zh-TW": "請勿提交 .env 或客戶文件。Smoke client 會檢查存活狀態、經認證的引擎探索，以及選用的端到端 PDF 轉換。" } },
    ],
  },
  {
    id: "roadmap",
    category: "project",
    title: { en: "Roadmap", "zh-TW": "產品藍圖" },
    summary: { en: "Track the stable core and intentionally staged delivery areas.", "zh-TW": "掌握穩定核心與分階段交付範圍。" },
    sections: [
      { id: "current", title: { en: "Current scope", "zh-TW": "目前範圍" }, body: { en: "The core library, CLI, conversion adapters, semantic artifacts, comparison tools, private API adapter, and container profiles are available.", "zh-TW": "目前已提供核心函式庫、CLI、轉換 adapters、語意 artifacts、比較工具、私有 API adapter 與容器 profiles。" } },
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