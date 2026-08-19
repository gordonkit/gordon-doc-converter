# Changelog

All notable changes to this project will be documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and Semantic Versioning.

## [Unreleased]

## [0.6.0] - 2026-08-19

### Added

- Versioned hierarchical YAML and JSON semantic artifacts with shared deterministic content,
  source-order IDs, document metadata controls, and explicit page provenance.
- Cross-format reverse locators with source/content fingerprints, OOXML element and table-cell
  paths for DOCX, and one-based page anchors for PDF.
- TTY-aware conversion progress for single and batch CLI commands, isolated on stderr with
  explicit `--progress` and `--no-progress` overrides.

## [0.5.1] - 2026-08-18

### Fixed

- Use absolute GitHub and documentation URLs in the package README so links work on PyPI.

## [0.5.0] - 2026-08-18

### Added

- DOCX semantic extraction for content controls, custom heading styles, Word numbering,
  Traditional Chinese numbering formats, text boxes, and nested list depth.
- Markdown and HTML nested-list serialization with continuation paragraphs.

### Changed

- Markdown output now normalizes Word list levels and generated tables for markdownlint.
- Runtime container builds apply available Debian security updates before installing
  profile packages.

### Fixed

- Restore content omitted from DOCX content controls and avoid duplicate compatibility
  representations from text boxes.
- Preserve numbering in table cells and restart child numbering across related Word
  numbering instances.

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
