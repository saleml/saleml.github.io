"""Per-conference deadline scrapers (used when HF has no data)."""

from .eacl import scrape_eacl

SCRAPERS = {
    "eacl": scrape_eacl,
}


def run_scraper(adapter: str, urls: list, entry: dict) -> list:
    fn = SCRAPERS.get(adapter)
    if not fn:
        return []
    return fn(urls, entry)
