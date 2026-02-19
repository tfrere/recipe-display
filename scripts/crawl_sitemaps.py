#!/usr/bin/env python3
"""
Crawl sitemaps from Tier S recipe sites and extract recipe URLs.

Usage:
    python scripts/crawl_sitemaps.py
    python scripts/crawl_sitemaps.py --site cookieandkate
    python scripts/crawl_sitemaps.py --output recipe_importer/urls_tier_s_all.json
"""

import argparse
import asyncio
import json
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import aiohttp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) RecipeDisplay/1.0"
}


@dataclass
class SiteConfig:
    """Configuration for crawling a recipe site."""
    name: str
    sitemap_urls: list[str]
    recipe_url_pattern: re.Pattern
    exclude_patterns: list[re.Pattern] = field(default_factory=list)


TIER_S_SITES: dict[str, SiteConfig] = {
    "cookieandkate": SiteConfig(
        name="Cookie and Kate",
        sitemap_urls=[
            "https://cookieandkate.com/post-sitemap.xml",
            "https://cookieandkate.com/sitemap_index.xml",
        ],
        recipe_url_pattern=re.compile(r"https://cookieandkate\.com/[a-z0-9-]+/?$"),
        exclude_patterns=[
            re.compile(r"/category/"),
            re.compile(r"/tag/"),
            re.compile(r"/page/"),
            re.compile(r"/about"),
            re.compile(r"/contact"),
            re.compile(r"/privacy"),
            re.compile(r"/disclosure"),
            re.compile(r"/advertise"),
            re.compile(r"/resources"),
            re.compile(r"/cookbook"),
            re.compile(r"/subscribe"),
            re.compile(r"/best-"),
            re.compile(r"/how-to-start"),
        ],
    ),
    "loveandlemons": SiteConfig(
        name="Love and Lemons",
        sitemap_urls=[
            "https://www.loveandlemons.com/post-sitemap.xml",
            "https://www.loveandlemons.com/sitemap_index.xml",
        ],
        recipe_url_pattern=re.compile(r"https://www\.loveandlemons\.com/[a-z0-9-]+/$"),
        exclude_patterns=[
            re.compile(r"/category/"),
            re.compile(r"/tag/"),
            re.compile(r"/page/"),
            re.compile(r"/best-"),
            re.compile(r"/how-to-"),
            re.compile(r"/what-to-"),
            re.compile(r"/meal-prep"),
        ],
    ),
    "smittenkitchen": SiteConfig(
        name="Smitten Kitchen",
        sitemap_urls=[
            "https://smittenkitchen.com/sitemap.xml",
            "https://smittenkitchen.com/sitemap-1.xml",
            "https://smittenkitchen.com/post-sitemap.xml",
        ],
        recipe_url_pattern=re.compile(r"https://smittenkitchen\.com/\d{4}/\d{2}/[a-z0-9-]+/$"),
        exclude_patterns=[
            re.compile(r"/category/"),
            re.compile(r"/tag/"),
        ],
    ),
    "101cookbooks": SiteConfig(
        name="101 Cookbooks",
        sitemap_urls=[
            "https://www.101cookbooks.com/post-sitemap.xml",
            "https://www.101cookbooks.com/sitemap_index.xml",
        ],
        recipe_url_pattern=re.compile(r"https://www\.101cookbooks\.com/[a-z0-9-]+/$"),
        exclude_patterns=[
            re.compile(r"/category/"),
            re.compile(r"/tag/"),
            re.compile(r"/page/"),
            re.compile(r"/best-"),
            re.compile(r"/archives"),
        ],
    ),
    "minimalistbaker": SiteConfig(
        name="Minimalist Baker",
        sitemap_urls=[
            "https://minimalistbaker.com/post-sitemap.xml",
            "https://minimalistbaker.com/sitemap_index.xml",
        ],
        recipe_url_pattern=re.compile(r"https://minimalistbaker\.com/[a-z0-9-]+/$"),
        exclude_patterns=[
            re.compile(r"/category/"),
            re.compile(r"/tag/"),
            re.compile(r"/page/"),
            re.compile(r"/best-"),
            re.compile(r"/how-to-"),
            re.compile(r"/what-is-"),
            re.compile(r"/meal-prep"),
        ],
    ),
}


