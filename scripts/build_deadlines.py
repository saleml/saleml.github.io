#!/usr/bin/env python3
"""
Build assets/data/deadlines.json from deadlines/conferences.json.

Edit deadlines/conferences.json by hand or ask an agent to web-search and
update entries, then run:

    python3 scripts/build_deadlines.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE_ROOT = HERE.parent
SRC = SITE_ROOT / "deadlines" / "conferences.json"
OUT = SITE_ROOT / "assets" / "data" / "deadlines.json"

REQUIRED = ("id", "name", "tags", "deadlines")


def main() -> int:
    if not SRC.exists():
        sys.exit(f"Missing source file: {SRC}")

    data = json.loads(SRC.read_text(encoding="utf-8"))
    confs = data.get("conferences") or []
    if not confs:
        sys.exit(f"No conferences listed in {SRC}")

    for c in confs:
        for key in REQUIRED:
            if key not in c:
                sys.exit(f"Conference {c.get('id', '?')} missing required field: {key}")
        c.setdefault("fullName", c["name"])
        c.setdefault("link", "")
        c.setdefault("location", "TBA")
        c.setdefault("dates", "TBD")

    payload = {
        "last_updated": data.get("last_updated")
        or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "deadlines/conferences.json (manual)",
        "conferences": confs,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if OUT.exists() and OUT.read_text(encoding="utf-8") == text:
        print("No changes to deadlines.json")
        return 0

    OUT.write_text(text, encoding="utf-8")
    print(f"Wrote {len(confs)} conferences → {OUT.relative_to(SITE_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
