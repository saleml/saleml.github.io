#!/usr/bin/env python3
"""
Sync publications from the CV LaTeX source to the website.

Reads  ../CV/publications.tex  and writes _pages/publications.md
in a three-column scrollable layout:

    [ Journal & Conference ]  [ Workshop ]  [ Preprints & Under Review ]

Thesis & edited volumes are rendered as a small appended section.

Usage (from the site root):
    python3 scripts/sync_publications.py
"""

from pathlib import Path
import html
import re
import sys

HERE = Path(__file__).resolve().parent
SITE_ROOT = HERE.parent
CV_FILE = SITE_ROOT.parent / "CV" / "publications.tex"
OUT_FILE = SITE_ROOT / "_pages" / "publications.md"


def find_balanced(text: str, start: int) -> int:
    assert text[start] == "{", f"Expected '{{' at {start}, got {text[start]!r}"
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


def tex_to_plain(s: str) -> str:
    """Strip LaTeX formatting; return plain text (for titles / venues)."""
    m = re.match(r"\s*\\small\{(?P<inner>.*)\}\s*$", s, re.DOTALL)
    if m:
        s = m.group("inner")

    # \href{url}{text} -> <a href="url" target="_blank">text</a>
    s = re.sub(
        r"\\href\{([^}]*)\}\{([^}]*)\}",
        r'<a href="\1" target="_blank">\2</a>',
        s,
    )
    # Drop formatting macros (we display only title + venue, no author markup)
    s = re.sub(r"\\textbf\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\textit\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\textcolor\{blue\}\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\mbox\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\small\{([^{}]*)\}", r"\1", s)
    s = s.replace(r"\&", "&")
    s = re.sub(r"\s+", " ", s).strip()
    return s


_ABBREV_WORDS = {"vol", "Ph", "Dr", "Prof", "Mr", "Mrs", "Ms", "etc", "eg", "ie"}


def _is_abbrev(token: str) -> bool:
    """Return True if `token` looks like an abbreviation (so the '. ' after it
    should NOT be used as the author/venue split point)."""
    t = token.rstrip(".,")
    if not t:
        return False
    # Single uppercase letter: author initial ("S.", "J.")
    if len(t) == 1 and t.isupper():
        return True
    # Short tokens with internal period: "Ph.D", "U.S", "e.g", "i.e", "J.K"
    # (longer tokens like "(Editors.)" are not abbrevs.)
    if "." in t and len(t) <= 5:
        return True
    # Known abbreviations
    if t in _ABBREV_WORDS:
        return True
    return False


def extract_venue(body: str) -> str:
    """Body is 'AUTHORS. VENUE'. Return just VENUE.

    Walk from the end of the text and pick the first `. ` whose preceding
    token is NOT an abbreviation. This avoids splitting inside 'Ph.D.',
    'vol.', or initials like 'S. Lahlou'.
    """
    plain = tex_to_plain(body)
    # Normalize '1000(' -> '1000 ('
    plain = re.sub(r"(\d)\(", r"\1 (", plain)

    # Walk split candidates from the end.
    for m in reversed(list(re.finditer(r"\. ", plain))):
        pos = m.start()
        # Find the preceding non-space token
        j = pos - 1
        while j >= 0 and not plain[j].isspace():
            j -= 1
        token = plain[j + 1 : pos]
        if _is_abbrev(token):
            continue
        return plain[pos + 2 :].strip(" .")
    return plain.strip(" .")


