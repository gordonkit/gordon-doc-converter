import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import type { Plugin } from "vite";
import { categories, type Locale, type Page, pages } from "./src/content";
import { parentOrganization, parentSiteLabel, parentSiteUrl } from "./src/parent";

const siteUrl = "https://docs.gordonkit.com";
/** The same `@id` gordonkit.com uses for this site in its own JSON-LD. */
const websiteId = `${siteUrl}/#website`;
const locales: Locale[] = ["en", "zh-TW", "zh-CN", "ja"];
const hreflang: Record<Locale, string> = { en: "en", "zh-TW": "zh-Hant-TW", "zh-CN": "zh-Hans-CN", ja: "ja" };
const openGraphLocale: Record<Locale, string> = { en: "en_US", "zh-TW": "zh_TW", "zh-CN": "zh_CN", ja: "ja_JP" };
const notApplicableLabel: Record<Locale, string> = {
  en: "Not applicable",
  "zh-TW": "不適用",
  "zh-CN": "不适用",
  ja: "該当なし",
};

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function pageUrl(locale: Locale, page: Page): string {
  return `${siteUrl}/${locale}/${page.id}/`;
}

function renderSection(page: Page, locale: Locale): string {
  const notApplicable = notApplicableLabel[locale];
  return page.sections.map((section) => {
    const interfaces = section.interfaces?.map((item) => `
      <section><h3>${escapeHtml(item.title[locale])}</h3><p>${escapeHtml(item.body[locale])}</p><code>${escapeHtml(item.example)}</code></section>`).join("") ?? "";
    const table = section.table ? `
      <table><caption>${escapeHtml(section.table.caption[locale])}</caption>
        <thead><tr>${section.table.headers[locale].map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead>
        <tbody>${section.table.rows[locale].map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell || notApplicable)}</td>`).join("")}</tr>`).join("")}</tbody>
      </table>` : "";
    const links = section.links?.map((link) => `<a href="${escapeHtml(link.href)}">${escapeHtml(link.label[locale])}</a>`).join(" ") ?? "";
    return `<section id="${escapeHtml(section.id)}">
      <h2>${escapeHtml(section.title[locale])}</h2>
      <p>${escapeHtml(section.body[locale])}</p>
      ${interfaces}${table}${section.code ? `<pre><code>${escapeHtml(section.code)}</code></pre>` : ""}${links}${section.note ? `<aside>${escapeHtml(section.note[locale])}</aside>` : ""}
    </section>`;
  }).join("");
}

function renderContent(page: Page, locale: Locale): string {
  const category = categories.find((item) => item.id === page.category);
  const navigation = pages.map((item) => `<a href="/${locale}/${item.id}/">${escapeHtml(item.title[locale])}</a>`).join(" ");
  return `<header><a href="/${locale}/overview/">GordonKit Document Converter</a><nav aria-label="Documentation">${navigation}</nav></header>
    <main><article>
      <p>${escapeHtml(category?.label[locale] ?? "")}</p>
      <h1>${escapeHtml(page.heading?.[locale] ?? page.title[locale])}</h1>
      <p>${escapeHtml(page.summary[locale])}</p>
      ${renderSection(page, locale)}
    </article></main>
    <footer><a href="https://github.com/gordonkit/gordon-doc-converter">GitHub</a> ${renderParentLink(locale)}</footer>`;
}

/** Visible in the served HTML, so the JSON-LD publisher is backed by a link a crawler can follow. */
function renderParentLink(locale: Locale): string {
  return `<span>${escapeHtml(parentSiteLabel[locale])}<a href="${parentSiteUrl(locale)}">gordonkit.com</a></span>`;
}

