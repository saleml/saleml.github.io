#!/usr/bin/env bash
# Build, test, and serve the deadlines page locally.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PORT="${PORT:-9876}"

if [[ ! -d .venv-deadlines ]]; then
  python3 -m venv .venv-deadlines
  .venv-deadlines/bin/pip install -q -r scripts/requirements-deadlines.txt
fi

echo "==> Syncing deadlines..."
.venv-deadlines/bin/python scripts/sync_deadlines.py

echo "==> Building _site (test mirror)..."
./scripts/build_test_site.sh

echo "==> Running tests..."
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory _site &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT
sleep 1

.venv-deadlines/bin/python scripts/test_deadlines_local.py --http-base "http://127.0.0.1:$PORT"
node scripts/_test_deadlines_browser.mjs "http://127.0.0.1:$PORT"

echo ""
echo "All tests passed. Open in browser:"
echo "  http://127.0.0.1:$PORT/deadlines/"
echo ""
echo "Press Ctrl+C to stop the server."
wait $SERVER_PID
