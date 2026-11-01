#!/usr/bin/env node
// Tells IndexNow (Bing, Yandex, Naver, Seznam) which pages changed in a deploy.
//
// The same file is copied into every GordonKit repo (gordonkit-site .plans/14). It runs twice in a
// deploy workflow:
//
//   plan    before the deploy. Fingerprints every page in the sitemap, compares the result with the
//           fingerprints the live site published last time (/indexnow-state.json), writes the new
//           fingerprints into dist so they ship with this deploy, and saves the changed URLs.
//   submit  after the deploy. Sends the saved URLs to IndexNow. A failure here is a warning, never a
//           failed deploy: the pages are already live, and the next deploy compares against them.
//
// Only changed, added and removed pages are sent. A fingerprint covers the title, the meta
// description and the visible body text, so a rebuilt asset hash does not resubmit the whole site.
// The first deploy finds no live state and sends every page, which is how the backlog gets in.
//
// Usage:
//   node indexnow.mjs plan --host <host> --dist <dir> --key <key> --out <file> [--root-file <name>]
//   node indexnow.mjs submit --plan <file>

import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { parseArgs } from "node:util";

const STATE_FILE = "indexnow-state.json";
const ENDPOINT = "https://api.indexnow.org/indexnow";
// IndexNow accepts up to 10,000 URLs in one request.
const BATCH_SIZE = 10_000;

const { positionals, values } = parseArgs({
  allowPositionals: true,
  options: {
    host: { type: "string" },
    dist: { type: "string" },
    key: { type: "string" },
    out: { type: "string" },
    plan: { type: "string" },
    "root-file": { type: "string" },
  },
});

function fail(message) {
  console.error(`indexnow: ${message}`);
  process.exit(1);
}

function warn(message) {
  // GitHub Actions shows this as an annotation on the run without failing it.
  console.log(`::warning title=IndexNow::${message}`);
}

function required(name) {
  const value = values[name];
  if (!value) fail(`--${name} is required`);
  return value;
}

/** The dist file a sitemap URL is served from, or undefined when none exists. */
function fileFor(dist, url, rootFile) {
  const path = decodeURIComponent(new URL(url).pathname);
  if (path === "/" && rootFile) return join(dist, rootFile);
  const relative = path.replace(/^\//, "");
  const candidates = path.endsWith("/")
    ? [`${relative}index.html`]
    : [`${relative}.html`, `${relative}/index.html`];
  return candidates.map((candidate) => join(dist, candidate)).find((file) => existsSync(file));
}

function fingerprint(html) {
  const title = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1] ?? "";
  const descriptionTag = html.match(/<meta\b[^>]*\bname=["']description["'][^>]*>/i)?.[0] ?? "";
  const description = descriptionTag.match(/\bcontent=["']([^"']*)["']/i)?.[1] ?? "";
  const body = (html.match(/<body[^>]*>([\s\S]*)<\/body>/i)?.[1] ?? html)
    .replace(/<(script|style|template)\b[\s\S]*?<\/\1>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return createHash("sha256").update(`${title}\n${description}\n${body}`).digest("hex").slice(0, 16);
}

async function liveState(host) {
  // The query string keeps an edge cache from answering with an older copy.
  const url = `https://${host}/${STATE_FILE}?t=${Date.now()}`;
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (response.status === 404) {
      console.log(`indexnow: no ${STATE_FILE} on ${host} yet, so every page counts as new`);
      return {};
    }
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const state = await response.json();
    return state && typeof state.pages === "object" ? state.pages : {};
  } catch (error) {
    warn(`could not read ${url} (${error.message}); every page will be sent`);
    return {};
  }
}

async function plan() {
  const host = required("host");
  const dist = required("dist");
  const key = required("key");
  const out = required("out");
  const rootFile = values["root-file"];

  // IndexNow fetches https://<host>/<key>.txt to prove the request comes from the site owner.
  const keyFile = join(dist, `${key}.txt`);
  if (!existsSync(keyFile) || readFileSync(keyFile, "utf8").trim() !== key) {
    fail(`${keyFile} must exist and contain the key, or IndexNow will reject every request`);
  }

  const sitemap = readFileSync(join(dist, "sitemap.xml"), "utf8");
  const urls = [...sitemap.matchAll(/<loc>\s*([^<\s]+)\s*<\/loc>/g)].map(([, url]) => url);
  if (urls.length === 0) fail(`${join(dist, "sitemap.xml")} lists no URLs`);

  const pages = {};
  for (const url of urls) {
    if (new URL(url).host !== host) fail(`${url} is not on ${host}; IndexNow takes one host per request`);
    const file = fileFor(dist, url, rootFile);
    if (!file) fail(`${url} has no matching file in ${dist}`);
    pages[url] = fingerprint(readFileSync(file, "utf8"));
  }

  const previous = await liveState(host);
  const changed = urls.filter((url) => previous[url] !== pages[url]);
  // A page that left the sitemap is reported too, so the engine rechecks it and drops it.
  const removed = Object.keys(previous).filter((url) => !(url in pages));

  writeFileSync(join(dist, STATE_FILE), `${JSON.stringify({ pages }, null, 2)}\n`);
  writeFileSync(out, `${JSON.stringify({ host, key, urls: [...changed, ...removed] }, null, 2)}\n`);
  console.log(
    `indexnow: ${urls.length} pages, ${changed.length} new or changed, ${removed.length} removed; plan saved to ${out}`,
  );
}

async function submit() {
  const { host, key, urls } = JSON.parse(readFileSync(required("plan"), "utf8"));
  if (urls.length === 0) {
    console.log(`indexnow: nothing changed on ${host}, nothing to send`);
    return;
  }

  for (let start = 0; start < urls.length; start += BATCH_SIZE) {
    const urlList = urls.slice(start, start + BATCH_SIZE);
    try {
      const response = await fetch(ENDPOINT, {
        method: "POST",
        headers: { "content-type": "application/json; charset=utf-8" },
        body: JSON.stringify({ host, key, keyLocation: `https://${host}/${key}.txt`, urlList }),
      });
      // 200 means accepted; 202 means accepted while the key is still being verified.
      if (response.status === 200 || response.status === 202) {
        console.log(`indexnow: sent ${urlList.length} URLs for ${host} (HTTP ${response.status})`);
      } else {
        const body = (await response.text()).slice(0, 300);
        warn(`HTTP ${response.status} for ${urlList.length} URLs on ${host}: ${body}`);
      }
    } catch (error) {
      warn(`request for ${host} failed: ${error.message}`);
    }
  }
}

const command = positionals[0];
if (command === "plan") await plan();
else if (command === "submit") await submit();
else fail("usage: indexnow.mjs plan|submit [options]");
