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
python3 build-index.py
echo "Done. Open index.html (all builds, switchable) or any pickers/*.html."
