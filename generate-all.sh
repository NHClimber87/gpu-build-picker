#!/usr/bin/env bash
# Regenerate index.html + every per-build picker in pickers/ from catalog.json.
# Validates the catalog first (the schema-guardian) — a broken catalog must not ship.
set -euo pipefail
cd "$(dirname "$0")"

python3 validate.py

mkdir -p pickers
ids=$(python3 -c "import json;print(' '.join(b['id'] for b in json.load(open('catalog.json'))['builds']))")
for id in $ids; do
  python3 build.py "$id" "pickers/$id.html"
  echo
done
python3 build-index.py
echo "Done. Open index.html (all builds, switchable) or any pickers/*.html."
