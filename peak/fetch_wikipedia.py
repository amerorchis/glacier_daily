"""
Fetch Wikipedia article text for all peaks in Glacier National Park.

This script reads peaks from PeaksCSV.csv and fetches the corresponding
Wikipedia article for each peak, saving results to peaks_wikipedia.json.
"""

import csv
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests_cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Constants
SCRIPT_DIR = Path(__file__).parent
CSV_PATH = SCRIPT_DIR / "PeaksCSV.csv"
OUTPUT_PATH = SCRIPT_DIR / "peaks_wikipedia.json"
PARTIAL_PATH = SCRIPT_DIR / "peaks_wikipedia_partial.json"
CACHE_DIR = SCRIPT_DIR / ".wiki_cache"

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
REQUEST_DELAY = 0.5  # seconds between requests


def _setup_session() -> requests_cache.CachedSession:
    """Set up a cached session with retry capabilities."""
    cache_session = requests_cache.CachedSession(
        str(CACHE_DIR),
        expire_after=86400,  # 24 hour cache
    )
    retry_strategy = Retry(total=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry_strategy)
    cache_session.mount("https://", adapter)
    cache_session.headers.update(
        {"User-Agent": "GlacierDailyBot/1.0 (https://glacier.org; educational project)"}
    )
    return cache_session


def load_peaks() -> list[dict]:
    """Load peaks from CSV file."""
    peaks = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["name"]:  # Skip empty rows
                peaks.append(
                    {
                        "name": row["name"].strip(),
                        "lat": float(row["lat"]),
                        "lon": float(row["lon"]),
                        "elevation": int(row["elevation"]),
                    }
                )
    return peaks


def load_partial_results() -> dict[str, dict]:
    """Load any existing partial results."""
    if PARTIAL_PATH.exists():
        with open(PARTIAL_PATH, encoding="utf-8") as f:
            data = json.load(f)
            # Index by name+coords to handle duplicates
            return {
                f"{p['name']}_{p['lat']}_{p['lon']}": p for p in data.get("peaks", [])
            }
    return {}


def save_partial_results(results: list[dict]) -> None:
    """Save partial results for resumability."""
    with open(PARTIAL_PATH, "w", encoding="utf-8") as f:
        json.dump({"peaks": results}, f, indent=2)


def generate_title_variants(name: str) -> list[str]:
    """Generate possible Wikipedia title variants for a peak name."""
    variants = [name]

    # Add disambiguation variants
    variants.append(f"{name} (Montana)")
    variants.append(f"{name} (Glacier National Park)")

    # Mount <-> Mountain conversions
    if name.startswith("Mount "):
        base = name[6:]
        variants.append(f"Mt. {base}")
        variants.append(f"{base} Mountain")
    elif name.startswith("Mt. "):
        base = name[4:]
        variants.append(f"Mount {base}")
        variants.append(f"{base} Mountain")
    elif name.endswith(" Mountain"):
        base = name[:-9]
        variants.append(f"Mount {base}")
        variants.append(f"Mt. {base}")

    # Handle hyphenated names
    if "-" in name:
        variants.append(name.replace("-", " "))

    # Handle apostrophes (some CSV names might be missing them)
    if "s " in name and "'" not in name:
        # Try adding apostrophe before 's'
        variants.append(re.sub(r"(\w)s ", r"\1's ", name))

    return variants


