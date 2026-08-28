# GordonKit 文档转换器

[![CI](https://github.com/gordonkit/gordon-doc-converter/actions/workflows/ci.yml/badge.svg)](https://github.com/gordonkit/gordon-doc-converter/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![授权：Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![开发状态：Pre-Alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](https://pypi.org/classifiers/)

[English](https://github.com/gordonkit/gordon-doc-converter/blob/main/README.md) ·
[繁體中文](https://github.com/gordonkit/gordon-doc-converter/blob/main/README.zh-TW.md) ·
[日本語](https://github.com/gordonkit/gordon-doc-converter/blob/main/README.ja.md)

[线上文档](https://docs.gordonkit.com/)

GordonKit Document Converter 可将 DOCX 与其他文档格式转换为 PDF、HTML、Markdown、
图片等格式。它提供 Python 库、命令行接口与 HTTP API，并使用 Microsoft Word、
LibreOffice、Pandoc 或 Gotenberg 进行排版转换。

## 支持的格式转换

| 输入格式 | DOCX | PDF | ODT | HTML | Markdown | YAML | JSON | 图片 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DOCX | × | Auto | LO | ✓ | ✓ | ✓ | ✓ | PDF |
| PDF | — | × | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| ODT | LO | LO | × | — | — | — | — | — |
| HTML | P | P+ | — | × | ✓ | ✓ | ✓ | — |
| Markdown | P | P+ | — | — | × | — | — | — |

`Auto` 依策略自动选择引擎 · `✓` 内置支持 · `LO` LibreOffice · `P` Pandoc ·
`P+` Pandoc 搭配 PDF 后端 · `PDF` 先转为 PDF · `—` 不支持 ·
`×` 相同格式，不执行转换

逐页图片可输出为 PNG 或 JPEG。DOCX 与 PDF 可产生 Markdown、HTML、YAML、JSON
及图片；Markdown 与 HTML 也可转换为 PDF 或 DOCX。HTML 另可通过与 DOCX、PDF 相同的
语义提取转换为 Markdown、YAML 与 JSON，且不需要外部引擎。Markdown 仍仅能转换为
PDF 与 DOCX。

DOCX 转 ODT、ODT 转 DOCX，以及 ODT 转 PDF 均使用 LibreOffice。DOCX 转换采用以下
引擎策略：

- 交互式 Windows 的 DOCX 转 PDF：自动模式优先使用 Word COM。
- 服务器的 DOCX 转 PDF：自动模式依序优先使用 Gotenberg、LibreOffice。
- 其他主机的 DOCX 转 PDF：自动模式优先使用 LibreOffice。
- DOCX 转 HTML：默认使用语义提取。在 Windows 桌面环境且 Word COM 可用时，通过 Word
    排版可获得更高的视觉忠实度。
- 使用 `--engine word-com` 可强制使用 Word COM 输出 HTML，使用 `--mode server` 则可强制
    使用语义提取。
- 明确指定引擎与 strict 模式绝不 fallback。
- 不同引擎的排版结果可能有差异。

ODT 支持以 ODF-CNS 15251／ISO/IEC 26300 Writer 文档为目标，会验证封装结构与内容是否
可读，但不保证来回转换后版式完全相同。

HTML／Markdown 转换为 PDF 与 DOCX 需要 Pandoc；输出 PDF 时还需要 `wkhtmltopdf` 等
Pandoc PDF 后端。可先执行 `gordon-doc template 报告.html` 创建可编辑、适合打印的 A4
模板，再执行 `gordon-doc convert 报告.html --to pdf` 或 `--to docx`。若要使用 A4 横式
版式，请加上 `--orientation landscape`。

HTML 转 Markdown／YAML／JSON 会直接解析文档，不需要任何引擎：

```console
gordon-doc convert 报告.html --to markdown --to yaml --to json
```

标题、段落、列表、表格、链接、`<ins>`／`<del>` 修订，以及 `<title>`／`<meta>` metadata
会规范化为与 DOCX、PDF 相同的 schema。内嵌的 `data:` 图片会写入 `<stem>.assets`
目录；以 URL 引用的图片则保持链接。script、style 与内嵌对象元素会被省略，所有省略
与失真的映射都会报告为机器可读的警告。

## 使用接口

| 接口 | 适用场景 |
| --- | --- |
| Python 库 | 在 Python 应用程序中使用具类型的转换、批量处理与引擎诊断功能 |
| `gordon-doc` 命令行工具 | 从终端、脚本或 CI 工作执行本地转换 |
| HTTP API | 将需验证身份的转换要求传送至内部服务 |
| 容器执行模式 | 在隔离镜像中执行命令行工具或 HTTP API 及其排版引擎依赖包 |

各种转换接口皆使用相同的应用服务，并保留结构化结果、引擎策略与诊断信息。

## 安装

| 接口 | 安装方式 |
| --- | --- |
| Python 库 | `python -m pip install gordon-doc-converter` |
| `gordon-doc` 命令行工具 | 随 `gordon-doc-converter` 安装；可执行 `gordon-doc version` 确认 |
| HTTP API | `python -m pip install "gordon-doc-converter[api]"` |
| 容器执行模式 | 安装 Docker Engine 或 Docker Desktop 与 Compose v2；不需安装本地 Python 包 |

部分排版与输出功能需要安装 `gordon-doc-converter[images]`、
`gordon-doc-converter[gotenberg]` 或 `gordon-doc-converter[word]`。各引擎与平台需求请参阅
[线上文档](https://docs.gordonkit.com/)。

## 快速开始

### Python 库

在 Python 应用程序中执行转换：

```python
from pathlib import Path

from gordon_doc_converter import ConversionRequest, convert

request = ConversionRequest.from_source(Path("示例.docx"))
result = convert(request)
if not result.success:
    raise RuntimeError(result.error.message if result.error else "conversion failed")
print(result.artifacts[0].path)
```

`convert()` 会依部署策略选择引擎、验证暂存输出，并只在验证成功后发布 PDF。
需要注入引擎时使用 `DocumentConversionService`；依序执行且各项失败互不影响的批量转换
使用 `convert_batch()`；能力诊断则使用 `probe_engines()`。

### 命令行工具

```console
gordon-doc convert 示例.docx --output 示例.pdf
```

### 容器

若不想在主机安装 Python 或 LibreOffice，可使用单一容器镜像。`cli` 执行模式会将当前
目录挂载至 `/work`，且不需要 API 密钥。以下单行命令可同时用于 Bash 与 PowerShell：

```console
docker compose -f docker/compose.yaml --profile cli run --rm cli convert /work/示例.docx --output /work/示例.pdf
```

若要启动内含 LibreOffice 的内部 HTTP 服务，请设置 API 密钥并启动 `standalone-lo`：

```dotenv
GORDON_DOC_API_KEY=replace-with-a-strong-random-value
```

```console
docker compose -f docker/compose.yaml --env-file .env --profile standalone-lo up --build
```

若要使用独立的 Gotenberg 排版服务，请改用 `gateway-gotenberg`；相同的 API 镜像会通过
共用 Docker network 连接 Gotenberg。设置 `GORDON_DOC_GOTENBERG_URL` 后，API 会明确以
Gotenberg 为默认引擎；Gotenberg 请求失败时不会静默改用 LibreOffice。容器执行模式、
安全性说明与基本检查请参阅[简中容器文档](docker/README.zh-CN.md)。正式版本 tag 会将
`gordonkit/gordon-doc-converter` 单一镜像发布至 Docker Hub；所需 repository 变量、
secrets 与发行步骤也记录于该文档。

### HTTP API

API 启动后，请传送 DOCX 内容、原始文件名与 Bearer Token：

```sh
curl --fail -H "Authorization: Bearer replace-me" \
    -H "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document" \
    -H "X-Filename: 示例.docx" --data-binary @示例.docx \
    http://localhost:8000/conversions --output 示例.pdf
```

PowerShell 请使用 `Invoke-WebRequest -InFile ... -OutFile ...`。LibreOffice 与 Gotenberg
profiles 的 Bash、PowerShell 完整启动、转换及停止服务示例，请参阅
[简中容器文档](docker/README.zh-CN.md)。

PDFium／Pillow 位图化功能使用 `.[images]`；远程适配器使用 `.[gotenberg]`；FastAPI
使用 `.[api]`；Windows COM 使用 `.[word]`。

## 命令行接口

```console
gordon-doc doctor
gordon-doc engines --json
gordon-doc template 报告.html --orientation portrait
gordon-doc convert 示例.docx --output 示例.pdf
gordon-doc convert 报告.odt --to docx
gordon-doc convert 示例.docx --to odt --engine libreoffice
gordon-doc convert 报告.html --to pdf --orientation landscape
gordon-doc convert 报告.html --to docx
gordon-doc convert 示例.pdf --to images --dpi 144
gordon-doc convert 示例.docx --to markdown --to html --to yaml --to json
gordon-doc convert 示例.docx --to html --engine word-com
gordon-doc convert 示例.docx --to yaml --metadata layout --progress
gordon-doc convert 示例.docx --to json --json-lines
gordon-doc compare 预期.pdf 实际.pdf --diff-dir 差异 --json
gordon-doc batch 文档一.docx 文档二.docx --output-dir 已转换 --json
gordon-doc version
```

使用 `--engine word-com`、`--engine libreoffice` 或已设置的 `--engine gotenberg` 可严格
指定引擎。DOCX 转 HTML 时，`--engine word-com` 会通过 Word COM 排版；省略或改用
`--mode server` 则使用语义提取。转换选项也包含 `--mode`、`--revisions`、`--comments`、
`--metadata`、`--timeout`、`--overwrite`、图片格式／质量／页码，以及可选的
`--gotenberg-url`。
逐页图片使用 `<stem>.pages/0001.png`；语义产出文件使用 `.md`、`.html`、`.yaml`、
`.json`、共用 `.assets/`，有注释时另建附属文件。YAML 与 JSON 共用具版本的章节、
段落、列表及表格结构，可供后续索引使用。`--to json` 产生文档内容；不同用途的
`--json` 则输出命令行执行结果，便于自动化集成。

加上 `--json-lines` 可将 JSON 产出写成以换行分隔的 JSON，文件名为 `<stem>.jsonl` 而非
`<stem>.json`。内容与嵌套文档相同，但每行是一条可独立解析的记录：先是一条 `document`
记录，接着依来源顺序输出每个区块，最后是 `asset`、`annotation` 与 `warning` 记录。每条
区块记录保留嵌套版本的所有字段，并额外加上 `section_path`（所属章节的标识符），因此仍可
从逐行数据还原章节层级。此选项适用于 DOCX、PDF 与 HTML 来源，且只影响 JSON 产出；
Markdown、HTML 与 YAML 产出不受影响。

PDF 没有语义标记，因此区块由版式推论而来。转换器会依字形坐标重建文本行、移除
重复的页首页尾，并综合 PDF outline、相对字级、粗体、留白与编号判定标题。编号以
数字系统、样式及章节词解析，涵盖阿拉伯数字、罗马数字、拉丁字母、圈号与中文数字，
因此标题层级依文档自身的编号体系而定，而非仅依字级。此推论为启发式，阅读顺序
仍标示为推定。

元数据等级可选 `none`、`basic`（默认允许列表中的文档属性）或 `layout`。PDF 实体
页码从 1 起算，提供者为 `pypdf`。DOCX 在尚未设置版式信息提供者时，会省略物理页码
与文档显示页码，并明确标示为无法获取，不会将推定页码当成精确数据。

结构化产出文件支持跨格式反向定位。`source.sha256` 用来确认完全相同的来源文件；
每个 `source_anchor` 另有规范化内容的 SHA-256，可供定位后验证。DOCX 区块可定位至
`word/document.xml` 元素，表格单元格再以列与单元格定位；PDF 区块则定位至从 1 起算的
物理页。当前 PDF 锚点定位到页面而非页内坐标；未来可由版式信息提供者加入坐标，且不会
破坏 DOCX 定位契约。没有值的可选定位字段不会输出为 null。

```yaml
schema_version: "1.3"
source: {format: "pdf", sha256: "<来源文件-sha256>"}
root_blocks: [{
    id: "block-000001",
    source_order: 0,
    kind: "paragraph",
    physical_page_number: 1,
    text: "页面文本",
    source_anchor: {
        locator: "pdf-page",
        page_number: 1,
        content_sha256: "<规范化内容-sha256>"
    }
}]
```

字节位移刻意不纳入稳定的定位契约。DOCX 位移指向 ZIP 内的压缩数据，Office 重新存储
或调整压缩方式后就会改变；PDF 位移指向序列化对象或数据流，经过优化、线性化或增量
存储后也会改变。请使用来源指纹搭配 OOXML 元素路径或 PDF 页面锚点。未来若加入字节
位移，也只会作为非权威的诊断提示。

`convert` 与 `batch` 在交互终端会自动显示转换阶段。进度只写入 stderr，使用 `--json`
或重定向时会自动关闭；可用 `--progress` 或 `--no-progress` 覆写自动判断。

固定结束代码为：`0` 成功；`2` 输入无效或输出已存在；`3` 引擎或能力不可用；`4` 转换
失败、超时或未产生输出；`5` PDF 验证失败。

Microsoft Word 与 LibreOffice 对同一文档可能产生不同版式。本项目会披露实际引擎及
备援原因；明确指定引擎时，不会在未告知的情况下切换引擎。

## 开发环境

```console
uv sync --dev
uv sync --dev --all-extras
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
uv build
```

系统找不到 `soffice` 时，LibreOffice 集成测试会跳过。已安装 LibreOffice 的环境可执行
`uv run pytest -m integration tests/integration/libreoffice`。

Microsoft Word 集成测试需要 Windows、合法授权的 Microsoft Word 及 `word` 选用依赖
包。请只在受控的交互式环境中执行：先执行 `uv sync --dev --extra word --locked`，
再执行 `uv run pytest -m integration tests/integration/word_com`。

静态文档网站使用 React、Vite、Tailwind CSS、随附的 Heroicons 与 Swagger UI 构建。
重新构建 `docs/` 前，请先安装 API 与前端依赖包；构建时会自动将当前的 FastAPI 契约
导出至 `openapi.json`：

```console
uv sync --dev --extra api --locked
npm ci
npm run build
```

产生的网站位于 `docs/`，并发布于 [docs.gordonkit.com](https://docs.gordonkit.com/)。构建会在
`/en/<topic>/`、`/zh-TW/<topic>/`、`/zh-CN/<topic>/` 与 `/ja/<topic>/` 产生可索引页面，包含本地化 metadata、
canonical、语言 alternate、结构化数据、sitemap 与 robots 指示。网站也提供英文、繁体中文、简体中文与
日文的语言下拉菜单，并支持搜索、响应式版式及亮色／暗色主题。API 契约位于
`docs/openapi.json`，只读 Swagger UI 位于 `docs/swagger/index.html`。可执行
`npm run openapi:check` 检查导出内容是否已过期。

请从[英文文档](https://docs.gordonkit.com/en/overview/)、
[繁体中文文档](https://docs.gordonkit.com/zh-TW/overview/)、
[简体中文文档](https://docs.gordonkit.com/zh-CN/overview/)或
[日文文档](https://docs.gordonkit.com/ja/overview/)浏览技术参考、使用指南、兼容性说明与开发规范。

## 授权

采用 Apache License 2.0，详见 [LICENSE](LICENSE)、[NOTICE](NOTICE) 与
[THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt)。