function renderMetadata(page: Page, locale: Locale): string {
  const title = `${page.heading?.[locale] ?? page.title[locale]} | GordonKit Docs`;
  const description = page.summary[locale];
  const url = pageUrl(locale, page);
  const alternateLocales = locales.filter((item) => item !== locale);
  const publisher = { "@id": parentOrganization.id };
  const structuredData = JSON.stringify({
    "@context": "https://schema.org",
    "@graph": [
      { "@type": "Organization", "@id": parentOrganization.id, name: parentOrganization.name, url: parentOrganization.url },
      {
        "@type": "WebSite",
        "@id": websiteId,
        name: "GordonKit Document Converter Documentation",
        url: `${siteUrl}/`,
        publisher,
      },
      {
        "@type": "TechArticle",
        headline: page.heading?.[locale] ?? page.title[locale],
        description,
        inLanguage: locale,
        url,
        isPartOf: { "@id": websiteId },
        publisher,
        about: {
          // codeRepository belongs to SoftwareSourceCode, not SoftwareApplication; with only the
          // latter, validator.schema.org flags it as an unknown field. The package is both.
          "@type": ["SoftwareApplication", "SoftwareSourceCode"],
          name: "GordonKit Document Converter",
          applicationCategory: "DeveloperApplication",
          operatingSystem: "Windows, Linux, macOS",
          codeRepository: "https://github.com/gordonkit/gordon-doc-converter",
          publisher,
        },
      },
    ],
  }).replaceAll("<", "\\u003c");

  return `<link rel="canonical" href="${url}" />
    ${locales.map((item) => `<link rel="alternate" hreflang="${hreflang[item]}" href="${pageUrl(item, page)}" />`).join("\n    ")}
    <link rel="alternate" hreflang="x-default" href="${pageUrl("en", page)}" />
    <meta name="robots" content="index, follow, max-image-preview:large" />
    <meta property="og:type" content="article" />
    <meta property="og:site_name" content="GordonKit Docs" />
    <meta property="og:locale" content="${openGraphLocale[locale]}" />
    ${alternateLocales.map((item) => `<meta property="og:locale:alternate" content="${openGraphLocale[item]}" />`).join("\n    ")}
    <meta property="og:title" content="${escapeHtml(title)}" />
    <meta property="og:description" content="${escapeHtml(description)}" />
    <meta property="og:url" content="${url}" />
    <meta name="twitter:card" content="summary" />
    <meta name="twitter:title" content="${escapeHtml(title)}" />
    <meta name="twitter:description" content="${escapeHtml(description)}" />
    <script type="application/ld+json">${structuredData}</script>`;
}

function renderPage(template: string, page: Page, locale: Locale): string {
  const title = `${page.heading?.[locale] ?? page.title[locale]} | GordonKit Docs`;
  return template
    .replaceAll("\r\n", "\n")
    .replace('<html lang="en">', `<html lang="${locale}">`)
    .replace(/<meta name="description" content="[^"]*" \/>/, `<meta name="description" content="${escapeHtml(page.summary[locale])}" />`)
    .replace(/<title>[^<]*<\/title>/, `<title>${escapeHtml(title)}</title>`)
    .replace("</head>", `    ${renderMetadata(page, locale)}\n  </head>`)
    .replace('<div id="root"></div>', `<div id="root">${renderContent(page, locale)}</div>`)
    .replace(/[ \t]+(?=\r?$)/gm, "");
}

const localeNames: Record<Locale, string> = { en: "English", "zh-TW": "繁體中文", "zh-CN": "简体中文", ja: "日本語" };
const englishLocaleNames: Record<Locale, string> = { en: "English", "zh-TW": "Traditional Chinese", "zh-CN": "Simplified Chinese", ja: "Japanese" };

/**
 * A top-level 404.html turns off the single-page fallback of Cloudflare Pages, so an address that
 * names no page answers 404 instead of 200 with the overview. It is plain HTML without the app:
 * the app would read the unknown path as "overview" and render that page over the message.
 */
