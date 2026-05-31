#!/usr/bin/env bash
# Minimal _site/ for local deadlines testing (when bundle/jekyll unavailable).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SITE="$ROOT/_site"
rm -rf "$SITE"
mkdir -p "$SITE/assets/data" "$SITE/assets/js" "$SITE/deadlines"

# Strip Jekyll front matter from deadlines page
python3 - "$ROOT/deadlines/index.html" "$SITE/deadlines/index.html" << 'PY'
import sys
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2])
text = src.read_text(encoding="utf-8")
if text.startswith("---"):
    end = text.find("\n---\n", 3)
    if end != -1:
        text = text[end + 5 :]
dst.write_text(text, encoding="utf-8")
PY

cp "$ROOT/assets/data/deadlines.json" "$SITE/assets/data/"
cp "$ROOT/assets/js/deadlines.js" "$SITE/assets/js/"
echo "Built test site at $SITE"
