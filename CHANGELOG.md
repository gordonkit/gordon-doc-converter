# Changelog

All notable changes to this project will be documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and Semantic Versioning.

## [Unreleased]

## [0.4.0] - 2026-08-14

### Added

- Initial package, tooling, governance, and bilingual documentation baseline.
- Engine-neutral conversion contracts, engine policy, protocol, and fake engine.
- PDF existence, parseability, encryption, and page-count validation.
- Isolated LibreOffice probing and DOCX-to-PDF conversion with bounded subprocess execution,
  stable error mapping, output validation, and cleanup.
- Generated CJK LibreOffice integration coverage and a dedicated Linux workflow.
- Isolated Microsoft Word COM activation and conversion with explicit revision/comment
  display modes, bounded worker execution, stable errors, and deterministic COM cleanup.
- Mock COM lifecycle coverage plus a controlled Windows Word integration workflow.
- Shared cross-platform process runner for bounded engine subprocess execution.
- Public single and batch conversion service with policy-driven engine probing, strict-mode
  enforcement, automatic fallback diagnostics, staged validation, and safe overwrite.
- End-to-end public API coverage producing the same result contract through Word and
  LibreOffice.
