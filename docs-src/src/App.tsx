import {
  Bars3Icon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ClipboardDocumentIcon,
  CodeBracketIcon,
  CommandLineIcon,
  CubeTransparentIcon,
  ArrowDownTrayIcon,
  ArrowTopRightOnSquareIcon,
  LanguageIcon,
  MagnifyingGlassIcon,
  MoonIcon,
  SunIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { useEffect, useState } from "react";
import { categories, type Locale, pages } from "./content";

const labels = {
  en: { search: "Search documentation", close: "Close search", onPage: "On this page", menu: "Open navigation", copy: "Copy code", copied: "Copied", previous: "Previous", next: "Next", results: "Search results", noResults: "No matching documentation" },
  "zh-TW": { search: "搜尋文件", close: "關閉搜尋", onPage: "本頁內容", menu: "開啟導覽", copy: "複製程式碼", copied: "已複製", previous: "上一頁", next: "下一頁", results: "搜尋結果", noResults: "找不到符合的文件" },
};

function Logo() {
  return (
    <span className="flex items-center gap-2.5">
      <span className="grid h-8 w-8 place-items-center bg-ink text-white dark:bg-white dark:text-ink"><CubeTransparentIcon className="h-5 w-5" /></span>
      <span className="font-semibold tracking-normal text-ink dark:text-white">GordonKit <span className="font-normal text-slate-400">Docs</span></span>
    </span>
  );
}

function App() {
  const [locale, setLocale] = useState<Locale>(() => (localStorage.getItem("gk-locale") as Locale) || "en");
  const [dark, setDark] = useState(() => localStorage.getItem("gk-theme") === "dark" || (!localStorage.getItem("gk-theme") && matchMedia("(prefers-color-scheme: dark)").matches));
  const [pageId, setPageId] = useState(() => location.hash.slice(1).split("/")[0] || "overview");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const pageIndex = Math.max(0, pages.findIndex((item) => item.id === pageId));
  const page = pages[pageIndex];
  const t = labels[locale];

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("gk-theme", dark ? "dark" : "light");
  }, [dark]);

  useEffect(() => {
    document.documentElement.lang = locale;
    localStorage.setItem("gk-locale", locale);
    document.title = `${page.heading?.[locale] ?? page.title[locale]} | GordonKit Docs`;
  }, [locale, page]);

  useEffect(() => {
    const onHashChange = () => setPageId(location.hash.slice(1).split("/")[0] || "overview");
    addEventListener("hashchange", onHashChange);
    return () => removeEventListener("hashchange", onHashChange);
  }, []);

  const navigate = (id: string) => {
    location.hash = id;
    setPageId(id);
    setMobileOpen(false);
    scrollTo({ top: 0, behavior: "smooth" });
  };

  const matches = query.trim()
    ? pages.filter((item) => [item.title[locale], item.summary[locale], ...item.sections.flatMap((section) => [section.title[locale], section.body[locale], ...(section.interfaces?.flatMap((entry) => [entry.title[locale], entry.label[locale], entry.body[locale]]) ?? [])])].join(" ").toLowerCase().includes(query.toLowerCase()))
    : pages;

  return (
    <div className="min-h-screen bg-white text-slate-700 antialiased dark:bg-[#11161d] dark:text-slate-300">
      <header className="fixed inset-x-0 top-0 z-40 h-16 border-b border-slate-200 bg-white/95 backdrop-blur dark:border-slate-800 dark:bg-[#11161d]/95">
        <div className="flex h-full items-center px-4 lg:px-6">
          <button className="mr-3 p-1.5 text-slate-500 lg:hidden" onClick={() => setMobileOpen(true)} aria-label={t.menu}><Bars3Icon className="h-6 w-6" /></button>
          <button onClick={() => navigate("overview")}><Logo /></button>
          <button className="ml-auto flex h-9 w-44 items-center gap-2 border border-slate-300 bg-slate-50 px-3 text-sm text-slate-500 transition hover:border-slate-400 md:w-64 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400" onClick={() => setSearchOpen(true)}>
            <MagnifyingGlassIcon className="h-4 w-4" /><span className="truncate">{t.search}</span>
          </button>
          <div className="ml-3 flex items-center border-l border-slate-200 pl-3 dark:border-slate-800">
            <button className="icon-button" onClick={() => setLocale(locale === "en" ? "zh-TW" : "en")} aria-label="Change language"><LanguageIcon className="h-5 w-5" /><span className="hidden text-xs font-semibold sm:block">{locale === "en" ? "EN" : "繁中"}</span></button>
            <button className="icon-button" onClick={() => setDark(!dark)} aria-label="Toggle theme">{dark ? <SunIcon className="h-5 w-5" /> : <MoonIcon className="h-5 w-5" />}</button>
            <a className="icon-button hidden sm:flex" href="https://github.com/gordonkit/gordon-doc-converter" aria-label="GitHub"><CodeBracketIcon className="h-5 w-5" /></a>
          </div>
        </div>
      </header>

      <aside className={`fixed inset-y-0 left-0 z-50 w-72 border-r border-slate-200 bg-mist px-5 pb-8 pt-5 transition-transform dark:border-slate-800 dark:bg-[#151b23] lg:top-16 lg:z-30 lg:w-64 lg:translate-x-0 lg:pt-7 ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="mb-7 flex items-center justify-between lg:hidden"><Logo /><button className="icon-button" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><XMarkIcon className="h-5 w-5" /></button></div>
        <nav className="space-y-7">
          {categories.map((category) => (
            <div key={category.id}>
              <p className="mb-2 px-2 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-500">{category.label[locale]}</p>
              <div className="space-y-0.5">
                {pages.filter((item) => item.category === category.id).map((item) => (
                  <button key={item.id} onClick={() => navigate(item.id)} className={`w-full border-l-2 px-3 py-2 text-left text-sm transition ${item.id === page.id ? "border-signal bg-white font-semibold text-ink shadow-sm dark:bg-slate-900 dark:text-white" : "border-transparent text-slate-600 hover:border-slate-300 hover:text-ink dark:text-slate-400 dark:hover:text-white"}`}>{item.title[locale]}</button>
                ))}
              </div>
            </div>
          ))}
        </nav>
      </aside>
      {mobileOpen && <button className="fixed inset-0 z-40 bg-ink/50 lg:hidden" onClick={() => setMobileOpen(false)} aria-label="Close navigation overlay" />}

      <main className="pt-16 lg:pl-64 xl:pr-60">
        <article className="mx-auto max-w-4xl px-6 py-12 sm:px-10 lg:py-16">
          <div className="mb-10 border-b border-slate-200 pb-9 dark:border-slate-800">
            <p className="mb-3 flex items-center gap-2 font-mono text-xs font-semibold uppercase text-leaf dark:text-emerald-400"><CommandLineIcon className="h-4 w-4" />{categories.find((category) => category.id === page.category)?.label[locale]}</p>
            <h1 className="text-4xl font-semibold text-ink dark:text-white sm:text-5xl">{page.heading?.[locale] ?? page.title[locale]}</h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600 dark:text-slate-400">{page.summary[locale]}</p>
          </div>
          <div className="space-y-12">
            {page.sections.map((section) => (
              <section key={section.id} id={section.id} className="scroll-mt-24">
                <h2 className="mb-4 text-2xl font-semibold text-ink dark:text-white">{section.title[locale]}</h2>
                <p className="leading-7">{section.body[locale]}</p>
                {section.interfaces && <InterfaceOptions interfaces={section.interfaces} locale={locale} />}
                {section.table && <FormatTable table={section.table} locale={locale} />}
                {section.code && <CodeBlock code={section.code} copyLabel={t.copy} copiedLabel={t.copied} />}
                {section.links && <ResourceLinks links={section.links} locale={locale} />}
                {section.note && <div className="mt-5 border-l-4 border-leaf bg-emerald-50 px-5 py-4 text-sm leading-6 text-emerald-950 dark:bg-emerald-950/30 dark:text-emerald-100">{section.note[locale]}</div>}
              </section>
            ))}
          </div>
          <nav className="mt-16 grid grid-cols-2 gap-4 border-t border-slate-200 pt-8 dark:border-slate-800">
            {pageIndex > 0 ? <PageLink direction="previous" label={t.previous} title={pages[pageIndex - 1].title[locale]} onClick={() => navigate(pages[pageIndex - 1].id)} /> : <span />}
            {pageIndex < pages.length - 1 && <PageLink direction="next" label={t.next} title={pages[pageIndex + 1].title[locale]} onClick={() => navigate(pages[pageIndex + 1].id)} />}
          </nav>
        </article>
      </main>

      <aside className="fixed bottom-0 right-0 top-16 hidden w-60 border-l border-slate-200 px-7 py-12 dark:border-slate-800 xl:block">
        <p className="mb-4 text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{t.onPage}</p>
        <nav className="space-y-3 border-l border-slate-200 dark:border-slate-700">
          {page.sections.map((section) => <a key={section.id} href={`#${page.id}/${section.id}`} onClick={(event) => { event.preventDefault(); document.getElementById(section.id)?.scrollIntoView({ behavior: "smooth" }); }} className="block border-l-2 border-transparent pl-4 text-sm text-slate-500 transition hover:border-signal hover:text-ink dark:hover:text-white">{section.title[locale]}</a>)}
        </nav>
      </aside>

      {searchOpen && <SearchDialog locale={locale} query={query} setQuery={setQuery} matches={matches} close={() => setSearchOpen(false)} navigate={navigate} />}
    </div>
  );
}

