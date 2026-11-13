"""Tests for search-engine metadata in the generated documentation site."""

from __future__ import annotations

import json
import re
from pathlib import Path
from xml.etree import ElementTree

import pytest

DOCS = Path(__file__).parents[2] / "docs"
PAGE_IDS = {
    "api",
    "architecture",
    "cli",
    "containers",
    "contributing",
    "deployment",
    "library",
    "overview",
    "roadmap",
    "security",
}


@pytest.mark.parametrize(
    ("locale", "page_id", "expected_heading"),
    [
        ("en", "cli", "Document conversion CLI reference"),
        ("zh-TW", "api", "DOCX 轉 PDF HTTP API"),
        ("zh-CN", "cli", "文档转换 CLI 命令参考"),
        ("zh-CN", "api", "DOCX 转 PDF HTTP API"),
        ("ja", "cli", "ドキュメント変換 CLI リファレンス"),
        ("ja", "api", "DOCX から PDF への HTTP API"),
    ],
)
def test_generated_page_contains_indexable_localized_content(
    locale: str, page_id: str, expected_heading: str
) -> None:
    content = (DOCS / locale / page_id / "index.html").read_text(encoding="utf-8")
    canonical = f"https://docs.gordonkit.com/{locale}/{page_id}/"

    assert f'<html lang="{locale}">' in content
    assert f'<link rel="canonical" href="{canonical}"' in content
    assert '<link rel="alternate" hreflang="en"' in content
    assert '<link rel="alternate" hreflang="zh-Hant-TW"' in content
    assert '<link rel="alternate" hreflang="zh-Hans-CN"' in content
    assert '<link rel="alternate" hreflang="ja"' in content
    assert '<link rel="alternate" hreflang="en-AU"' in content
    assert '<meta property="og:title"' in content
    assert '<script type="application/ld+json">' in content
    assert f"<h1>{expected_heading}</h1>" in content


PARENT_ORGANIZATION_ID = "https://gordonkit.com/#organization"
LD_JSON = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL)


@pytest.mark.parametrize(
    ("locale", "parent_url"),
    [
        ("en", "https://gordonkit.com/en/"),
        ("en-AU", "https://gordonkit.com/en-AU/"),
        ("zh-TW", "https://gordonkit.com/zh-TW/"),
        ("zh-CN", "https://gordonkit.com/zh-CN/"),
        ("ja", "https://gordonkit.com/ja/"),
    ],
)
def test_generated_page_names_gordonkit_as_publisher(locale: str, parent_url: str) -> None:
    content = (DOCS / locale / "overview" / "index.html").read_text(encoding="utf-8")
    match = LD_JSON.search(content)
    assert match is not None
    graph = json.loads(match.group(1))["@graph"]

    organization = next(node for node in graph if node["@type"] == "Organization")
    website = next(node for node in graph if node["@type"] == "WebSite")
    article = next(node for node in graph if node["@type"] == "TechArticle")
    assert organization["@id"] == PARENT_ORGANIZATION_ID
    assert website["@id"] == "https://docs.gordonkit.com/#website"
    assert website["publisher"] == {"@id": PARENT_ORGANIZATION_ID}
    assert article["publisher"] == {"@id": PARENT_ORGANIZATION_ID}
    assert article["isPartOf"] == {"@id": website["@id"]}
    # The publisher is backed by a link a crawler can follow without running the app.
    footer = content.split("<footer>", 1)[1]
    assert f'<a href="{parent_url}">gordonkit.com</a>' in footer


def test_unknown_address_has_a_noindex_not_found_page() -> None:
    content = (DOCS / "404.html").read_text(encoding="utf-8")

    assert '<meta name="robots" content="noindex" />' in content
    assert '<script type="module"' not in content
    for locale in ("en", "en-AU", "zh-TW", "zh-CN", "ja"):
        assert f'href="/{locale}/overview/"' in content


def test_locale_roots_redirect_to_the_overview() -> None:
    redirects = (DOCS / "_redirects").read_text(encoding="utf-8").splitlines()

    for locale in ("en", "en-AU", "zh-TW", "zh-CN", "ja"):
        assert f"/{locale} /{locale}/overview/ 301" in redirects
        assert f"/{locale}/ /{locale}/overview/ 301" in redirects


def test_llms_txt_lists_every_english_page_and_links_to_gordonkit() -> None:
    text = (DOCS / "llms.txt").read_text(encoding="utf-8")
    lines = text.splitlines()

    assert lines[0] == "# GordonKit Document Converter"
    assert lines[2].startswith("> Convert DOCX")
    assert "(https://gordonkit.com/llms.txt)" in text
    links = set(re.findall(r"\]\((https://docs\.gordonkit\.com/[^)]+)\)", text))
    english = {f"https://docs.gordonkit.com/en/{page_id}/" for page_id in PAGE_IDS}
    assert english <= links
    assert links - english == {
        f"https://docs.gordonkit.com/{locale}/overview/" for locale in ("en-AU", "zh-TW", "zh-CN", "ja")
    }
    for line in lines:
        if line.startswith("- "):
            assert re.match(r"^- \[[^\]]+\]\(https://[^)]+\): \S", line), line


def test_sitemap_contains_every_localized_documentation_page() -> None:
    sitemap = ElementTree.parse(DOCS / "sitemap.xml")
    namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = {element.text for element in sitemap.findall("sitemap:url/sitemap:loc", namespace)}
    expected = {
        f"https://docs.gordonkit.com/{locale}/{page_id}/"
        for locale in ("en", "en-AU", "zh-TW", "zh-CN", "ja")
        for page_id in PAGE_IDS
    }

    assert locations == expected
    robots = (DOCS / "robots.txt").read_text(encoding="utf-8")
    assert "Sitemap: https://docs.gordonkit.com/sitemap.xml" in robots
