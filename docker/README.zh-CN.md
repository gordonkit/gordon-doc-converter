# 容器镜像与 Profiles

[English](README.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md)

单一 `gordonkit/gordon-doc-converter` 镜像同时提供 CLI 与 HTTP API。Compose 文件提供三个
必须明确选用的 profile：

- `standalone-lo`：HTTP API 使用镜像内置的 LibreOffice。
- `gateway-gotenberg`：相同的 HTTP API 镜像搭配独立 Gotenberg renderer。
- `cli`：命令行模式使用内置 LibreOffice，并以 `/work` 作为文档 volume。

正式版本会发布至单一 Docker Hub repository：

- `<namespace>/gordon-doc-converter`

例如 `v0.6.0` 会发布 `0.6.0`、`0.6` 与 `latest` 三个 image tag。当前镜像目标平台为
`linux/amd64`。

镜像 entrypoint 默认执行 CLI；第一个参数传入 `api` 则会启动 HTTP API：

```console
docker run --rm gordonkit/gordon-doc-converter:latest version
docker run --rm --publish 8000:8000 \
  --env GORDON_DOC_API_KEY=replace-me \
  gordonkit/gordon-doc-converter:latest api
```

Compose 文件会从当前 source tree 构建 `gordonkit/gordon-doc-converter:local`，适合开发与
验证。需要可重现部署时，请使用 Docker Hub 的明确版本 tag。

## CLI Profile

CLI profile 不需要 API 密钥。请在 repository 根目录通过 Bash 或 PowerShell 执行；当前
目录会挂载至 `/work`：

```console
docker compose -f docker/compose.yaml --profile cli run --rm --build cli convert /work/report.docx --output /work/report.pdf --engine libreoffice --overwrite
```

## API Profiles

启动 API profile 前，请设置高强度 `GORDON_DOC_API_KEY`。在 repository 根目录创建不纳入
版本控制的 `.env`，即可让 Bash 与 PowerShell 使用相同的 Compose 命令：

```dotenv
GORDON_DOC_API_KEY=replace-with-a-strong-random-value
```

此密钥由部署者自行产生及管理，并非由外部服务核发；请勿提交 `.env`。转换 request body
为 DOCX bytes，
`Content-Type` 使用 OOXML MIME type，并通过 `X-Filename` 传入原始 basename。API 会执行有
资源限制的 OOXML 验证，并提供可注入的认证、malware scanning 与不含文档内容的 telemetry
hooks。多 replica 生产环境仍须由 ingress 限制 request body 并提供分布式 rate limiting。

### 单体 LibreOffice API

```console
docker compose -f docker/compose.yaml --env-file .env --profile standalone-lo up --detach --build
```

Bash：

```bash
set -a; . ./.env; set +a
curl --fail http://127.0.0.1:8000/live
curl --fail-with-body -H "Authorization: Bearer $GORDON_DOC_API_KEY" -H "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document" -H "X-Filename: report.docx" --data-binary @report.docx "http://127.0.0.1:8000/conversions?engine=libreoffice" --output report-api.pdf
```

PowerShell：

```powershell
$env:GORDON_DOC_API_KEY = ((Get-Content .env | Where-Object { $_ -match '^GORDON_DOC_API_KEY=' }) -replace '^GORDON_DOC_API_KEY=', '')
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/live'
$headers = @{ Authorization = "Bearer $env:GORDON_DOC_API_KEY"; 'X-Filename' = 'report.docx' }
Invoke-WebRequest -Uri 'http://127.0.0.1:8000/conversions?engine=libreoffice' -Method Post -Headers $headers -ContentType 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' -InFile .\report.docx -OutFile .\report-api.pdf
```

### Gotenberg Gateway API

Compose 会将 API 与 Gotenberg service 加入同一个 `gordon-doc` network，等待 Gotenberg
健康后再启动 API，并将 API 设为调用 `http://gotenberg:3000`：

```console
docker compose -f docker/compose.yaml --env-file .env --profile gateway-gotenberg up --detach --build
```

Bash：

```bash
set -a; . ./.env; set +a
curl --fail-with-body -H "Authorization: Bearer $GORDON_DOC_API_KEY" -H "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document" -H "X-Filename: report.docx" --data-binary @report.docx "http://127.0.0.1:8000/conversions?engine=gotenberg" --output report-gb.pdf
```

PowerShell：

```powershell
$env:GORDON_DOC_API_KEY = ((Get-Content .env | Where-Object { $_ -match '^GORDON_DOC_API_KEY=' }) -replace '^GORDON_DOC_API_KEY=', '')
$headers = @{ Authorization = "Bearer $env:GORDON_DOC_API_KEY"; 'X-Filename' = 'report.docx' }
Invoke-WebRequest -Uri 'http://127.0.0.1:8000/conversions?engine=gotenberg' -Method Post -Headers $headers -ContentType 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' -InFile .\report.docx -OutFile .\report-gb.pdf
```

设置 `GORDON_DOC_GOTENBERG_URL` 后，API 会明确以 Gotenberg 为默认引擎。连接或转换失败
会返回给调用端，不会静默改用镜像内置的 LibreOffice。若策略要求本地排版，请使用
`standalone-lo` profile。

测试后可停止对应的 API profile：

```console
docker compose -f docker/compose.yaml --profile standalone-lo down
docker compose -f docker/compose.yaml --profile gateway-gotenberg down
```

镜像以非 root 用户、只读 root filesystem 与有限 `/tmp` tmpfs 执行。每个 request 返回前
都会删除上传与产出文档。镜像不含 Microsoft Office 组件或 Microsoft 字体；CJK 支持使用
Noto CJK 字体。Project license 与第三方声明安装于
`/usr/share/licenses/gordon-doc-converter/`，container CI 也会产生 CycloneDX SBOM。

启动后可使用下列 smoke client 检查 health、经认证的 engine inventory，以及可选的端到端
转换：

```console
python docker/smoke.py --token replace-me --docx sample.docx
```

## Docker Hub 发布设置

先在预定的 Docker Hub user 或 organization 创建 `<namespace>/gordon-doc-converter`，再创建
具备 read/write 权限的 Docker Hub access token。到 GitHub repository 的
**Settings > Secrets and variables > Actions** 设置：

| 类型 | 名称 | 值 |
| --- | --- | --- |
| Variable | `DOCKERHUB_NAMESPACE` | 拥有 repository 的 Docker Hub user 或 organization |
| Secret | `DOCKERHUB_USERNAME` | 对 namespace 具推送权限的 Docker Hub user |
| Secret | `DOCKERHUB_TOKEN` | Docker Hub access token；请勿使用账号密码 |

推送符合格式的 release tag 会执行 `.github/workflows/release.yml`。发布前，workflow 会测试
CLI，并通过 standalone LibreOffice 与 gateway + Gotenberg 两个 Compose profile 实际执行
DOCX-to-PDF 转换。通过后才发布 Python distribution，并以 Buildx 推送具备 SBOM attestation
与 build provenance 的镜像：

```console
git tag -s v0.6.0 -m "Release v0.6.0"
git push origin v0.6.0
```

Tag 必须与 `pyproject.toml` 的版本一致。PyPI 与 Docker Hub 是独立 registry，因此 Python
distribution 发布后，Docker Hub job 仍可能失败；公告发行前应确认每个 release job 均成功。
若 Docker job 失败，可对相同 source tag 重新执行，Docker tags 会更新为相同内容。
