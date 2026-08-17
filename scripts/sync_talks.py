#!/usr/bin/env python3
"""
Sync the website talks page from the CV LaTeX source.

Reads ../CV/cv.tex (Invited Talks and Presentations section) and writes
_pages/talks.md.

Optional trailing tag on a talk line (or after a multi-line \\cventry):

  % TALK: [HTML suffix]     # appended after venue, e.g. slides / tutorial links

Usage (from the site root):
    python3 scripts/sync_talks.py
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
SITE_ROOT = HERE.parent
CV_FILE = SITE_ROOT.parent / "CV" / "cv.tex"
OUT_FILE = SITE_ROOT / "_pages" / "talks.md"

MONTH_ORDER = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}
TALK_TAG_RE = re.compile(r"%\s*TALK:\s*\[(.*?)\]\s*$")
SECTION_RE = re.compile(
    r"\\section\{Invited Talks and Presentations\}(.*?)(?=\\section\{)",
    re.DOTALL,
)


def find_balanced(text: str, start: int) -> int:
    assert text[start] == "{"
    depth = 1
    i = start + 1
    while i < len(text) and depth > 0:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    if depth != 0:
        raise ValueError(f"Unbalanced braces starting at {start}")
    return i


def parse_cventry(text: str, start: int):
    tag = r"\cventry"
    if not text.startswith(tag, start):
        return None
    i = start + len(tag)
    args = []
    for _ in range(6):
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text) or text[i] != "{":
            return None
        end = find_balanced(text, i)
        args.append(text[i + 1 : end - 1])
        i = end
    return args, i


def latex_to_html(s: str) -> str:
    s = re.sub(
        r"\\href\{([^}]*)\}\{([^}]*)\}",
        r'<a href="\1" target="_blank">\2</a>',
        s,
    )
    s = re.sub(r"\\textbf\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\textit\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\textcolor\{blue\}\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\small\{([^{}]*)\}", r"\1", s)
    s = s.replace(r"\&", "&amp;")
    s = re.sub(r"--", "&ndash;", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_title(title_arg: str) -> str:
    m = re.match(r"\s*\\small\{(?P<inner>.*)\}\s*$", title_arg, re.DOTALL)
    inner = m.group("inner") if m else title_arg
    m2 = re.match(r"\s*\\textit\{(?P<t>.*)\}\s*$", inner, re.DOTALL)
    if m2:
        return latex_to_html(m2.group("t"))
    return latex_to_html(inner)


def extract_itemize_details(desc: str) -> str:
    if r"\begin{itemize}" not in desc:
        return ""
    items = re.findall(
        r"\\item\s+(.*?)(?=\\item|\\end\{itemize\})",
        desc,
        re.DOTALL,
    )
    cleaned = []
    for item in items:
        item = latex_to_html(item)
        item = item.replace("``", '"').replace("''", '"')
        cleaned.append(item)
    return "; ".join(cleaned)


def parse_talk_suffix(chunk: str) -> str:
    for line in chunk.splitlines():
        m = TALK_TAG_RE.search(line.rstrip())
        if m:
            return m.group(1).strip()
    return ""


def month_sort_key(date: str) -> int:
    parts = date.split()
    if len(parts) >= 2 and parts[-1].isdigit():
        year = int(parts[-1])
        month = MONTH_ORDER.get(parts[0], 0)
        return year * 100 + month
    m = re.search(r"(20\d{2})", date)
    return int(m.group(1)) * 100 if m else 0


def year_from_date(date: str) -> str:
    m = re.search(r"(20\d{2})", date)
    return m.group(1) if m else date


def parse_talks(section_text: str):
    talks = []
    i = 0
    while True:
        idx = section_text.find(r"\cventry", i)
        if idx == -1:
            break
        result = parse_cventry(section_text, idx)
        if result is None:
            i = idx + 1
            continue
        args, end = result
        next_idx = section_text.find(r"\cventry", end)
        if next_idx == -1:
            next_idx = len(section_text)
        suffix = parse_talk_suffix(section_text[idx:next_idx])

        title = extract_title(args[1])
        venue = latex_to_html(args[2])
        details = extract_itemize_details(args[5])
        body = venue
        if details:
            body = f"{venue}. {details}" if venue else details

        talks.append(
            {
                "date": args[0].strip(),
                "year": year_from_date(args[0]),
                "title": title,
                "body": body,
                "suffix": suffix,
            }
        )
        i = end
    return talks


def render_talk(t: dict) -> str:
    line = f'- **{t["date"]}** &mdash; *{t["title"]}.*'
    if t["body"]:
        body = t["body"].rstrip(".")
        line += f' {body}.'
    if t["suffix"]:
        line += f' {t["suffix"]}'
    return line


HEADER = """---
title: Talks
layout: about
permalink: /talks/
published: true
---

## Invited Talks and Presentations
"""


def main():
    if not CV_FILE.exists():
        sys.exit(f"CV file not found: {CV_FILE}")

    text = CV_FILE.read_text()
    m = SECTION_RE.search(text)
    if not m:
        sys.exit("Invited Talks section not found in cv.tex")

    talks = parse_talks(m.group(1))
    if not talks:
        sys.exit("No talks found in Invited Talks section")

    by_year: dict[str, list[dict]] = {}
    for talk in talks:
        by_year.setdefault(talk["year"], []).append(talk)

    out = [HEADER]
    for year in sorted(by_year.keys(), reverse=True):
        out.append(f"### {year}")
        out.append("")
        for talk in sorted(by_year[year], key=lambda t: month_sort_key(t["date"]), reverse=True):
            out.append(render_talk(talk))
            out.append("")

    OUT_FILE.write_text("\n".join(out).rstrip() + "\n")
    print(f"Wrote {OUT_FILE}")
    print(f"  {len(talks)} talks across {len(by_year)} years")


if __name__ == "__main__":
    main()