async def fetch_sitemap(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    """Fetch a sitemap XML from a URL."""
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                text = await resp.text()
                logger.info(f"  Fetched {url} ({len(text)} chars)")
                return text
            logger.warning(f"  HTTP {resp.status} for {url}")
            return None
    except Exception as e:
        logger.warning(f"  Error fetching {url}: {e}")
        return None


def extract_urls_from_sitemap(xml_text: str) -> list[str]:
    """Extract all <loc> URLs from a sitemap XML."""
    urls = []
    try:
        root = ET.fromstring(xml_text)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for loc in root.findall(".//sm:loc", ns):
            if loc.text:
                urls.append(loc.text.strip())
        if not urls:
            for loc in root.iter():
                if loc.tag.endswith("}loc") or loc.tag == "loc":
                    if loc.text:
                        urls.append(loc.text.strip())
    except ET.ParseError as e:
        logger.error(f"  XML parse error: {e}")
    return urls


def is_sub_sitemap(url: str) -> bool:
    """Check if a URL points to another sitemap."""
    return url.endswith(".xml") or "sitemap" in url.lower()


async def crawl_site(session: aiohttp.ClientSession, config: SiteConfig) -> list[str]:
    """Crawl all sitemaps for a site and return recipe URLs."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Crawling: {config.name}")
    logger.info(f"{'='*60}")

    all_urls: set[str] = set()
    sitemaps_to_fetch = list(config.sitemap_urls)
    fetched_sitemaps: set[str] = set()

    while sitemaps_to_fetch:
        url = sitemaps_to_fetch.pop(0)
        if url in fetched_sitemaps:
            continue
        fetched_sitemaps.add(url)

        xml_text = await fetch_sitemap(session, url)
        if not xml_text:
            continue

        urls = extract_urls_from_sitemap(xml_text)
        logger.info(f"  Found {len(urls)} URLs in {url}")

        for u in urls:
            if is_sub_sitemap(u) and u not in fetched_sitemaps:
                sitemaps_to_fetch.append(u)
            else:
                all_urls.add(u)

    recipe_urls = []
    for u in sorted(all_urls):
        if not config.recipe_url_pattern.match(u):
            continue
        if any(p.search(u) for p in config.exclude_patterns):
            continue
        recipe_urls.append(u)

    logger.info(f"\n  Total raw URLs: {len(all_urls)}")
    logger.info(f"  Recipe URLs (filtered): {len(recipe_urls)}")
    return recipe_urls


async def main(sites: Optional[list[str]] = None, output: Optional[str] = None):
    """Main entry point."""
    configs = TIER_S_SITES
    if sites:
        configs = {k: v for k, v in TIER_S_SITES.items() if k in sites}
        if not configs:
            logger.error(f"No matching sites. Available: {list(TIER_S_SITES.keys())}")
            return

    all_recipe_urls: dict[str, list[str]] = {}

    async with aiohttp.ClientSession() as session:
        for key, config in configs.items():
            urls = await crawl_site(session, config)
            all_recipe_urls[key] = urls

    total = sum(len(v) for v in all_recipe_urls.values())
    logger.info(f"\n{'='*60}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*60}")
    for key, urls in all_recipe_urls.items():
        logger.info(f"  {TIER_S_SITES[key].name}: {len(urls)} recipes")
    logger.info(f"  TOTAL: {total} recipes")

    script_dir = Path(__file__).resolve().parent.parent
    output_dir = script_dir / "recipe_importer"

    # Save per-site JSON files
    for key, urls in all_recipe_urls.items():
        filepath = output_dir / f"urls_{key}.json"
        filepath.write_text(json.dumps(urls, indent=2, ensure_ascii=False))
        logger.info(f"  Saved {filepath} ({len(urls)} URLs)")

    # Save combined JSON
    combined = []
    for urls in all_recipe_urls.values():
        combined.extend(urls)

    combined_path = Path(output) if output else output_dir / "urls_tier_s_all.json"
    combined_path.write_text(json.dumps(combined, indent=2, ensure_ascii=False))
    logger.info(f"  Saved {combined_path} ({len(combined)} URLs)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl sitemaps from Tier S recipe sites")
    parser.add_argument("--site", nargs="+", help="Specific sites to crawl")
    parser.add_argument("--output", help="Output file path for combined URLs")
    args = parser.parse_args()

    asyncio.run(main(sites=args.site, output=args.output))
