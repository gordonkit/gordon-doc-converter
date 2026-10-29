# 兼容性政策

[English](COMPATIBILITY.md) · [繁體中文](COMPATIBILITY.zh-TW.md) · [日本語](COMPATIBILITY.ja.md)

> **草稿。** 本政策自 `1.0.0` 起生效。在此之前，依 Semantic Versioning 的规定，任何 `0.x`
> minor 版本仍可能变动下列接口，每项变动都会记录在 `CHANGELOG.md`。本文为英文版
> `COMPATIBILITY.md` 的翻译，两者有出入时以英文版为准。

GordonKit Document Converter 遵循 [Semantic Versioning](https://semver.org/)。自 `1.0.0`
起，破坏下列公开契约的版本会提升 major 版本号。Minor 版本只新增行为而不破坏兼容性；
patch 版本修复错误与安全问题。

## 公开契约

### Python 库

公开的 Python API 恰好是 `gordon_doc_converter.__all__` 导出的名称，以及其文档记载的参数、
字段、方法与返回类型：

- 转换入口：`convert`、`convert_batch`、`probe_engines` 与 `DocumentConversionService`；
- 请求与结果模型：`ConversionRequest`、`ConversionOptions`、`ConversionResult`、
  `ArtifactResult`、`ArtifactItem`、`EngineProbeResult`、`PdfValidationResult`、
  `NormalizedAnnotation`、`AnnotationAnchor` 与 `PageImageArtifact`；
- 枚举：`SourceFormat`、`ArtifactType`、`ArtifactStatus`、`EngineName`、`DeploymentMode`、
  `RevisionMode`、`CommentMode`、`AnnotationKind`、`PageImageFormat` 与 `ErrorCode`；
- 错误：`ConversionError`；
- 逐页图片与比较：`PdfRasterizer`、`PdfiumPageRenderer`、`RasterOptions`、
  `PdfComparisonService`、`PdfComparisonReport` 与 `PillowImageDiffer`。

其他所有模块，包括 `gordon_doc_converter.engines`、`content`、`process`、`api` 与 `cli`，
以及任何以下划线开头的名称，都属于内部实现，任何版本都可能变动。

兼容的变动包括：在 `__all__` 新增名称、新增带默认值的 keyword 参数、在模型新增可选字段，
以及在枚举新增成员。匹配枚举值的调用方应能处理未知的成员。

### 命令行接口

- `doctor`、`engines`、`template`、`convert`、`compare`、`batch` 与 `version` 命令，以及其
  文档记载的选项与参数。
- Exit code：`0` 成功；`2` 输入无效或输出已存在；`3` 引擎或能力不可用；`4` 转换失败、
  超时或未产生输出；`5` PDF 验证失败。新的失败类别会获得新的 code，既有 code 的含义永不改变。
- `--json` 输出的文档。可新增字段；既有字段不会被移除、改名或变更类型。

供人阅读的文本输出、stderr 上的进度输出与帮助文本不属于契约。

### 错误与警告代码

- `ErrorCode` 的值是稳定的。Minor 版本可能新增代码。
- 警告的 `code` 值（例如 `ENGINE_FALLBACK` 与 `LAYOUT_NOT_PRESERVED`）一经发布即为稳定。
  Minor 版本可能新增警告，因此调用方应忽略无法识别的代码。
- 错误与警告的 `message` 文本是供人阅读的，任何版本都可能变动。

### 结构化 YAML、JSON 与 JSON Lines Artifact

结构化 schema 带有自己的 `schema_version`，与包版本无关。

- Schema 的 minor 版本（例如 `1.5` 到 `1.6`）只会新增可选字段、区块种类、locator 种类或
  record 类型。未使用这些新项目的文档，序列化结果与先前完全相同。
- 移除、改名、变更字段类型或字段含义，必须提升 schema 的 major 版本（`1.x` 到 `2.0`），
  而且只会在包的 major 版本中发布。
- 可选字段会直接省略，而不是序列化为 `null`。读取方应忽略未知的字段与区块种类。
- 字节偏移不属于 locator 契约，原因请见 README。

### 排版输出

PDF、DOCX、ODT、HTML、Markdown 与逐页图片输出不保证逐字节相同。引擎版本、字体与 writer
的修复都会改变其确切字节与版式。这些输出的文件名与目录结构（`<stem>.pages/0001.png`、
`<stem>.assets/` 与注释 sidecar）属于契约。

### HTTP API

带版本前缀的路由为 `POST /v1/conversions`、`GET /v1/engines` 与 `GET /v1/version`。
探测端点 `GET /live` 与 `GET /ready` 不加版本前缀，因此容器的健康检查永远不需要更改。

- 导出的 OpenAPI 契约（`docs/openapi.json`）所记载的路径、请求头、query 参数、状态码
  与错误内容都受本政策保障。
- 破坏性变更会在新的前缀（例如 `/v2/`）下发布，并与 `/v1/` 并存至少一个 minor 版本，
  之后才会在 major 版本中移除 `/v1/`。
- `GORDON_DOC_API_KEY` 与 `GORDON_DOC_GOTENBERG_URL` 是稳定的配置名称。
- 没有前缀的 `/conversions`、`/engines` 与 `/version` 是为 `0.12.0` 之前的客户端保留的
  已弃用别名。它们在 OpenAPI 契约中标记为 `deprecated`，并会在 `1.0.0` 移除。

### 容器镜像

- 镜像名称、tag 规则（`X.Y.Z`、`X.Y`、`latest`）、发布平台（`linux/amd64` 与
  `linux/arm64`）、默认的 CLI entrypoint、`api` 参数与 Compose profile 名称都属于契约。
- Minor 版本可能增加镜像内的引擎。移除引擎或镜像提供的转换路径属于破坏性变更。
- 基础镜像，以及 LibreOffice 与其他系统包的版本，不属于契约。

## 支持平台

`.github/workflows/ci.yml` 中的 `quality` job 会在下列每种组合上运行完整的单元测试，本清单
必须与其保持一致。

- Python：3.12、3.13 与 3.14。对某个 Python 版本的支持只会在 minor 版本中停止，而且必须在
  该版本终止维护之后。
- 操作系统：Linux、Windows 与 macOS。Microsoft Word COM 只能在 Windows 上使用；实际引擎的
  集成测试在 Linux（LibreOffice）与受控的 Windows 主机（Word）上运行。
- 引擎：对各引擎版本的支持为尽力而为。本项目绝不保证 Microsoft Word 与 LibreOffice 的
  排版结果相同。

## 弃用流程

1. 公开契约在 minor 版本中标记为弃用，并在 `CHANGELOG.md` 加入 `Deprecated` 记录；Python
   API 另会发出指出替代方案的 `DeprecationWarning`。
2. 已弃用的契约至少会在下一个 minor 版本中继续运作，并且只会在下一个 major 版本中移除。
3. 安全修复是唯一的例外。若保留某项契约会让用户暴露于风险，该契约可能在 minor 或 patch
   版本中变更，并在 `Security` 段落中特别说明。