function renderNotFound(): string {
  const links = locales
    .map((locale) => `<li><a href="/${locale}/overview/" hreflang="${hreflang[locale]}">${escapeHtml(localeNames[locale])}</a></li>`)
    .join("\n        ");
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="robots" content="noindex" />
    <title>Page not found | GordonKit Docs</title>
  </head>
  <body>
    <main>
      <h1>Page not found</h1>
      <p>This address is not part of the GordonKit Document Converter documentation. Choose a language to open the overview.</p>
      <ul>
        ${links}
      </ul>
      <p>${renderParentLink("en")}</p>
    </main>
  </body>
</html>
`;
}

/**
 * `/llms.txt` in the llmstxt.org format: one Markdown file that tells a language model what this
 * site documents and where each page is. It is written in English, with the other languages named
 * at the end, and every line reuses the page's own heading and summary, so it cannot describe a
 * page differently from the page. The opening links to the GordonKit list, so a model that only
 * reaches this site still learns who publishes it and what else they publish.
 */
function renderLlmsText(): string {
  const overview = pages[0];
  const item = (page: Page) => `- [${page.heading?.en ?? page.title.en}](${pageUrl("en", page)}): ${page.summary.en}`;
  const sections = categories.flatMap((category) => {
    const members = pages.filter((page) => page.category === category.id);
    return members.length === 0 ? [] : [`## ${category.label.en}`, "", ...members.map(item), ""];
  });
  const otherLocales = locales
    .filter((locale) => locale !== "en")
    .map((locale) => `- [${localeNames[locale]}](${pageUrl(locale, overview)}): The same documentation in ${englishLocaleNames[locale]}, under /${locale}/.`);
  return [
    "# GordonKit Document Converter",
    "",
    `> ${overview.summary.en}`,
    "",
    `This is the documentation of gordon-doc-converter, an open-source project published by ${parentOrganization.name}. The [source code](https://github.com/gordonkit/gordon-doc-converter) is on GitHub. ${parentOrganization.name} lists all of its sites in [gordonkit.com/llms.txt](${parentOrganization.url}llms.txt).`,
    "",
    ...sections,
    "## Optional",
    "",
    ...otherLocales,
    `- [${parentOrganization.name}](${parentOrganization.url}llms.txt): Every site ${parentOrganization.name} publishes.`,
    "",
  ].join("\n");
}

export function seoPagesPlugin(outputDirectory: string): Plugin {
  return {
    name: "gordonkit-seo-pages",
    apply: "build",
    async closeBundle() {
      const templatePath = join(outputDirectory, "index.html");
      const template = await readFile(templatePath, "utf8");
      for (const locale of locales) {
        for (const page of pages) {
          const pageDirectory = join(outputDirectory, locale, page.id);
          await mkdir(pageDirectory, { recursive: true });
          await writeFile(join(pageDirectory, "index.html"), renderPage(template, page, locale), "utf8");
        }
      }

      await writeFile(templatePath, renderPage(template, pages[0], "en"), "utf8");
      const sitemap = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n${pages.flatMap((page) => locales.map((locale) => `  <url><loc>${pageUrl(locale, page)}</loc>${locales.map((item) => `<xhtml:link rel="alternate" hreflang="${hreflang[item]}" href="${pageUrl(item, page)}"/>`).join("")}</url>`)).join("\n")}\n</urlset>\n`;
      await writeFile(join(outputDirectory, "sitemap.xml"), sitemap, "utf8");
      await writeFile(join(outputDirectory, "404.html"), renderNotFound(), "utf8");
      await writeFile(join(outputDirectory, "llms.txt"), renderLlmsText(), "utf8");
      // A locale root names no page of its own. It used to reach the overview only through the
      // single-page fallback that 404.html turns off, so it is redirected there explicitly.
      const redirects = locales.flatMap((locale) => [`/${locale} /${locale}/overview/ 301`, `/${locale}/ /${locale}/overview/ 301`]);
      await writeFile(join(outputDirectory, "_redirects"), `${redirects.join("\n")}\n`, "utf8");
      await writeFile(join(outputDirectory, "robots.txt"), `User-agent: *\nContent-Signal: search=yes,ai-input=yes,ai-train=yes\nAllow: /\n\nSitemap: ${siteUrl}/sitemap.xml\n`, "utf8");
    },
  };
}