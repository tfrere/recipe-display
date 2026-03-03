#!/usr/bin/env python3
"""
LLM-powered recipe URL discovery.

Give it any root URL and it automatically finds all recipe URLs on that site.

Strategy:
  1. Try to find the site's XML sitemap (robots.txt → sitemap_index → sub-sitemaps)
  2. If sitemap found: extract all URLs, send them to LLM in batches for classification
  3. If no sitemap: fall back to HTML crawling with pagination following

Supports authenticated sites via the same auth_presets.json as the batch importer.

Usage:
    # Auto-discover (tries sitemap first, then HTML crawl)
    python scripts/discover_recipe_urls.py https://books.ottolenghi.co.uk/

    # Force HTML crawl only (skip sitemap)
    python scripts/discover_recipe_urls.py https://example.com/recipes --no-sitemap --depth 3

    # Custom output
    python scripts/discover_recipe_urls.py https://smittenkitchen.com/ -o urls.json

    # Then import
    cd ../recipe_importer && poetry run recipe-importer url -f urls.json

Requirements (all available in the server venv):
    aiohttp beautifulsoup4 openai instructor pydantic python-dotenv

Env vars:
    OPENROUTER_API_KEY  or  DEEPSEEK_API_KEY   (same as the rest of the project)
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin, urlparse

import aiohttp
import instructor
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

_env_path = Path(__file__).resolve().parent.parent / "server" / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) RecipeDisplay/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml",
}

PROVIDERS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "deepseek/deepseek-v3.2",
        "env_key": "OPENROUTER_API_KEY",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
    },
}

# LLM processes URLs in batches of this size (keep small for token limits)
BATCH_SIZE = 200

# URL path segments that strongly indicate a recipe page
RECIPE_PATH_SIGNALS = ("/recipe/", "/recette/", "/recipes/", "/recettes/")

# URL path segments that strongly indicate NOT a recipe page
NON_RECIPE_PATH_SIGNALS = (
    "/category/", "/tag/", "/author/", "/page/", "/wp-content/",
    "/wp-admin/", "/feed/", "/comment", "/search", "/cart", "/shop/",
    "/product/", "/privacy", "/terms", "/contact", "/about/",
    "/login", "/register", "/account", "/articles/", "/article/",
    "/type/", "/favourites/",
)


# ── Structured output models ────────────────────────────────────────


class ClassifiedUrls(BaseModel):
    """LLM-classified URLs."""

    recipe_urls: list[str] = Field(
        description="URLs that point to individual recipe pages"
    )
    reasoning: str = Field(
        description="Brief explanation of how you identified recipe vs non-recipe URLs"
    )


class PageClassification(BaseModel):
    """LLM-classified URLs from an HTML page (includes navigation)."""

    recipe_urls: list[str] = Field(
        description="URLs that point to individual recipe pages"
    )
    pagination_urls: list[str] = Field(
        default_factory=list,
        description="URLs for next pages, older posts, page/2, etc. — pages listing MORE recipes",
    )
    section_urls: list[str] = Field(
        default_factory=list,
        description="Category/section/book pages that likely contain recipe listings",
    )
    reasoning: str = Field(
        description="Brief explanation of the classification"
    )


# ── LLM client ──────────────────────────────────────────────────────


def _get_client() -> tuple[instructor.AsyncInstructor, str]:
    """Build an Instructor-patched AsyncOpenAI client from env vars."""
    for provider_name in ("openrouter", "deepseek"):
        cfg = PROVIDERS[provider_name]
        api_key = os.getenv(cfg["env_key"])
        if api_key:
            raw = AsyncOpenAI(base_url=cfg["base_url"], api_key=api_key)
            client = instructor.from_openai(raw)
            logger.info("Using %s (%s)", provider_name, cfg["model"])
            return client, cfg["model"]

    print(
        "Error: set OPENROUTER_API_KEY or DEEPSEEK_API_KEY "
        "(same keys as the recipe-display server).",
        file=sys.stderr,
    )
    sys.exit(1)


# ── Auth presets ─────────────────────────────────────────────────────


def load_auth_presets(auth_path: str | None) -> dict:
    """Load auth_presets.json — tries the given path, then the default location."""
    candidates = []
    if auth_path:
        candidates.append(Path(auth_path))
    default = Path(__file__).resolve().parent.parent / "recipe_importer" / "auth_presets.json"
    candidates.append(default)

    for path in candidates:
        if path.exists():
            with open(path) as f:
                presets = json.load(f)
            logger.info("Loaded auth presets from %s (%d domains)", path, len(presets))
            return presets

    logger.debug("No auth_presets.json found — all requests will be unauthenticated")
    return {}


def get_cookies_for_url(url: str, auth_presets: dict) -> dict[str, str]:
    """Match a URL against auth presets and return cookies to inject."""
    if not auth_presets:
        return {}
    domain = urlparse(url).netloc
    for preset_domain, preset_config in auth_presets.items():
        if preset_domain in domain and preset_config.get("type") == "cookie":
            return preset_config.get("values", {})
    return {}


# ── HTTP helpers ─────────────────────────────────────────────────────


async def fetch(
    session: aiohttp.ClientSession,
    url: str,
    auth_presets: dict | None = None,
) -> str | None:
    """Fetch a URL with optional auth cookies."""
    cookies = get_cookies_for_url(url, auth_presets or {})
    try:
        async with session.get(
            url,
            headers=HEADERS,
            cookies=cookies,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status == 200:
                return await resp.text()
            logger.warning("HTTP %d for %s", resp.status, url)
            return None
    except Exception as e:
        logger.warning("Error fetching %s: %s", url, e)
        return None


# ── Sitemap discovery & parsing ──────────────────────────────────────


def _extract_urls_from_xml(xml_text: str) -> list[str]:
    """Extract all <loc> URLs from a sitemap XML."""
    urls = []
    try:
        root = ET.fromstring(xml_text)
        for elem in root.iter():
            if elem.tag.endswith("}loc") or elem.tag == "loc":
                if elem.text:
                    urls.append(elem.text.strip())
    except ET.ParseError:
        pass
    return urls


def _is_sitemap_url(url: str) -> bool:
    return url.endswith(".xml") or "sitemap" in url.lower()


async def discover_sitemaps(
    session: aiohttp.ClientSession,
    root_url: str,
    auth_presets: dict | None = None,
) -> list[str]:
    """Try to find and parse all sitemaps for a site. Returns all discovered URLs."""
    parsed = urlparse(root_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    # Candidate sitemap locations
    candidates = [
        f"{base}/robots.txt",
        f"{base}/sitemap.xml",
        f"{base}/sitemap_index.xml",
        f"{base}/wp-sitemap.xml",
    ]

    sitemap_urls_to_fetch: list[str] = []
    fetched_sitemaps: set[str] = set()

    # Step 1: Check robots.txt for sitemap declarations
    robots_text = await fetch(session, candidates[0], auth_presets)
    if robots_text:
        for line in robots_text.splitlines():
            if line.lower().startswith("sitemap:"):
                sm_url = line.split(":", 1)[1].strip()
                if sm_url not in sitemap_urls_to_fetch:
                    sitemap_urls_to_fetch.append(sm_url)

    # Step 2: Try standard sitemap locations if robots.txt didn't help
    if not sitemap_urls_to_fetch:
        for url in candidates[1:]:
            sitemap_urls_to_fetch.append(url)

    # Step 3: Recursively fetch all sitemaps (index → sub-sitemaps)
    all_urls: list[str] = []

    while sitemap_urls_to_fetch:
        sm_url = sitemap_urls_to_fetch.pop(0)
        if sm_url in fetched_sitemaps:
            continue
        fetched_sitemaps.add(sm_url)

        xml_text = await fetch(session, sm_url, auth_presets)
        if not xml_text:
            continue

        urls = _extract_urls_from_xml(xml_text)
        if not urls:
            continue

        logger.info("  Sitemap %s → %d URLs", sm_url, len(urls))

        for u in urls:
            if _is_sitemap_url(u) and u not in fetched_sitemaps:
                sitemap_urls_to_fetch.append(u)
            else:
                all_urls.append(u)

    return all_urls


# ── LLM classification ──────────────────────────────────────────────


SITEMAP_SYSTEM_PROMPT = """\
You are a recipe URL classifier. Given a list of URLs from a website's sitemap,
identify which ones are individual recipe pages.

