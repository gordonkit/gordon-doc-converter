"""Tests for search-engine metadata in the generated documentation site."""

from __future__ import annotations

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
    assert '<link rel="alternate" hreflang="ja"' in content
    assert '<meta property="og:title"' in content
    assert '<script type="application/ld+json">' in content
    assert f"<h1>{expected_heading}</h1>" in content


def test_sitemap_contains_every_localized_documentation_page() -> None:
    sitemap = ElementTree.parse(DOCS / "sitemap.xml")
    namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = {element.text for element in sitemap.findall("sitemap:url/sitemap:loc", namespace)}
    expected = {
        f"https://docs.gordonkit.com/{locale}/{page_id}/"
        for locale in ("en", "zh-TW", "ja")
        for page_id in PAGE_IDS
    }

    assert locations == expected
    robots = (DOCS / "robots.txt").read_text(encoding="utf-8")
    assert "Sitemap: https://docs.gordonkit.com/sitemap.xml" in robots
