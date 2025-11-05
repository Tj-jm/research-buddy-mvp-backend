import asyncio, os, re
from urllib.parse import urljoin, urlparse
import httpx
from selectolax.parser import HTMLParser
from tenacity import retry, wait_exponential, stop_after_attempt
from loguru import logger

CONCURRENCY = int(os.getenv("SCRAPER_CONCURRENCY", "8"))
TIMEOUT = int(os.getenv("SCRAPER_TIMEOUT", "30"))

EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

HEADERS = {
    "User-Agent": "ResearchBuddy-FacultyScraper/1.0 (+https://turjo-jaman.com)"
}

def _extract_links(html: str, base_url: str) -> list[str]:
    dom = HTMLParser(html)
    hrefs = []
    for a in dom.css("a"):
        href = a.attributes.get("href")
        if not href:
            continue
        full = urljoin(base_url, href)
        # heuristics to keep profile-ish links
        if any(k in full.lower() for k in ["people", "faculty", "profile", "person", "directory", "researchers"]):
            hrefs.append(full)
    # dedupe
    return list(dict.fromkeys(hrefs))

@retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3))
async def fetch_text(client: httpx.AsyncClient, url: str) -> str:
    r = await client.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text

async def directory_to_profiles(directory_url: str, max_profiles: int | None = None) -> list[str]:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        html = await fetch_text(client, directory_url)
        links = _extract_links(html, directory_url)
        # If the directory page lists profiles directly, keep them; else we may need to crawl subpages
        # Keep it simple initially:
        profiles = [u for u in links if not u.rstrip("/").endswith(("faculty","people","directory","search"))]
        if not profiles:
            profiles = links  # fallback: try all
        if max_profiles:
            profiles = profiles[:max_profiles]
        logger.info(f"Collected {len(profiles)} candidate profiles")
        return profiles

def _html_text(html: str) -> str:
    dom = HTMLParser(html)
    # Remove scripts/style
    for tag in dom.css("script, style, noscript"):
        tag.decompose()
    # Join text nodes
    return "\n".join([t.text(strip=True) for t in dom.root.iter_text() if t.text(strip=True)])

async def scrape_profiles(profile_urls: list[str]) -> list[dict]:
    sem = asyncio.Semaphore(CONCURRENCY)
    results = []

    async def worker(url: str):
        async with sem:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                try:
                    html = await fetch_text(client, url)
                    text = _html_text(html)
                    # quick email discover if page shows it directly (LLM will still decide)
                    maybe_email = EMAIL_REGEX.search(text)
                    results.append({"url": url, "text": text, "email_hint": maybe_email.group(0) if maybe_email else None})
                except Exception as e:
                    logger.warning(f"Failed {url}: {e}")

    await asyncio.gather(*[worker(u) for u in profile_urls])
    return results

def infer_university_from_url(url: str) -> str | None:
    netloc = urlparse(url).netloc
    # crude: "utexas.edu" -> "The University of Texas at Austin"
    # keep simple; LLM will polish
    parts = netloc.split(".")
    if len(parts) >= 2:
        return parts[-2].upper() + "." + parts[-1].upper()
    return None