function InterfaceOptions({ interfaces, locale }: { interfaces: NonNullable<(typeof pages)[number]["sections"][number]["interfaces"]>; locale: Locale }) {
  return (
    <div className="mt-6 grid gap-4 md:grid-cols-3">
      {interfaces.map((item) => (
        <article key={item.title.en} className="flex min-w-0 flex-col border border-slate-200 bg-slate-50 p-5 dark:border-slate-700 dark:bg-slate-900/50">
          <p className="mb-2 font-mono text-[11px] font-semibold uppercase text-leaf dark:text-emerald-400">{item.label[locale]}</p>
          <h3 className="text-lg font-semibold text-ink dark:text-white">{item.title[locale]}</h3>
          <p className="mt-3 flex-1 text-sm leading-6 text-slate-600 dark:text-slate-400">{item.body[locale]}</p>
          <code className="mt-5 block overflow-hidden text-ellipsis whitespace-nowrap border-t border-slate-200 pt-3 font-mono text-[11px] text-slate-600 dark:border-slate-700 dark:text-slate-300" title={item.example}>{item.example}</code>
        </article>
      ))}
    </div>
  );
}

function FormatTable({ table, locale }: { table: NonNullable<(typeof pages)[number]["sections"][number]["table"]>; locale: Locale }) {
  const headers = table.headers[locale];
  const rows = table.rows[locale];
  const disabledLabel = locale === "en" ? "Same input and output format" : "輸入與輸出格式相同";

  return (
    <div className="mt-6">
      <div className="hidden border border-slate-200 dark:border-slate-700 md:block">
        <table className="w-full table-fixed border-collapse text-center text-sm">
          <caption className="sr-only">{table.caption[locale]}</caption>
          <thead className="bg-ink text-white dark:bg-slate-800">
            <tr>{headers.map((header, index) => <th key={header} scope="col" className={`border-r border-white/10 px-2 py-3 font-semibold last:border-r-0 ${index === 0 ? "w-28 text-left" : ""}`}>{header}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
            {rows.map((row) => (
              <tr key={row[0]} className="even:bg-slate-50 dark:even:bg-slate-900/50">
                {row.map((cell, index) => index === 0
                  ? <th key={cell} scope="row" className="border-r border-slate-200 px-3 py-3 text-left font-mono font-semibold text-ink dark:border-slate-700 dark:text-white">{cell}</th>
                  : <td key={`${row[0]}-${index}`} aria-disabled={!cell || undefined} title={!cell ? disabledLabel : undefined} className={`border-r border-slate-200 px-2 py-3 font-mono text-xs font-semibold last:border-r-0 dark:border-slate-700 ${!cell ? "bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500" : cell === "—" ? "text-slate-300 dark:text-slate-600" : "text-leaf dark:text-emerald-400"}`}>{cell || "×"}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="divide-y divide-slate-200 border border-slate-200 dark:divide-slate-700 dark:border-slate-700 md:hidden" aria-label={table.caption[locale]}>
        {rows.map((row) => (
          <section key={row[0]} className="p-4">
            <h3 className="mb-3 font-mono text-sm font-semibold text-ink dark:text-white">{row[0]}</h3>
            <dl className="grid grid-cols-2 gap-x-5 gap-y-2">
              {row.slice(1).map((cell, index) => (
                <div key={`${row[0]}-${headers[index + 1]}`} aria-disabled={!cell || undefined} title={!cell ? disabledLabel : undefined} className={`flex items-center justify-between gap-2 border-b pb-1.5 ${!cell ? "border-slate-200 bg-slate-100 px-1.5 text-slate-400 dark:border-slate-700 dark:bg-slate-800" : "border-slate-100 dark:border-slate-800"}`}>
                  <dt className="text-xs text-slate-500">{headers[index + 1]}</dt>
                  <dd className={`font-mono text-xs font-semibold ${!cell ? "text-slate-400 dark:text-slate-500" : cell === "—" ? "text-slate-300 dark:text-slate-600" : "text-leaf dark:text-emerald-400"}`}>{cell || "×"}</dd>
                </div>
              ))}
            </dl>
          </section>
        ))}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-slate-500 dark:text-slate-400">
        {table.legend[locale].map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>
  );
}

function CodeBlock({ code, copyLabel, copiedLabel }: { code: string; copyLabel: string; copiedLabel: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => { await navigator.clipboard.writeText(code); setCopied(true); setTimeout(() => setCopied(false), 1500); };
  return <div className="group relative mt-5 overflow-hidden border border-slate-800 bg-[#151b23]"><button onClick={copy} className="absolute right-2 top-2 flex items-center gap-1.5 border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs text-slate-300 opacity-0 transition group-hover:opacity-100 focus:opacity-100"><ClipboardDocumentIcon className="h-4 w-4" />{copied ? copiedLabel : copyLabel}</button><pre className="overflow-x-auto p-5 font-mono text-[13px] leading-6 text-slate-200"><code>{code}</code></pre></div>;
}

function ResourceLinks({ links, locale }: { links: NonNullable<(typeof pages)[number]["sections"][number]["links"]>; locale: Locale }) {
  return (
    <div className="mt-6 flex flex-wrap gap-3">
      {links.map((link) => (
        <a key={`${link.href}-${link.label.en}`} href={link.href} download={link.download || undefined} target={link.download ? undefined : "_blank"} rel={link.download ? undefined : "noreferrer"} className="inline-flex h-10 items-center gap-2 border border-slate-300 bg-white px-4 text-sm font-semibold text-ink transition hover:border-signal hover:text-leaf dark:border-slate-700 dark:bg-slate-900 dark:text-white dark:hover:border-emerald-500 dark:hover:text-emerald-400">
          {link.download ? <ArrowDownTrayIcon className="h-4 w-4" /> : <ArrowTopRightOnSquareIcon className="h-4 w-4" />}
          {link.label[locale]}
        </a>
      ))}
    </div>
  );
}

function PageLink({ direction, label, title, onClick }: { direction: "previous" | "next"; label: string; title: string; onClick: () => void }) {
  return <button onClick={onClick} className={`group flex min-w-0 items-center gap-3 border border-slate-200 p-4 text-left transition hover:border-slate-400 dark:border-slate-800 dark:hover:border-slate-600 ${direction === "next" ? "justify-end text-right" : ""}`}>{direction === "previous" && <ChevronLeftIcon className="h-5 w-5 shrink-0" />}<span className="min-w-0"><span className="block text-xs text-slate-500">{label}</span><span className="mt-1 block truncate text-sm font-semibold text-ink dark:text-white">{title}</span></span>{direction === "next" && <ChevronRightIcon className="h-5 w-5 shrink-0" />}</button>;
}

function SearchDialog({ locale, query, setQuery, matches, close, navigate }: { locale: Locale; query: string; setQuery: (value: string) => void; matches: typeof pages; close: () => void; navigate: (id: string) => void }) {
  const t = labels[locale];
  return <div className="fixed inset-0 z-[60] flex items-start justify-center bg-ink/60 px-4 pt-[12vh] backdrop-blur-sm" onMouseDown={close}><div className="w-full max-w-2xl overflow-hidden border border-slate-300 bg-white shadow-2xl dark:border-slate-700 dark:bg-[#151b23]" onMouseDown={(event) => event.stopPropagation()} role="dialog" aria-modal="true"><div className="flex items-center border-b border-slate-200 px-4 dark:border-slate-700"><MagnifyingGlassIcon className="h-5 w-5 text-slate-400" /><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t.search} className="h-14 flex-1 bg-transparent px-3 text-base text-ink outline-none placeholder:text-slate-400 dark:text-white" /><button className="icon-button" onClick={close} aria-label={t.close}><XMarkIcon className="h-5 w-5" /></button></div><div className="max-h-[55vh] overflow-y-auto p-2"><p className="px-3 py-2 text-xs font-bold uppercase tracking-[0.12em] text-slate-500">{t.results}</p>{matches.length ? matches.map((item) => <button key={item.id} onClick={() => { navigate(item.id); close(); }} className="block w-full border-l-2 border-transparent px-3 py-3 text-left hover:border-signal hover:bg-slate-50 dark:hover:bg-slate-900"><span className="block font-semibold text-ink dark:text-white">{item.title[locale]}</span><span className="mt-1 block truncate text-sm text-slate-500">{item.summary[locale]}</span></button>) : <p className="px-3 py-8 text-center text-sm text-slate-500">{t.noResults}</p>}</div></div></div>;
}

export default App;