def authors_to_html(body: str) -> str:
    """Body is 'AUTHORS. VENUE'. Return the AUTHORS portion as HTML, preserving
    the CV color code: people supervised by me (\\textcolor{blue}) in blue and
    me (\\textbf) in bold. Equal-contribution asterisks are kept as-is.
    """
    s = body
    s = re.sub(
        r"\\href\{([^}]*)\}\{([^}]*)\}",
        r'<a href="\1" target="_blank">\2</a>',
        s,
    )
    s = re.sub(
        r"\\textcolor\{blue\}\{([^{}]*)\}",
        r'<span class="pub-author-student">\1</span>',
        s,
    )
    s = re.sub(r"\\textbf\{([^{}]*)\}", r'<strong class="pub-author-me">\1</strong>', s)
    s = re.sub(r"\\textit\{([^{}]*)\}", r"<em>\1</em>", s)
    s = re.sub(r"\\mbox\{([^{}]*)\}", r"\1", s)
    s = s.replace(r"\&", "&amp;")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(\d)\(", r"\1 (", s)

    # Split off the trailing venue using the same abbreviation-aware rule as
    # extract_venue (the HTML tags introduced above never contain '. ').
    for m in reversed(list(re.finditer(r"\. ", s))):
        pos = m.start()
        j = pos - 1
        while j >= 0 and not s[j].isspace():
            j -= 1
        token = s[j + 1 : pos]
        if _is_abbrev(token):
            continue
        return s[:pos].strip(" .")
    return s.strip(" .")


def parse_section(section_text: str):
    entries = []
    i = 0
    while True:
        idx = section_text.find(r"\cventry", i)
        if idx == -1:
            break
        result = parse_cventry(section_text, idx)
        if result is None:
            i = idx + 1
            continue
        args, i = result
        entries.append(
            {
                "year": args[0].strip(),
                "title": tex_to_plain(args[1]),
                "venue": extract_venue(args[2]),
                "authors": authors_to_html(args[2]),
            }
        )
    return entries


def split_into_sections(text: str):
    parts = re.split(r"\\subsection\{([^}]+)\}", text)
    result = {}
    for k in range(1, len(parts), 2):
        result[parts[k].strip()] = parts[k + 1]
    return result


def render_column_html(entries) -> str:
    """Render entries as raw HTML (not subject to kramdown parsing)."""
    out = []
    current_year = None
    for e in entries:
        if e["year"] != current_year:
            if current_year is not None:
                out.append("</ul>")
            out.append(f'<p class="pub-year">{html.escape(e["year"])}</p>')
            out.append("<ul>")
            current_year = e["year"]
        # Title may contain <a href="...">text</a> from \href; don't escape it.
        title = e["title"]
        venue = e["venue"]
        authors = e.get("authors", "")
        authors_html = f'<div class="pub-authors">{authors}</div>' if authors else ""
        out.append(
            f'<li><strong>{title}.</strong> <em>{venue}</em>{authors_html}</li>'
        )
    if current_year is not None:
        out.append("</ul>")
    return "\n".join(out)


HEADER = """---
title: Publications
layout: about
permalink: /publications/
published: true
---

## Publications

<p style="font-size: 0.9em; color: #666;">
* = equal contribution.
</p>
"""

STYLE = """<style>
/* Break out of the default 800px body width for the publications page */
body { max-width: 1200px !important; }

.publications-columns {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 1.2em;
  margin-top: 1.2em;
}
.publications-column {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.publications-column h3 {
  margin: 0 0 0.5em 0;
  font-size: 1em;
  padding-bottom: 0.3em;
  border-bottom: 1px solid #d3d3d3;
}
.publications-scroll {
  max-height: 70vh;
  overflow-y: auto;
  padding: 0.2em 0.75em 0.5em 0.25em;
  font-size: 0.82em;
  line-height: 1.45;
}
.publications-scroll ul {
  padding-left: 1.1em;
  margin: 0.3em 0 0.8em 0;
  list-style: disc;
}
.publications-scroll li {
  margin-bottom: 0.5em;
}
.publications-scroll p.pub-year {
  margin: 0.7em 0 0.2em 0;
  font-weight: 600;
}
.pub-authors {
  font-size: 0.9em;
  color: #666;
  margin-top: 0.1em;
  line-height: 1.35;
}
.pub-author-student { color: #1a56db; }
.pub-author-me { font-weight: 700; color: #000; }
@media (max-width: 720px) {
  body { max-width: 100% !important; }
  .publications-columns { grid-template-columns: 1fr; }
  .publications-scroll { max-height: none; }
}
</style>
"""


def main():
    if not CV_FILE.exists():
        sys.exit(f"Publications file not found: {CV_FILE}")
    text = CV_FILE.read_text()
    sections = split_into_sections(text)

    conf = parse_section(sections.get("Journal and Conference Papers (Published / Accepted)", ""))
    workshop = parse_section(sections.get("Workshop Papers and Extended Abstracts", ""))
    preprints = parse_section(sections.get("Preprints and Under Review", ""))
    thesis = parse_section(sections.get("Thesis and Edited Volumes", ""))

    out = [HEADER]
    out.append('<div class="publications-columns">')
    for title, entries in [
        ("Journal &amp; Conference Papers", conf),
        ("Workshop Papers &amp; Extended Abstracts", workshop),
        ("Preprints &amp; Under Review", preprints),
    ]:
        out.append('<div class="publications-column">')
        out.append(f'<h3>{title}</h3>')
        out.append('<div class="publications-scroll">')
        out.append(render_column_html(entries))
        out.append('</div>')
        out.append('</div>')
    out.append('</div>')

    if thesis:
        out.append("")
        out.append("### Thesis and Edited Volumes")
        out.append("")
        for e in thesis:
            authors = e.get("authors", "")
            authors_html = (
                f'<br><span class="pub-authors">{authors}</span>' if authors else ""
            )
            out.append(f'- **{e["title"]}.** *{e["venue"]}*{authors_html}')

    out.append("")
    out.append(STYLE)

    OUT_FILE.write_text("\n".join(out) + "\n")
    print(f"Wrote {OUT_FILE}")
    print(f"  Journal/Conf: {len(conf)}, Workshop: {len(workshop)}, Preprints: {len(preprints)}, Thesis: {len(thesis)}")


if __name__ == "__main__":
    main()
