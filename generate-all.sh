#!/usr/bin/env bash
# Regenerate every picker in pickers/ from the BOM JSONs in builds/.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p pickers
for f in builds/*.json; do
  name="$(basename "$f" .json)"
  python3 build.py "$f" "pickers/$name.html"
  echo
done
echo "Done. Open any pickers/*.html in a browser."
