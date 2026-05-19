#!/usr/bin/env python3
"""Local smoke test for /deadlines/ page (run after jekyll build)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

SITE_ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = SITE_ROOT / "_site"
JSON_PATH = SITE_DIR / "assets" / "data" / "deadlines.json"
JS_PATH = SITE_DIR / "assets" / "js" / "deadlines.js"
HTML_PATH = SITE_DIR / "deadlines" / "index.html"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def test_built_files() -> None:
    for p in (JSON_PATH, JS_PATH, HTML_PATH):
        if not p.is_file():
            fail(f"Missing built file: {p.relative_to(SITE_ROOT)}")
    ok("Built files exist under _site/")


def test_json() -> list:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    confs = data.get("conferences")
    if not isinstance(confs, list) or len(confs) < 10:
        fail(f"Expected conferences list, got {type(confs)} len={len(confs) if confs else 0}")
    for c in confs:
        for key in ("id", "name", "tags", "deadlines"):
            if key not in c:
                fail(f"Card {c.get('id')} missing {key}")
    ok(f"JSON valid ({len(confs)} conferences)")
    return confs


def test_html_paths() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    if 'src="../assets/js/deadlines.js"' not in html:
        fail("HTML should use relative ../assets/js/deadlines.js")
    if "deadlines.json" not in html:
        fail("HTML should reference deadlines.json")
    ok("HTML asset paths look correct")


def test_js_logic(confs: list) -> None:
    """Run deadlines.js helpers via node."""
    import subprocess

    node_script = SITE_ROOT / "scripts" / "_test_deadlines_node.mjs"
    node_script.write_text(
        """
import fs from 'fs';
const root = process.argv[2];
const data = JSON.parse(fs.readFileSync(`${root}/assets/data/deadlines.json`, 'utf8'));
let code = fs.readFileSync(`${root}/assets/js/deadlines.js`, 'utf8');
code = code.replace(/^let CONFERENCES = \\[\\];\\n*/m, '');
const api = new Function('CONFERENCES', code + `
  sortConferences(CONFERENCES);
  return true;
`);
api(data.conferences);
console.log('node-sort-ok');
""",
        encoding="utf-8",
    )
    # Use source assets (same as built for js)
    src_js = SITE_ROOT / "assets" / "js" / "deadlines.js"
    built_js = SITE_DIR / "assets" / "js" / "deadlines.js"
    if src_js.read_text() != built_js.read_text():
        fail("Built deadlines.js differs from source — rebuild site")

    r = subprocess.run(
        ["node", str(node_script), str(SITE_ROOT)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        fail(f"Node JS test failed:\\n{r.stderr or r.stdout}")
    ok("JS sort logic runs without error")


def test_http(base: str) -> None:
    """Fetch page and assets from local server."""
    page_url = f"{base}/deadlines/"
    json_url = f"{base}/assets/data/deadlines.json"
    js_url = f"{base}/assets/js/deadlines.js"

    for url in (page_url, json_url, js_url):
        try:
            with urlopen(url, timeout=5) as resp:
                if resp.status != 200:
                    fail(f"{url} returned {resp.status}")
        except (HTTPError, URLError) as e:
            fail(f"Could not fetch {url}: {e}")

    with urlopen(page_url, timeout=5) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    if 'id="conf-list"' not in html:
        fail("Page missing conf-list container")

  # Resolve relative JSON URL as browser would from /deadlines/
    with urlopen(json_url, timeout=5) as resp:
        json.loads(resp.read().decode())

    ok(f"HTTP smoke test passed ({base})")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--http-base", default="", help="e.g. http://127.0.0.1:4000")
    args = parser.parse_args()

    if not SITE_DIR.is_dir():
        fail("_site/ not found — run: bundle exec jekyll build")

    test_built_files()
    confs = test_json()
    test_html_paths()
    test_js_logic(confs)

    if args.http_base:
        test_http(args.http_base.rstrip("/"))

    print("\nAll local deadline tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
