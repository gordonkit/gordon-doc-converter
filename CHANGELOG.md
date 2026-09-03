# Changelog

All notable changes to this project will be documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and Semantic Versioning.

## [Unreleased]

## [0.9.0] - 2026-09-03

### Added

- Character formatting in the normalized content model. Inline spans now carry an orthogonal
  `styles` set (`strong`, `emphasis`, `code`), so bold, italic, and monospace runs survive
  extraction instead of being flattened to plain text. Styles combine with the existing span
  kinds, letting a link or a tracked revision stay itself while also carrying emphasis.
- Code blocks, block quotes, and thematic breaks in the normalized content model, as the
  `code-block` and `thematic-break` block kinds plus `quote_level` and `language` block
  fields. DOCX reads them from the `Quote` and `HTML Preformatted` paragraph styles, ODT from
  `Quotations` and `Preformatted Text`, and HTML from `<blockquote>`, `<pre>`, and `<hr>`.
- Markdown and HTML writers render the new facts: `**strong**`, `*emphasis*`, backtick code
  spans whose fence clears any backticks they contain, fenced code blocks with their info
  string, `> ` quote prefixes, and `---` rules; HTML emits `<strong>`, `<em>`, `<code>`,
  `<pre><code class="language-...">`, nested `<blockquote>`, and `<hr>`.
- Markdown-to-HTML, Markdown-to-YAML, and Markdown-to-JSON conversion through the same
  semantic extraction used for DOCX, ODT, PDF, and HTML sources, with no external engine
  required. CommonMark is parsed with the GFM table and strikethrough extensions: headings,
  paragraphs, nested and ordered lists, tables, links, emphasis, code spans, fenced and
  indented code blocks, block quotes, and thematic breaks are normalized into the existing
  schema. A leading YAML front-matter block becomes document metadata, inline `data:` images
  become shared assets, images referenced by path or URL stay linked, and raw HTML blocks are
  omitted apart from the `<ins>`, `<del>`, and `<br>` tags the writers emit. Blocks carry a
  `markdown-line` source anchor.
- Markdown source validation covering extension, declared MIME type, and file size.
- Markdown-to-ODT and Markdown-to-page-image conversion, plus the same two artifacts from
  HTML sources. ODT is produced by LibreOffice from the print-ready HTML intermediate, which
  carries the A4 page setup and CJK fonts into the ODF page layout; page images rasterize the
  rendered PDF through the existing raster route and reuse a PDF artifact when one was
  requested in the same run, instead of rendering it twice.
- `gordon-doc template notes.md` writes a Markdown starter whose YAML front matter carries
  document metadata. The command now picks the starter from the output extension, so
  `.html`/`.htm` still writes the A4 print-ready document; `--orientation` applies to HTML
  templates only, since Markdown holds no page setup of its own, and the JSON payload reports
  the `format` written.
- GFM task-list checkboxes in Markdown sources. `- [ ]` and `- [x]` items now carry the
  □ and ☑ symbols instead of literal brackets, so every output renders what the author
  wrote.
- Markup PDF and DOCX fall back to LibreOffice when wkhtmltopdf or Pandoc is unavailable,
  reporting an `ENGINE_FALLBACK` warning that names the substituted engine. The container
  image carries LibreOffice alone, so Markdown and HTML sources could previously produce
  neither artifact inside it; wkhtmltopdf cannot be added, having been dropped from Debian
  after upstream archived it. LibreOffice reads the same print-ready intermediate and keeps
  the A4 page setup, table grid, and CJK fonts, but renders headings in a different face and
  leaves table headers unshaded, so an installation carrying wkhtmltopdf or Pandoc still
  renders through them.

### Changed

- Rendered Markdown output now goes through the normalized content model. Markdown is
  extracted, serialized to a print-ready A4 HTML intermediate carrying the same CSS as
  `gordon-doc template`, and only then handed to Pandoc. PDF and DOCX from Markdown therefore
  get the CJK font stack, `@page` A4 margins, and one consistent look shared with HTML
  sources, and raw HTML in the source never reaches the PDF engine.
- `write_blank_html_template` became `write_blank_template`, which returns the `SourceFormat`
  it wrote. The compatibility tables in all four README locales and on the documentation site
  now show ODT and page images for HTML and Markdown sources.
- The LibreOffice file adapter accepts HTML sources, loading them with the
  `HTML (StarWriter)` import filter and saving through an explicit output filter, so an HTML
  source becomes a Writer text document rather than a Writer/Web document without page setup.
- Pandoc reads Markdown as `gfm` rather than Pandoc's own dialect, and receives a
  `--resource-path` pointing at the source directory, so images referenced by relative path
  resolve against the document instead of the working directory.
- Markup PDF output is rendered by wkhtmltopdf directly instead of through Pandoc. Pandoc's
  HTML reader keeps only the body and the document metadata, so it replaced the print
  stylesheet with its own defaults and added a second title block: rendered pages came out
  36em wide on a tinted background with the title printed twice. The engine now reads the
  document as written, with A4, the requested orientation, and the stylesheet's 20mm margins
  passed as arguments, since wkhtmltopdf ignores `@page`. The earlier `--variable geometry:`
  settings only ever applied to LaTeX templates and were silently ignored.
- The DOCX intermediate leaves the visible title block out, because Pandoc's DOCX writer
  renders its own from the head metadata. Title and author appeared twice before.
