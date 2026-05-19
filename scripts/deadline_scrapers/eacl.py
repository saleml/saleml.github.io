"""Scrape EACL official pages for submission deadlines."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup

USER_AGENT = "lahlou-deadlines-sync/1.0 (+https://lahlou.org/deadlines/)"
TIMEOUT = 25

# Keywords near dates on CFP pages
DEADLINE_KEYWORDS = re.compile(
    r"(abstract|paper|submission|notification|camera[- ]?ready|rebuttal)",
    re.I,
)
ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
MONTH_DATE = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})",
    re.I,
)
MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def _fetch(url: str) -> str | None:
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
        if r.status_code >= 400:
            return None
        return r.text
    except requests.RequestException:
        return None


def _parse_date_token(text: str) -> str | None:
    m = ISO_DATE.search(text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = MONTH_DATE.search(text)
    if m:
        month = MONTHS[m.group(1).lower()]
        return f"{m.group(3)}-{month:02d}-{int(m.group(2)):02d}"
    return None


def _extract_deadlines_from_html(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    deadlines: list[dict[str, Any]] = []
    seen: set[str] = set()

    for line in text.split("\n"):
        line = line.strip()
        if len(line) < 8 or len(line) > 400:
            continue
        if not DEADLINE_KEYWORDS.search(line):
            continue
        d = _parse_date_token(line)
        if not d or d in seen:
            continue
        seen.add(d)
        label = "Submission"
        low = line.lower()
        if "abstract" in low:
            label = "Abstract"
        elif "paper" in low:
            label = "Paper"
        elif "notification" in low:
            label = "Notification"
        deadlines.append({
            "label": label,
            "date": d,
            "timezone": "AoE",
            "note": None,
        })

    # Also scan table cells
    for cell in soup.find_all(["td", "th", "li", "p"]):
        chunk = cell.get_text(" ", strip=True)
        if not DEADLINE_KEYWORDS.search(chunk):
            continue
        d = _parse_date_token(chunk)
        if not d or d in seen:
            continue
        seen.add(d)
        low = chunk.lower()
        label = "Abstract" if "abstract" in low else "Paper" if "paper" in low else "Submission"
        deadlines.append({"label": label, "date": d, "timezone": "AoE", "note": None})

    return deadlines


def _clean_meta(value: str, fallback: str) -> str:
    v = (value or "").strip()
    if not v or len(v) > 70:
        return fallback
    if re.search(r"\b(ACs|SACs|Committee|Call for|specifics)\b", v, re.I):
        return fallback
    return v


def _clean_location(loc: str) -> str:
    loc = _clean_meta(loc, "TBA")
    if loc == "TBA":
        return loc
    if "," in loc or re.search(
        r"\b(USA|UK|U\.S\.|France|Germany|Spain|Italy|Netherlands|Austria|"
        r"Switzerland|Canada|China|Japan|Korea|India|UAE|Morocco)\b",
        loc,
        re.I,
    ):
        return loc
    return "TBA"


def _extract_location_dates(soup: BeautifulSoup) -> tuple[str, str]:
    text = soup.get_text(" ", strip=True)
    location = "TBA"
    dates = "TBD"
    loc_m = re.search(r"(?:Location|Venue|Place)[:\s]+([^\n.]{4,70})", text, re.I)
    if loc_m:
        location = _clean_location(loc_m.group(1))
    date_m = re.search(
        r"(?:Conference dates|Main conference dates?)[:\s]+"
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}"
        r"[^\n.]{0,40}\d{4})",
        text,
        re.I,
    )
    if date_m:
        dates = _clean_meta(date_m.group(1), "TBD")
    return location, dates


def scrape_eacl(urls: list, entry: dict) -> list:
    """Return card dicts for each configured year (scrape or TBA)."""
    title = entry.get("title", "EACL")
    full_name = entry.get("full_name", title)
    tags = entry.get("tags", ["nlp"])
    cards = []
    now_year = datetime.now().year

    for item in urls:
        year = int(item.get("year", now_year))
        if year < now_year - 1 or year > now_year + 1:
            continue
        link = item.get("link") or item.get("cfp") or ""
        cfp = item.get("cfp") or link
        card_id = f"eacl{year}"

        html = _fetch(cfp) if cfp else None
        if not html and link:
            html = _fetch(link)

        if not html:
            cards.append(_tba_card(card_id, title, full_name, tags, year, link))
            continue

        soup = BeautifulSoup(html, "html.parser")
        deadlines = _extract_deadlines_from_html(html)
        submission = [
            d for d in deadlines
            if d["label"] in ("Abstract", "Paper", "Submission")
        ]
        if not submission:
            cards.append(_tba_card(card_id, title, full_name, tags, year, link))
            continue

        location, dates = _extract_location_dates(soup)
        cards.append({
            "id": card_id,
            "name": f"{title} {year}",
            "fullName": full_name,
            "tags": tags,
            "link": link or cfp,
            "location": location,
            "dates": dates,
            "deadlines": submission,
            "source": "scrape",
        })
    return cards


def _tba_card(card_id, title, full_name, tags, year, link):
    return {
        "id": card_id,
        "name": f"{title} {year}",
        "fullName": full_name,
        "tags": tags,
        "link": link or "https://www.aclweb.org/",
        "location": "TBA",
        "dates": "TBD",
        "deadlines": [{"label": "Submission", "date": None, "timezone": "AoE", "note": "TBA"}],
        "source": "tba",
    }