Rules:
- Recipe URLs lead to a SINGLE recipe (with ingredients, steps, etc.)
- Exclude: category indexes, tag pages, about pages, articles, blog posts that aren't recipes,
  author pages, search pages, policy pages, contact pages, shop/product pages
- When a URL contains "/recipe/" or "/recette/" in the path, it's very likely a recipe
- When unsure, include it — false positives are OK, the importer handles duplicates
- Return ONLY URLs from the provided list — do not invent URLs"""

HTML_SYSTEM_PROMPT = """\
You are a recipe URL classifier. Given a list of URLs extracted from a web page,
classify them into three categories.

Rules:
- recipe_urls: individual recipe pages (with ingredients, steps, etc.)
- pagination_urls: "next page", "older posts", "page/2" — pages listing MORE recipes
  from the SAME section. Do NOT include category/section links here.
- section_urls: category pages, book pages, cuisine types, meal types — pages that
  contain DIFFERENT recipe listings worth exploring
- Ignore: social media, ads, privacy, author bios, comments, print/share links
- When unsure, lean towards including as recipe (false positives are fine)
- Return ONLY URLs from the provided list — do not invent URLs"""


async def classify_sitemap_urls(
    client: instructor.AsyncInstructor,
    model: str,
    site_url: str,
    urls: list[str],
) -> list[str]:
    """Classify sitemap URLs in batches. Returns recipe URLs."""
    all_recipe_urls: list[str] = []

    for i in range(0, len(urls), BATCH_SIZE):
        batch = urls[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(urls) + BATCH_SIZE - 1) // BATCH_SIZE

        logger.info(
            "  Classifying batch %d/%d (%d URLs)…",
            batch_num,
            total_batches,
            len(batch),
        )

        urls_text = "\n".join(batch)

        try:
            result = await client.chat.completions.create(
                model=model,
                response_model=ClassifiedUrls,
                messages=[
                    {"role": "system", "content": SITEMAP_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Website: {site_url}\n\n"
                            f"Here are {len(batch)} URLs from the sitemap:\n\n"
                            f"{urls_text}\n\n"
                            f"Which are individual recipe pages?"
                        ),
                    },
                ],
                temperature=0,
                max_tokens=16384,
            )
            all_recipe_urls.extend(result.recipe_urls)
            logger.info(
                "    → %d recipes found. Reasoning: %s",
                len(result.recipe_urls),
                result.reasoning,
            )
        except Exception as e:
            logger.error("    LLM classification failed: %s", e)

    return all_recipe_urls


async def classify_page_urls(
    client: instructor.AsyncInstructor,
    model: str,
    page_url: str,
    page_context: str,
    links: list[str],
) -> PageClassification:
    """Classify links from an HTML page."""
    domain = urlparse(page_url).netloc
    same_domain = [l for l in links if urlparse(l).netloc == domain]
    other = [l for l in links if urlparse(l).netloc != domain]
    truncated = same_domain[:500] + other[:100]

    urls_text = "\n".join(truncated)

    return await client.chat.completions.create(
        model=model,
        response_model=PageClassification,
        messages=[
            {"role": "system", "content": HTML_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Source page: {page_url}\n"
                    f"{page_context}\n\n"
                    f"Here are {len(truncated)} links found on this page:\n\n"
                    f"{urls_text}\n\n"
                    f"Classify them."
                ),
            },
        ],
        temperature=0,
        max_tokens=16384,
    )


# ── HTML helpers ─────────────────────────────────────────────────────


def extract_links(html: str, base_url: str) -> list[str]:
    """Extract all unique absolute href links from an HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    links: list[str] = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        absolute = urljoin(base_url, href)
        absolute = absolute.split("#")[0]
        if absolute not in seen:
            seen.add(absolute)
            links.append(absolute)

    return links


