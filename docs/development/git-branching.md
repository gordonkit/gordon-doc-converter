# Git Branching and Integration Workflow

This project uses a trunk-based workflow centered on `main`.

## Branches

- `main` is the only long-lived integration branch.
- It must remain buildable and testable.
- Create a short-lived branch from the latest `main` for every change.
- Delete the branch after its pull request is merged.
- Do not create permanent `develop`, personal, or environment branches.

Use the following branch name format:

```text
<type>/<short-description>
```

Allowed types are `feature`, `fix`, `docs`, `test`, `refactor`, `chore`, and `ci`.
Use lowercase English words separated by hyphens, for example:

```text
feature/add-gotenberg-health-check
fix/cleanup-timeout-process
docs/document-branch-workflow
```

## Pull Requests

- Open pull requests against `main`.
- Keep each pull request focused on one logical change.
- Update the branch from `main` before merging when it has become stale.
- Required checks must pass: format, lint, types, tests, and build.
- Use squash merge unless individual commits need to be preserved.
- Delete the source branch after merging.

Repository settings should protect `main` and require pull request review.
They should also require CI status checks before merging.
The hosting provider maintains these settings.

## Commits

Use Conventional Commits with an imperative English subject no longer than 72
characters:

```text
<type>(<scope>): <imperative summary>
```

Examples: `feat(cli): add dry-run option` and `fix(pdf): reject encrypted input`.

## Releases

Create a semantic version tag from `main`, such as `v0.1.0`.
The release workflow publishes matching `v<major>.<minor>.<patch>` tags.

Create a temporary `release/vX.Y.Z` branch only for release stabilization.
Merge fixes back to `main` and remove the branch after publishing.
Use `fix/` for urgent corrections; do not maintain a permanent `hotfix` branch.
