# コンテナーイメージと Profiles

[English](README.md) · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md)

単一の `gordonkit/gordon-doc-converter` イメージが CLI と HTTP API の両方を提供します。
Compose ファイルには、明示的に選択する 3 つの profile があります。

- `standalone-lo`: イメージに含まれる LibreOffice を使うプライベートな HTTP API。
- `gateway-gotenberg`: 同じ HTTP API イメージと、別立ての Gotenberg renderer。
- `cli`: 同梱の LibreOffice を使い、`/work` をドキュメント用ボリュームとするコマンドラインモード。

タグ付きリリースでは、1 つの Docker Hub リポジトリを公開します。

- `<namespace>/gordon-doc-converter`

`v0.6.0` のようなリリースタグは、そのリポジトリに `0.6.0`、`0.6`、`latest` のイメージタグを
公開します。現在の対象プラットフォームは `linux/amd64` です。

イメージの entrypoint は既定で CLI を実行します。HTTP API を起動するには、最初の引数として
`api` を渡してください。

```console
docker run --rm gordonkit/gordon-doc-converter:latest version
docker run --rm --publish 8000:8000 \
  --env GORDON_DOC_API_KEY=replace-me \
  gordonkit/gordon-doc-converter:latest api
```

Compose ファイルは、現在のソースツリーから `gordonkit/gordon-doc-converter:local` をビルド
します。開発と検証にはこれを使い、再現性が必要な配備にはバージョン付きの Docker Hub タグを
使ってください。

## CLI profile

CLI profile に API key は不要です。リポジトリのルートから Bash または PowerShell で次の
コマンドを実行します。カレントディレクトリは `/work` にマウントされます。

```console
docker compose -f docker/compose.yaml --profile cli run --rm --build cli convert /work/report.docx --output /work/report.pdf --engine libreoffice --overwrite
```

## API profiles

API profile を起動する前に、強度の高い `GORDON_DOC_API_KEY` を設定してください。同じ Compose
コマンドが Bash でも PowerShell でも動くよう、リポジトリのルートに追跡対象外の `.env` を作成
します。

```dotenv
GORDON_DOC_API_KEY=replace-with-a-strong-random-value
```

この key は配備者が作成・管理するもので、外部サービスから発行されるものではありません。
`.env` はコミットしないでください。変換リクエストは、DOCX のバイト列を request body に、
OOXML MIME type を `Content-Type` に、元のファイル名を `X-Filename` に指定します。API は上限
付きの OOXML 検証を行い、注入可能な認証、マルウェアスキャン、内容を含まない telemetry の hook
を受け付けます。本番の ingress では、リクエストボディの上限も設定し、複数レプリカを使う場合は
分散型のレート制限を提供する必要があります。

### 単体構成の LibreOffice API

```console
docker compose -f docker/compose.yaml --env-file .env --profile standalone-lo up --detach --build
```

Bash:

```bash
set -a; . ./.env; set +a
curl --fail http://127.0.0.1:8000/live
curl --fail-with-body -H "Authorization: Bearer $GORDON_DOC_API_KEY" -H "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document" -H "X-Filename: report.docx" --data-binary @report.docx "http://127.0.0.1:8000/conversions?engine=libreoffice" --output report-api.pdf
```

PowerShell:

```powershell
$env:GORDON_DOC_API_KEY = ((Get-Content .env | Where-Object { $_ -match '^GORDON_DOC_API_KEY=' }) -replace '^GORDON_DOC_API_KEY=', '')
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/live'
$headers = @{ Authorization = "Bearer $env:GORDON_DOC_API_KEY"; 'X-Filename' = 'report.docx' }
Invoke-WebRequest -Uri 'http://127.0.0.1:8000/conversions?engine=libreoffice' -Method Post -Headers $headers -ContentType 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' -InFile .\report.docx -OutFile .\report-api.pdf
```

### Gotenberg gateway API

Compose は API と Gotenberg の service を同じ `gordon-doc` network に接続し、Gotenberg が
healthy になるまで待機してから、API が `http://gotenberg:3000` を呼び出すよう設定します。