def get_page_context(html: str) -> str:
    """Extract title and meta description for LLM context."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    meta = soup.find("meta", attrs={"name": "description"})
    desc = meta["content"].strip() if meta and meta.get("content") else ""
    return f"Page title: {title}\nDescription: {desc}"


# ── Discovery strategies ─────────────────────────────────────────────


def _pre_classify_urls(urls: list[str]) -> tuple[list[str], list[str]]:
    """Fast heuristic pre-filter. Returns (likely_recipes, ambiguous).

    URLs with strong recipe signals go straight to output.
    URLs with strong non-recipe signals are discarded.
    Everything else goes to the LLM for classification.
    """
    likely_recipes: list[str] = []
    ambiguous: list[str] = []

    for url in urls:
        path = urlparse(url).path.lower()

        if any(sig in path for sig in RECIPE_PATH_SIGNALS):
            likely_recipes.append(url)
        elif any(sig in path for sig in NON_RECIPE_PATH_SIGNALS):
            continue  # discard
        elif path.endswith((".xml", ".jpg", ".png", ".gif", ".pdf", ".css", ".js")):
            continue  # discard static assets
        else:
            ambiguous.append(url)

    return likely_recipes, ambiguous


async def discover_via_sitemap(
    root_url: str,
    auth_presets: dict | None = None,
) -> list[str] | None:
    """Try sitemap-based discovery. Returns recipe URLs or None if no sitemap found.

    Uses a 2-phase approach:
      1. Heuristic pre-filter catches obvious recipe/non-recipe URLs
      2. LLM only classifies the ambiguous remainder
    """
    async with aiohttp.ClientSession() as session:
        logger.info("Looking for sitemaps…")
        all_urls = await discover_sitemaps(session, root_url, auth_presets)

        if not all_urls:
            logger.info("No sitemap found — will fall back to HTML crawl.")
            return None

        unique_urls = list(dict.fromkeys(all_urls))
        logger.info("Found %d URLs in sitemaps (%d unique).", len(all_urls), len(unique_urls))

        # Phase 1: heuristic pre-filter
        obvious_recipes, ambiguous = _pre_classify_urls(unique_urls)
        logger.info(
            "Pre-filter: %d obvious recipes, %d discarded, %d ambiguous → LLM",
            len(obvious_recipes),
            len(unique_urls) - len(obvious_recipes) - len(ambiguous),
            len(ambiguous),
        )

        # Phase 2: LLM classifies only ambiguous URLs
        llm_recipes: list[str] = []
        if ambiguous:
            client, model = _get_client()
            llm_recipes = await classify_sitemap_urls(client, model, root_url, ambiguous)
            logger.info("LLM found %d additional recipes in ambiguous URLs.", len(llm_recipes))

        combined = sorted(set(obvious_recipes + llm_recipes))
        return combined


async def discover_via_crawl(
    root_url: str,
    max_depth: int = 2,
    max_pages: int = 50,
    auth_presets: dict | None = None,
) -> list[str]:
    """HTML crawl-based discovery with section + pagination following."""

    client, model = _get_client()
    all_recipe_urls: set[str] = set()
    visited: set[str] = set()

    # Queue: (url, depth, is_pagination)
    # Pagination doesn't cost depth, sections do
    queue: list[tuple[str, int, bool]] = [(root_url, 0, False)]

    async with aiohttp.ClientSession() as session:
        pages_fetched = 0

        while queue and pages_fetched < max_pages:
            url, depth, is_pagination = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            label = "pagination" if is_pagination else f"depth {depth}/{max_depth}"
            logger.info("[%s] Fetching %s (%d pages so far)", label, url, pages_fetched)

            html = await fetch(session, url, auth_presets)
            if not html:
                continue
            pages_fetched += 1

            links = extract_links(html, url)
            page_ctx = get_page_context(html)

            logger.info("  Found %d links, classifying with LLM…", len(links))

            try:
                result = await classify_page_urls(client, model, url, page_ctx, links)
            except Exception as e:
                logger.error("  LLM classification failed: %s", e)
                continue

            new_recipes = set(result.recipe_urls) - all_recipe_urls
            all_recipe_urls.update(result.recipe_urls)

            logger.info(
                "  → %d recipes (+%d new), %d pagination, %d sections",
                len(result.recipe_urls),
                len(new_recipes),
                len(result.pagination_urls),
                len(result.section_urls),
            )
            logger.info("  Reasoning: %s", result.reasoning)

            # Pagination: follow without depth cost
            for purl in result.pagination_urls:
                if purl not in visited:
                    queue.append((purl, depth, True))

            # Sections: follow with depth cost
            if depth < max_depth:
                for surl in result.section_urls:
                    if surl not in visited:
                        queue.append((surl, depth + 1, False))

    return sorted(all_recipe_urls)


# ── CLI ──────────────────────────────────────────────────────────────


async def main():
    parser = argparse.ArgumentParser(
        description="Discover recipe URLs from any website using an LLM agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://books.ottolenghi.co.uk/
  %(prog)s https://smittenkitchen.com/
  %(prog)s https://cookieandkate.com/ --no-sitemap --depth 3
  %(prog)s https://example.com/recipes -o urls.json
        """,
    )
    parser.add_argument("url", help="Root URL of the recipe site")
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file (default: recipe_importer/urls_discovered.json)",
    )
    parser.add_argument(
        "--auth",
        help="Path to auth_presets.json (default: recipe_importer/auth_presets.json)",
    )
    parser.add_argument(
        "--no-sitemap",
        action="store_true",
        help="Skip sitemap discovery, go straight to HTML crawl",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=2,
        help="Max section depth for HTML crawl (default: 2)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Max pages to fetch in HTML crawl mode (default: 50)",
    )

    args = parser.parse_args()
    auth_presets = load_auth_presets(args.auth)
    recipe_urls: list[str] = []

    # Strategy 1: Sitemap
    if not args.no_sitemap:
        result = await discover_via_sitemap(args.url, auth_presets)
        if result is not None:
            recipe_urls = result

    # Strategy 2: HTML crawl (fallback or explicit)
    if not recipe_urls:
        logger.info("Starting HTML crawl discovery…")
        recipe_urls = await discover_via_crawl(
            args.url,
            max_depth=args.depth,
            max_pages=args.max_pages,
            auth_presets=auth_presets,
        )

    if not recipe_urls:
        logger.warning("No recipe URLs found.")
        sys.exit(0)

    # Output
    script_dir = Path(__file__).resolve().parent.parent
    output_path = (
        Path(args.output)
        if args.output
        else script_dir / "recipe_importer" / "urls_discovered.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(recipe_urls, indent=2, ensure_ascii=False))

    logger.info("Discovered %d recipe URLs → %s", len(recipe_urls), output_path)
    print(str(output_path))


if __name__ == "__main__":
    asyncio.run(main())
