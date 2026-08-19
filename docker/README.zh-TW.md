# 容器映像與 Profiles

[English](README.md)

單一 `gordonkit/gordon-doc-converter` 映像同時提供 CLI 與 HTTP API。Compose 檔案提供三個
必須明確選用的 profile：

- `standalone-lo`：HTTP API 使用映像內建的 LibreOffice。
- `gateway-gotenberg`：相同的 HTTP API 映像搭配獨立 Gotenberg renderer。
- `cli`：命令列模式使用內建 LibreOffice，並以 `/work` 作為文件 volume。

正式版本會發布至單一 Docker Hub repository：

- `<namespace>/gordon-doc-converter`

例如 `v0.5.1` 會發布 `0.5.1`、`0.5` 與 `latest` 三個 image tag。目前映像目標平台為
`linux/amd64`。

映像 entrypoint 預設執行 CLI；第一個參數傳入 `api` 則會啟動 HTTP API：

```console
docker run --rm gordonkit/gordon-doc-converter:latest version
docker run --rm --publish 8000:8000 \
  --env GORDON_DOC_API_KEY=replace-me \
  gordonkit/gordon-doc-converter:latest api
```

Compose 檔案會從目前 source tree 建置 `gordonkit/gordon-doc-converter:local`，適合開發與
驗證。需要可重現部署時，請使用 Docker Hub 的明確版本 tag。

## API Profiles

啟動 API profile 前，請設定高強度 `GORDON_DOC_API_KEY`。轉換 request body 為 DOCX bytes，
`Content-Type` 使用 OOXML MIME type，並透過 `X-Filename` 傳入原始 basename。API 會執行有
資源限制的 OOXML 驗證，並提供可注入的認證、malware scanning 與不含文件內容的 telemetry
hooks。多 replica 正式環境仍須由 ingress 限制 request body 並提供分散式 rate limiting。

使用內建 LibreOffice：

```sh
GORDON_DOC_API_KEY=replace-me docker compose -f docker/compose.yaml \
  --profile standalone-lo up --build
```

使用 Gotenberg：

```sh
GORDON_DOC_API_KEY=replace-me docker compose -f docker/compose.yaml \
  --profile gateway-gotenberg up --build
```

Compose 會將 API 與 Gotenberg service 加入同一個 `gordon-doc` network，等待 Gotenberg
健康後再啟動 API，並將 API 設為呼叫 `http://gotenberg:3000`。

設定 `GORDON_DOC_GOTENBERG_URL` 後，API 會明確以 Gotenberg 為預設引擎。連線或轉換失敗
會回傳給呼叫端，不會靜默改用映像內建的 LibreOffice。若政策要求本機排版，請使用
`standalone-lo` profile。

API 啟動後可執行：

```sh
curl --fail http://localhost:8000/live
curl --fail -H "Authorization: Bearer replace-me" \
  -H "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document" \
  -H "X-Filename: sample.docx" --data-binary @sample.docx \
  http://localhost:8000/conversions --output converted.pdf
```

映像以非 root 使用者、唯讀 root filesystem 與有限 `/tmp` tmpfs 執行。每個 request 回傳前
都會刪除上傳與產出文件。映像不含 Microsoft Office 元件或 Microsoft 字型；CJK 支援使用
Noto CJK 字型。Project license 與第三方聲明安裝於
`/usr/share/licenses/gordon-doc-converter/`，container CI 也會產生 CycloneDX SBOM。

啟動後可使用下列 smoke client 檢查 health、經認證的 engine inventory，以及選用的端到端
轉換：

```console
python docker/smoke.py --token replace-me --docx sample.docx
```

## Docker Hub 發布設定

先在預定的 Docker Hub user 或 organization 建立 `<namespace>/gordon-doc-converter`，再建立
具備 read/write 權限的 Docker Hub access token。到 GitHub repository 的
**Settings > Secrets and variables > Actions** 設定：

| 類型 | 名稱 | 值 |
| --- | --- | --- |
| Variable | `DOCKERHUB_NAMESPACE` | 擁有 repository 的 Docker Hub user 或 organization |
| Secret | `DOCKERHUB_USERNAME` | 對 namespace 具推送權限的 Docker Hub user |
| Secret | `DOCKERHUB_TOKEN` | Docker Hub access token；請勿使用帳號密碼 |

推送符合格式的 release tag 會執行 `.github/workflows/release.yml`。發布前，workflow 會測試
CLI，並透過 standalone LibreOffice 與 gateway + Gotenberg 兩個 Compose profile 實際執行
DOCX-to-PDF 轉換。通過後才發布 Python distribution，並以 Buildx 推送具備 SBOM attestation
與 build provenance 的映像：

```console
git tag -s v0.5.1 -m "Release v0.5.1"
git push origin v0.5.1
```

Tag 必須與 `pyproject.toml` 的版本一致。PyPI 與 Docker Hub 是獨立 registry，因此 Python
distribution 發布後，Docker Hub job 仍可能失敗；公告發行前應確認每個 release job 均成功。
若 Docker job 失敗，可對相同 source tag 重新執行，Docker tags 會更新為相同內容。
