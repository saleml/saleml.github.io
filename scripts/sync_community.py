#!/usr/bin/env python3
"""
Sync the website community page from the CV LaTeX sources.

Reads:
  ../CV/cv.tex              (Academic Service, Institutional Service, open-source)
  ../CV/publications.tex    (editorial / edited volumes)

Writes _pages/community.md.

Inclusion is an explicit allowlist, because the community page is a
highlights list rather than a full dump of reviewing, juries, and
committees.

Tag syntax (on a \\cventry line, combinable with % NEWS: / % TALK:):

  % COMMUNITY
  % COMMUNITY:roles
  % COMMUNITY:workshops
  % COMMUNITY:editorial
  % COMMUNITY:roles [HTML]          # full <li> body; do not include the leading -
  % NO-COMMUNITY                    # silence the missing-tag warning

If the group is omitted, it is inferred from the role:
  organizer → workshops, editor → editorial, otherwise → roles.

Open-source enumerate items are always included.

Usage (from the site root):
    python3 scripts/sync_community.py
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
SITE_ROOT = HERE.parent
CV_FILE = SITE_ROOT.parent / "CV" / "cv.tex"
PUBS_FILE = SITE_ROOT.parent / "CV" / "publications.tex"
OUT_FILE = SITE_ROOT / "_pages" / "community.md"

COMMUNITY_RE = re.compile(
    r"%\s*COMMUNITY(?::(?P<group>roles|workshops|editorial))?(?:\s+\[(?P<html>.*?)\])?"
)
NO_COMMUNITY_RE = re.compile(r"%\s*NO-COMMUNITY\b")
WARN_ROLE_RE = re.compile(
    r"chair|organiz|editor|committee",
    re.IGNORECASE,
)
SKIP_WARN_RE = re.compile(r"^reviewer\b", re.IGNORECASE)

SECTION_HEADING_RE = re.compile(r"\\(?:sub)?section\*?\{([^}]+)\}")
ENUM_ITEM_RE = re.compile(
    r"\\item\s+\\href\{(?P<url>[^}]*)\}\{(?P<label>[^}]*)\}:\s*(?P<desc>.*?)(?=\\item|\\end\{enumerate\})",
    re.DOTALL,
)

HEADER = """---
title: Community
layout: about
permalink: /community/
published: true
---

## Community
"""

FOOTER = """- Reviewing duties for a broader set of venues (ICLR, ICML, NeurIPS, UAI, AAAI, ECAI, TMLR, IEEE TPAMI, JASA, ACL, NETYS, ...) and full committee/jury service are listed in the <a href="{{site.baseurl}}/assets/files/CV.pdf" target="_blank">CV</a>.
"""

SECTION_TITLES = {
    "roles": "Conference Roles",
    "workshops": "Workshops Organized",
    "software": "Open-Source Software",
    "editorial": "Editorial",
}


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
    s = re.sub(r"\\emph\{([^{}]*)\}", r"*\1*", s)
    s = re.sub(r"\\textcolor\{blue\}\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\small\{([^{}]*)\}", r"\1", s)
    s = s.replace(r"\&", "&amp;")
    s = re.sub(r"--", "&ndash;", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def strip_role(role_arg: str) -> str:
    return latex_to_html(role_arg)


def infer_group(role: str) -> str:
    blob = role.lower()
    if "editor" in blob:
        return "editorial"
    if "organiz" in blob:
        return "workshops"
    return "roles"


def trailing_chunk(text: str, end: int) -> str:
    nxt = text.find(r"\cventry", end)
    heading = SECTION_HEADING_RE.search(text, end)
    cuts = [len(text)]
    if nxt != -1:
        cuts.append(nxt)
    if heading:
        cuts.append(heading.start())
    return text[end : min(cuts)]


def parse_tagged_cventries(text: str, warn_section: bool = False):
    items = []
    i = 0
    while True:
        idx = text.find(r"\cventry", i)
        if idx == -1:
            break
        result = parse_cventry(text, idx)
        if result is None:
            i = idx + 1
            continue
        args, end = result
        chunk = text[idx:end] + trailing_chunk(text, end)
        no_community = bool(NO_COMMUNITY_RE.search(chunk))
        m = COMMUNITY_RE.search(chunk)
        role = strip_role(args[1])
        venue = latex_to_html(args[2])
        extra = latex_to_html(args[5]) if args[5].strip() else ""

        if warn_section and not m and not no_community:
            if WARN_ROLE_RE.search(role) and not SKIP_WARN_RE.search(role):
                print(
                    f"warning: community highlight missing % COMMUNITY / % NO-COMMUNITY: {role}",
                    file=sys.stderr,
                )

        if m:
            group = m.group("group") or infer_group(role)
            html = m.group("html")
            if html is None:
                body = venue or extra
                html = f"**{role}** &mdash; {body}." if body else f"**{role}**."
            years = re.findall(r"20\d{2}", args[0])
            year = int(years[-1]) if years else 0
            items.append({"group": group, "html": html.strip(), "year": year})
        i = end
    return items


def extract_section(text: str, heading: str) -> str:
    m = re.search(
        rf"\\section\{{{re.escape(heading)}\}}(.*?)(?=\\section\{{)",
        text,
        re.DOTALL,
    )
    return m.group(1) if m else ""


def parse_open_source(text: str):
    section = extract_section(text, "Selected Contributions in Open-Source Code Repositories")
    items = []
    for m in ENUM_ITEM_RE.finditer(section):
        label = latex_to_html(m.group("label"))
        short = label
        paren = re.search(r"\(([^)]+)\)$", label)
        if paren:
            short = paren.group(1)
        desc = latex_to_html(m.group("desc"))
        first = desc.split(". ")[0].rstrip(".")
        items.append(
            {
                "group": "software",
                "year": 0,
                "html": (
                    f'<a href="{m.group("url")}" target="_blank"><strong>{short}</strong></a>'
                    f" &mdash; {first}."
                ),
            }
        )
    return items


def render(groups: dict[str, list[str]]) -> str:
    out = [HEADER]
    for key in ("roles", "workshops", "software", "editorial"):
        entries = groups.get(key) or []
        if not entries and key != "editorial":
            continue
        out.append(f"### {SECTION_TITLES[key]}")
        out.append("")
        for html in entries:
            out.append(f"- {html}")
        if key == "editorial":
            out.append(FOOTER.rstrip())
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main():
    if not CV_FILE.exists():
        sys.exit(f"CV file not found: {CV_FILE}")
    if not PUBS_FILE.exists():
        sys.exit(f"Publications file not found: {PUBS_FILE}")

    cv = CV_FILE.read_text()
    pubs = PUBS_FILE.read_text()

    academic = extract_section(cv, "Academic Service")
    institutional = extract_section(cv, "Institutional Service")

    items = []
    items.extend(parse_tagged_cventries(academic, warn_section=True))
    items.extend(parse_tagged_cventries(institutional, warn_section=False))
    items.extend(parse_open_source(cv))
    items.extend(parse_tagged_cventries(pubs, warn_section=False))

    groups: dict[str, list[dict]] = {k: [] for k in SECTION_TITLES}
    for item in items:
        groups[item["group"]].append(item)
    for key, entries in groups.items():
        entries.sort(key=lambda e: e["year"], reverse=True)
        groups[key] = [e["html"] for e in entries]

    OUT_FILE.write_text(render(groups))
    counts = ", ".join(f"{k}={len(v)}" for k, v in groups.items() if v)
    print(f"Wrote {OUT_FILE}")
    print(f"  {counts}")


if __name__ == "__main__":
    main()