def search_wikipedia(session: requests_cache.CachedSession, query: str) -> list[dict]:
    """Search Wikipedia for articles matching query."""
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": 5,
        "format": "json",
    }
    response = session.get(WIKIPEDIA_API, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data.get("query", {}).get("search", [])


def get_page_by_title(
    session: requests_cache.CachedSession, title: str
) -> Optional[dict]:
    """Try to get a Wikipedia page by exact title."""
    params = {
        "action": "query",
        "titles": title,
        "prop": "extracts|coordinates|info",
        "explaintext": "true",
        "inprop": "url",
        "format": "json",
        "redirects": "1",  # Follow redirects
    }
    response = session.get(WIKIPEDIA_API, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    pages = data.get("query", {}).get("pages", {})
    for page_id, page in pages.items():
        if page_id != "-1" and "missing" not in page:
            return page
    return None


def get_page_content(
    session: requests_cache.CachedSession, page_id: int
) -> Optional[dict]:
    """Get full content of a Wikipedia page by ID."""
    params = {
        "action": "query",
        "pageids": page_id,
        "prop": "extracts|coordinates|info",
        "explaintext": "true",
        "inprop": "url",
        "format": "json",
    }
    response = session.get(WIKIPEDIA_API, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    pages = data.get("query", {}).get("pages", {})
    return pages.get(str(page_id))


def verify_article(
    article_text: str, peak_lat: float, peak_lon: float, article_coords: Optional[list]
) -> bool:
    """Verify that an article is about a peak in Glacier National Park."""
    text_lower = article_text.lower()

    # Check for GNP or Montana mentions
    gnp_mentions = (
        "glacier national park" in text_lower
        or "montana" in text_lower
        or "lewis range" in text_lower
        or "livingston range" in text_lower
    )

    # Check coordinates if available
    coords_match = False
    if article_coords:
        for coord in article_coords:
            lat_diff = abs(coord.get("lat", 0) - peak_lat)
            lon_diff = abs(coord.get("lon", 0) - peak_lon)
            if lat_diff < 0.1 and lon_diff < 0.1:
                coords_match = True
                break

    return gnp_mentions or coords_match


def find_wikipedia_article(
    session: requests_cache.CachedSession, peak: dict
) -> Optional[dict]:
    """
    Find the Wikipedia article for a peak using multi-pass search.
    Returns article info or None if not found.
    """
    name = peak["name"]
    lat = peak["lat"]
    lon = peak["lon"]

    # Pass 1: Try direct title lookups
    title_variants = generate_title_variants(name)
    for title in title_variants:
        page = get_page_by_title(session, title)
        if page:
            text = page.get("extract", "")
            coords = page.get("coordinates")
            if verify_article(text, lat, lon, coords):
                return {
                    "title": page.get("title"),
                    "url": page.get("fullurl"),
                    "text": text,
                    "page_id": page.get("pageid"),
                }
        time.sleep(REQUEST_DELAY)

    # Pass 2: Search API
    search_queries = [
        f'"{name}" Glacier National Park',
        f'"{name}" Montana mountain',
        f"{name} peak Montana",
    ]

    for query in search_queries:
        results = search_wikipedia(session, query)
        for result in results[:3]:
            page = get_page_content(session, result["pageid"])
            if page:
                text = page.get("extract", "")
                coords = page.get("coordinates")
                if verify_article(text, lat, lon, coords):
                    return {
                        "title": page.get("title"),
                        "url": page.get("fullurl"),
                        "text": text,
                        "page_id": page.get("pageid"),
                    }
        time.sleep(REQUEST_DELAY)

    return None


def fetch_all_wikipedia_data() -> list[dict]:
    """Fetch Wikipedia data for all peaks."""
    session = _setup_session()
    peaks = load_peaks()
    existing = load_partial_results()
    results = []

    print(f"Processing {len(peaks)} peaks...")

    for i, peak in enumerate(peaks):
        key = f"{peak['name']}_{peak['lat']}_{peak['lon']}"

        # Skip if already processed
        if key in existing:
            results.append(existing[key])
            print(f"[{i+1}/{len(peaks)}] {peak['name']} - cached")
            continue

        print(f"[{i+1}/{len(peaks)}] {peak['name']} - fetching...", end=" ")

        article = find_wikipedia_article(session, peak)

        result = {
            "name": peak["name"],
            "lat": peak["lat"],
            "lon": peak["lon"],
            "elevation": peak["elevation"],
            "has_article": article is not None,
            "wikipedia_url": article["url"] if article else None,
            "wikipedia_text": article["text"] if article else None,
        }

        results.append(result)

        if article:
            print(f"found: {article['title']}")
        else:
            print("NOT FOUND")

        # Save progress periodically
        if (i + 1) % 10 == 0:
            save_partial_results(results)

    return results


def main():
    """Main entry point."""
    print("Fetching Wikipedia data for Glacier National Park peaks...")
    print(f"CSV: {CSV_PATH}")
    print(f"Output: {OUTPUT_PATH}")
    print()

    results = fetch_all_wikipedia_data()

    # Calculate statistics
    with_articles = sum(1 for r in results if r["has_article"])
    without_articles = len(results) - with_articles

    # Build final output
    output = {
        "peaks": results,
        "metadata": {
            "total_peaks": len(results),
            "peaks_with_articles": with_articles,
            "peaks_without_articles": without_articles,
            "generated_at": datetime.now().isoformat(),
        },
    }

    # Save final output
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Clean up partial file if successful
    if PARTIAL_PATH.exists():
        PARTIAL_PATH.unlink()

    print()
    print(f"Done! Results saved to {OUTPUT_PATH}")
    print(f"  - Peaks with articles: {with_articles}")
    print(f"  - Peaks without articles: {without_articles}")


if __name__ == "__main__":
    main()