- DOCX output from markup sources is rendered against a generated `--reference-doc` whose
  default and named styles use CJK-capable fonts at the same 10.5pt body size as the HTML
  print stylesheet, instead of leaving Pandoc's default fonts in place.
- The structured JSON and YAML schema is now version `1.4`. Inline payloads gain an optional
  `styles` array, and block payloads gain optional `quote_level` and `language` fields. Every
  1.3 field keeps its meaning, so existing readers continue to work.
- `markdown-it-py` is now a direct dependency, used only by the Markdown content reader. It
  was already installed transitively, so no new package enters the environment.

### Fixed

- Markup and semantic artifacts are published across a filesystem boundary. They were moved
  onto the output path with `Path.rename`, which raises `EXDEV` when the temporary staging
  directory and the destination are different devices — routinely the case for a mounted
  output directory in a container, where every markup and semantic conversion failed at the
  final move regardless of engine.
- Tables rendered by LibreOffice carry their grid. Its HTML importer ignores the border
  declarations on `th` and `td`, so imported tables arrived with no borders at all; the print
  intermediate now also carries the presentational `border` attribute, which is the only
  instruction it honours. wkhtmltopdf continues to use the stylesheet, which outranks the
  attribute in the cascade.
- Thematic breaks appear in wkhtmltopdf output. Its WebKit discards a sub-pixel top border,
  so every `---` in a Markdown or HTML source rendered as nothing; the rule is drawn as a
  filled block instead.

## [0.8.0] - 2026-08-28

### Added

- Native ODT semantic extraction, so ODT sources convert to Markdown, HTML, YAML, JSON, and
  page images in addition to DOCX and PDF. Content is read directly from the ODF package
  without modifying the source: headings with `text:outline-style` chapter numbering, nested
  lists with `text:list-style` markers and `text:display-levels`, tables with repeated and
  covered cells, links, embedded images, `office:annotation` comments, `text:tracked-changes`
  revisions, drawing text boxes, sections, and `meta.xml` document properties. Markdown, HTML,
  YAML, and JSON need no external engine; ODT page images render through LibreOffice first.
- Requests mixing office-file artifacts with semantic or page-image artifacts, such as
  `--to docx --to markdown` from an ODT source, now produce every artifact under one shared
  output stem with independent per-artifact status.
- HTML-to-Markdown, HTML-to-YAML, and HTML-to-JSON conversion through the same semantic
  extraction used for DOCX and PDF sources, with no external engine required. Headings,
  paragraphs, nested and ordered lists, tables, links, `<ins>`/`<del>` revisions, and
  `<title>`/`<meta>` metadata are normalized into the existing schema; inline `data:` images
  become shared assets, and omitted or lossy content is reported as warnings.
- HTML source validation covering extension, declared MIME type, file size, encoding
  detection, and a bound on element nesting depth.
- `--json-lines` (`ConversionOptions.json_lines`) writes the JSON artifact for DOCX, PDF, and
  HTML sources as newline-delimited JSON to `<stem>.jsonl`. Records carry the same versioned
  schema as the nested document: one `document` record, every block in source order with its
  enclosing `section_path`, then `asset`, `annotation`, and `warning` records.
- Google Analytics (gtag.js) on the documentation site, injected into both Vite entry
  points so it covers every generated locale page and the Swagger API reference.
- Simplified Chinese documentation site locale under `/zh-CN/<topic>/`, using mainland
  Chinese terminology, with localized metadata, hreflang and Open Graph alternates,
  sitemap entries, and a language dropdown entry.
- Simplified Chinese `README.zh-CN.md` and `docker/README.zh-CN.md` translations, linked
  from the existing English, Traditional Chinese, and Japanese READMEs.
- Japanese documentation site locale under `/ja/<topic>/`, with localized metadata, hreflang
  and Open Graph alternates, and sitemap entries.
- Japanese `README.ja.md` and `docker/README.ja.md` translations, linked from the existing
  English and Traditional Chinese READMEs.

### Changed

- Markdown and HTML writers now keep image targets referenced by URL instead of dropping
  them to alt text.
- Replaced the documentation navigation bar's two-way language toggle with a language
  dropdown covering English, Traditional Chinese, and Japanese.
- Pinned generated `docs/**/*.html` to LF in `.gitattributes`, so a Windows checkout
  cannot rewrite the inline analytics block to CRLF and invalidate its byte-exact
  Content-Security-Policy hash.

### Fixed

- HTML sources written with CRLF or lone CR line endings now normalize to LF while decoding,
  as HTML parser preprocessing requires. Preformatted text previously kept its carriage
  returns, so the same document extracted differently depending on the platform that wrote it
  and a stray CR reached the Markdown, HTML, YAML, and JSON artifacts.

### Security

- Widened the documentation site's Content-Security-Policy to admit Google Analytics:
  `googletagmanager.com` in `script-src` with a `sha256` hash for the inline config block
  instead of `unsafe-inline`, plus the analytics endpoints in `connect-src` and `img-src`.

## [0.7.0] - 2026-08-25

### Added

- Microsoft Word COM support for high-fidelity DOCX-to-HTML conversion.
- PDF layout analysis that infers headings and ordered or unordered lists for semantic
  artifacts.
- Expanded bilingual documentation, search metadata, sitemap, and mobile navigation.

### Fixed

- Preserve DOCX numbered paragraphs as list items during semantic extraction.
- Render source-numbered items as ordered lists in Markdown output.

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
