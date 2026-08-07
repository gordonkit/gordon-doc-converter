# Git 分支與整合流程

本專案採用以 `main` 為核心的 trunk-based workflow。

## 分支

- `main` 是唯一的長期整合分支，必須維持可建置及可測試。
- 每項變更都應從最新的 `main` 建立短期分支。
- Pull request 合併後刪除來源分支。
- 不建立永久性的 `develop`、個人或環境分支。

分支名稱格式如下：

```text
<type>/<short-description>
```

允許的類型為 `feature`、`fix`、`docs`、`test`、`refactor`、`chore` 與 `ci`。使用小寫
英文，以連字號分隔，例如：

```text
feature/add-gotenberg-health-check
fix/cleanup-timeout-process
docs/document-branch-workflow
```

## Pull Request

- Pull request 統一提交至 `main`。
- 每個 pull request 維持單一、清楚的邏輯變更。
- 分支落後 `main` 時，合併前先同步最新內容。
- 格式化、lint、型別檢查、測試與 build 都必須通過。
- 除非有明確且已記錄的理由，否則使用 squash merge。
- 合併後刪除來源分支。

Repository 應在託管平台設定 `main` branch protection、必要的 pull request review，
以及合併前必須通過 CI。這些設定由託管平台維護，不由本文件取代。

## Commit

使用 Conventional Commits，主旨使用祈使語氣的英文，長度不超過 72 個字元：

```text
<type>(<scope>): <imperative summary>
```

例如 `feat(cli): add dry-run option` 與 `fix(pdf): reject encrypted input`。

## Release

從 `main` 建立符合 Semantic Versioning 的版本 tag，例如 `v0.1.0`。目前 release
workflow 會處理符合 `v<major>.<minor>.<patch>` 格式的 tag。

只有在版本需要一段穩定化期間時，才建立暫時性的 `release/vX.Y.Z` 分支。必要修正
應同步合併回 `main`，發布後刪除 release 分支。緊急修正仍使用一般的 `fix/` 流程，
不維護永久性的 `hotfix` 分支。