```console
docker compose -f docker/compose.yaml --env-file .env --profile gateway-gotenberg up --detach --build
```

Bash:

```bash
set -a; . ./.env; set +a
curl --fail-with-body -H "Authorization: Bearer $GORDON_DOC_API_KEY" -H "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document" -H "X-Filename: report.docx" --data-binary @report.docx "http://127.0.0.1:8000/conversions?engine=gotenberg" --output report-gb.pdf
```

PowerShell:

```powershell
$env:GORDON_DOC_API_KEY = ((Get-Content .env | Where-Object { $_ -match '^GORDON_DOC_API_KEY=' }) -replace '^GORDON_DOC_API_KEY=', '')
$headers = @{ Authorization = "Bearer $env:GORDON_DOC_API_KEY"; 'X-Filename' = 'report.docx' }
Invoke-WebRequest -Uri 'http://127.0.0.1:8000/conversions?engine=gotenberg' -Method Post -Headers $headers -ContentType 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' -InFile .\report.docx -OutFile .\report-gb.pdf
```

`GORDON_DOC_GOTENBERG_URL` を設定すると、API は明示的に Gotenberg を既定エンジンにします。
接続や変換の失敗は呼び出し元に返され、同梱の LibreOffice エンジンへ暗黙にフォールバックする
ことはありません。ローカル組版を意図したポリシーの場合は `standalone-lo` profile を使って
ください。

テスト後は、どちらの API profile も停止してください。

```console
docker compose -f docker/compose.yaml --profile standalone-lo down
docker compose -f docker/compose.yaml --profile gateway-gotenberg down
```

イメージは非 root ユーザー、読み取り専用の root filesystem、上限付きの `/tmp` tmpfs で実行され
ます。アップロードされたドキュメントと生成されたドキュメントは、各リクエストが返る前に削除
されます。Microsoft Office のコンポーネントや Microsoft のフォントは含まれておらず、イメージ
には Noto CJK フォントをインストールしています。

プロジェクトのライセンスとサードパーティー表示のファイルは
`/usr/share/licenses/gordon-doc-converter/` 以下にインストールされます。コンテナーの CI は
CycloneDX SBOM も公開します。

起動後、`python docker/smoke.py --token replace-me --docx sample.docx` を実行すると、ヘルス、
認証付きのエンジン一覧、および任意でエンドツーエンドの変換を確認できます。

## Docker Hub リリースの設定

上記のリポジトリを、対象の Docker Hub ユーザーまたは組織に作成してください。読み取りと書き込み
権限を持つ Docker Hub のアクセストークンを作成し、GitHub リポジトリの
**Settings > Secrets and variables > Actions** で次の設定を行います。

| 種別 | 名前 | 値 |
| --- | --- | --- |
| Variable | `DOCKERHUB_NAMESPACE` | リポジトリを所有する Docker Hub のユーザーまたは組織 |
| Secret | `DOCKERHUB_USERNAME` | 該当 namespace に push できる Docker Hub ユーザー |
| Secret | `DOCKERHUB_TOKEN` | Docker Hub のアクセストークン。アカウントのパスワードは使わない |

対応するリリースタグを push すると `.github/workflows/release.yml` が実行されます。公開前に、
workflow は CLI を実行し、standalone LibreOffice と gateway + Gotenberg の両 Compose profile で
実際の DOCX から PDF への変換を行います。その後、Python の配布物を公開し、Buildx、SBOM の
attestation、build provenance を付けてイメージを push します。

```console
git tag -s v0.6.0 -m "Release v0.6.0"
git push origin v0.6.0
```

タグは `pyproject.toml` のバージョンと一致している必要があります。PyPI と Docker Hub は独立した
レジストリのため、Python の配布物を公開した後に Docker Hub 側で失敗することがあります。
リリースを告知する前に、すべてのリリースジョブを確認してください。失敗した Docker ジョブを同じ
ソースタグで再実行すると、Docker のタグは同じ内容に更新されます。
