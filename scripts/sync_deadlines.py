#!/usr/bin/env python3
"""
Sync conference deadlines from Hugging Face ai-deadlines and local scrapers.

Usage (from site root):
    python3 scripts/sync_deadlines.py
"""

from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
import yaml

HERE = Path(__file__).resolve().parent
SITE_ROOT = HERE.parent
WATCHLIST = SITE_ROOT / "deadlines" / "watchlist.yaml"
OVERRIDES = SITE_ROOT / "deadlines" / "overrides.yaml"
OUT_JSON = SITE_ROOT / "assets" / "data" / "deadlines.json"
HF_RAW = (
    "https://huggingface.co/spaces/huggingface/ai-deadlines/raw/main"
    "/src/data/conferences/{slug}.yml"
)

SUBMISSION_TYPES = frozenset({
    "abstract", "paper", "submission", "registration",
})
SKIP_TYPES = frozenset({
    "rebuttal_start", "rebuttal_end", "rebuttal",
    "notification", "camera_ready", "supplementary",
})

MONTHS_PAST_GRACE_DAYS = 365


def load_yaml(path: Path) -> Any:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def fetch_hf_yaml(slug: str) -> list | None:
    url = HF_RAW.format(slug=slug)
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            return None
        data = yaml.safe_load(r.text)
        return data if isinstance(data, list) else None
    except (requests.RequestException, yaml.YAMLError):
        return None


def parse_date_only(dt: str | None) -> str | None:
    if not dt:
        return None
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(dt).strip())
    return m.group(1) if m else None


def deadline_end_utc(date_str: str, tz: str | None) -> datetime:
    """End instant for countdown (AoE = UTC-12 end of listed calendar day)."""
    y, m, d = map(int, date_str.split("-"))
    if tz and str(tz).strip().upper() in ("AOE", "UTC-12"):
        return datetime(y, m, d, tzinfo=timezone.utc) + timedelta(days=1, hours=12)
    return datetime(y, m, d, 23, 59, 59, tzinfo=timezone.utc)


def extract_submission_deadlines(block: dict) -> list[dict]:
    rows: list[dict] = []
    if block.get("abstract_deadline"):
        rows.append({
            "label": "Abstract",
            "date": parse_date_only(block["abstract_deadline"]),
            "timezone": block.get("timezone", "AoE"),
            "note": None,
        })
    if block.get("deadline") and not block.get("deadlines"):
        rows.append({
            "label": "Paper",
            "date": parse_date_only(block["deadline"]),
            "timezone": block.get("timezone", "AoE"),
            "note": block.get("comment"),
        })
    for item in block.get("deadlines") or []:
        typ = (item.get("type") or "").lower()
        if typ in SKIP_TYPES:
            continue
        if typ and typ not in SUBMISSION_TYPES:
            continue
        label = item.get("label") or typ.replace("_", " ").title() or "Submission"
        rows.append({
            "label": label,
            "date": parse_date_only(item.get("date")),
            "timezone": item.get("timezone") or block.get("timezone", "AoE"),
            "note": item.get("comment"),
        })
    # dedupe by label+date
    seen = set()
    out = []
    for r in rows:
        if not r.get("date"):
            continue
        key = (r["label"], r["date"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def block_is_stale(block: dict, now: datetime) -> bool:
    dls = extract_submission_deadlines(block)
    if not dls:
        return True
    latest = max(deadline_end_utc(d["date"], d.get("timezone")) for d in dls)
    return latest < now - timedelta(days=MONTHS_PAST_GRACE_DAYS)


def location_from_block(block: dict) -> str:
    if block.get("venue"):
        return str(block["venue"])
    city, country = block.get("city"), block.get("country")
    if city and country:
        return f"{city}, {country}"
    if city:
        return str(city)
    if country:
        return str(country)
    return "TBA"


def hf_block_to_card(block: dict, entry: dict) -> dict | None:
    year = block.get("year")
    if not year:
        return None
    title = entry.get("title") or block.get("title", "Conference")
    tags = entry.get("tags", [])
    deadlines = extract_submission_deadlines(block)
    card_id = block.get("id") or f"{entry['id']}{year}"
    return {
        "id": str(card_id),
        "name": f"{title} {year}",
        "fullName": block.get("full_name") or entry.get("full_name") or title,
        "tags": tags,
        "link": block.get("link") or "",
        "location": location_from_block(block),
        "dates": block.get("date") or "TBD",
        "deadlines": deadlines if deadlines else [
            {"label": "Submission", "date": None, "timezone": "AoE", "note": "TBA"},
        ],
        "source": "hf" if deadlines else "tba",
    }


def target_years(now: datetime) -> set[int]:
    y = now.year
    return {y, y + 1}


def cards_from_hf(entry: dict, now: datetime) -> list[dict]:
    slug = entry.get("hf_slug")
    if not slug:
        return []
    blocks = fetch_hf_yaml(slug)
    if not blocks:
        return []
    years_wanted = target_years(now)
    cards = []
    for block in blocks:
        year = block.get("year")
        if year not in years_wanted:
            continue
        if block_is_stale(block, now):
            continue
        card = hf_block_to_card(block, entry)
        if card:
            cards.append(card)
    return cards


def tba_card_for_year(entry: dict, year: int, link: str = "") -> dict:
    eid = entry["id"]
    title = entry.get("title", eid)
    return {
        "id": f"{eid}{year}",
        "name": f"{title} {year}",
        "fullName": entry.get("full_name", title),
        "tags": entry.get("tags", []),
        "link": link or "",
        "location": "TBA",
        "dates": "TBD",
        "deadlines": [
            {"label": "Submission", "date": None, "timezone": "AoE", "note": "TBA"},
        ],
        "source": "tba",
    }


def cards_from_scrape(entry: dict, now: datetime) -> list[dict]:
    scrape = entry.get("scrape") or {}
    adapter = scrape.get("adapter")
    urls = scrape.get("urls") or []
    if not adapter:
        return []
    sys.path.insert(0, str(HERE))
    from deadline_scrapers import run_scraper

    return run_scraper(adapter, urls, entry)


def merge_entry_cards(entry: dict, now: datetime) -> list[dict]:
    hf_slug = entry.get("hf_slug")
    cards: list[dict] = []

    if hf_slug:
        cards = cards_from_hf(entry, now)
        years_found = set()
        for c in cards:
            m = re.search(r"(\d{4})\s*$", c["name"])
            if m:
                years_found.add(int(m.group(1)))
        for y in target_years(now):
            if y not in years_found:
                # try scrape if configured for missing year
                scrape = entry.get("scrape")
                if scrape:
                    year_urls = [
                        u for u in (scrape.get("urls") or [])
                        if int(u.get("year", 0)) == y
                    ]
                    if year_urls:
                        sub = {**entry, "scrape": {**scrape, "urls": year_urls}}
                        cards.extend(cards_from_scrape(sub, now))
                    else:
                        cards.append(tba_card_for_year(entry, y))
                else:
                    cards.append(tba_card_for_year(entry, y, ""))
    else:
        cards = cards_from_scrape(entry, now)
        years_found = set()
        for c in cards:
            m = re.search(r"(\d{4})\s*$", c["name"])
            if m:
                years_found.add(int(m.group(1)))
        for y in target_years(now):
            if y not in years_found:
                link = ""
                for u in (entry.get("scrape") or {}).get("urls") or []:
                    if int(u.get("year", 0)) == y:
                        link = u.get("link") or ""
                cards.append(tba_card_for_year(entry, y, link))

    return cards


def apply_overrides(cards: list[dict], overrides: dict) -> list[dict]:
    patches = {c["id"]: c for c in (overrides.get("conferences") or []) if c.get("id")}
    if not patches:
        return cards
    out = []
    for card in cards:
        cid = card["id"]
        if cid in patches:
            merged = deepcopy(card)
            merged.update(patches[cid])
            out.append(merged)
        else:
            out.append(card)
    return out


def main() -> int:
    watch = load_yaml(WATCHLIST)
    overrides = load_yaml(OVERRIDES)
    entries = watch.get("conferences") or []
    now = datetime.now(timezone.utc)

    all_cards: list[dict] = []
    for entry in entries:
        all_cards.extend(merge_entry_cards(entry, now))

    all_cards = apply_overrides(all_cards, overrides)

    payload = {
        "last_updated": now.strftime("%Y-%m-%d"),
        "source": "huggingface/ai-deadlines + local scrapers",
        "conferences": all_cards,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if OUT_JSON.exists() and OUT_JSON.read_text(encoding="utf-8") == text:
        print("No changes to deadlines.json")
        return 0
    OUT_JSON.write_text(text, encoding="utf-8")
    print(f"Wrote {len(all_cards)} conference cards to {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
