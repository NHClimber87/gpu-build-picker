#!/usr/bin/env python3
"""
update-prices — weekly price cache for gpu-build-picker.

Live retailer scraping (Newegg / Micro Center / Amazon) is blocked server-side
(403 / 429), so this pulls the big movers — GPUs — from GPU Poet, a price-tracker
that DOES serve server-side, and:
  1. writes data/prices.json (a dated record + badge), and
  2. patches the `price` of any build row that opted in with a "price_key",
     so the regenerated pickers carry fresh prices.

Run weekly by .github/workflows/update-prices.yml (or a local cron). Only parts a
row opts into via price_key are touched — e.g. the 8x3090 build keeps its $850
*deal* price because that row has no price_key. Anything it can't fetch is left
exactly as-is.

Usage:  python3 scripts/update-prices.py [--no-patch]
"""
import json, re, os, sys, glob, urllib.request, datetime

HERE   = os.path.dirname(os.path.abspath(__file__))
ROOT   = os.path.normpath(os.path.join(HERE, ".."))
DATA   = os.path.join(ROOT, "data", "prices.json")
BUILDS = os.path.join(ROOT, "builds")

# tracked parts: price_key -> GPU Poet slug
GPUS = {
    "rtx-3090":    "nvidia-geforce-rtx-3090",
    "rtx-3090-ti": "nvidia-geforce-rtx-3090-ti",
    "rtx-5090":    "nvidia-geforce-rtx-5090",
}

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (gpu-build-picker price-cache)"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "ignore")

def recent_months(n=3):
    d = datetime.date.today()
    for i in range(n):
        m, y = d.month - i, d.year
        while m <= 0:
            m += 12; y -= 1
        yield datetime.date(y, m, 1).strftime("%B-%Y").lower()

def gpupoet_price(slug):
    """Lowest-average price for a GPU, trying the current month then falling back."""
    for mo in recent_months():
        url = f"https://gpupoet.com/gpu/learn/price/{mo}/{slug}"
        try:
            html = fetch(url)
        except Exception:
            continue
        m = re.search(r"average price</b>\s*of[^$]*\$([\d,]+)", html)
        if m:
            return int(m.group(1).replace(",", "")), url
    return None, None

def patch_builds(prices):
    touched = 0
    for path in sorted(glob.glob(os.path.join(BUILDS, "*.json"))):
        spec = json.load(open(path, encoding="utf-8"))
        changed = False
        for row in spec.get("rows", []):
            k = row.get("price_key")
            if k and k in prices and row.get("price") != prices[k]:
                row["price"] = prices[k]; changed = True; touched += 1
        if changed:
            json.dump(spec, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
            print(f"  patched {os.path.basename(path)}")
    return touched

def main():
    prices, sources, missing = {}, {}, []
    print("fetching tracked GPU prices (GPU Poet):")
    for key, slug in GPUS.items():
        val, url = gpupoet_price(slug)
        if val:
            prices[key] = val; sources[key] = url
            print(f"  {key:12s} ${val:,}")
        else:
            missing.append(key); print(f"  {key:12s} (no data — left unchanged)")

    out = {
        "updated": datetime.date.today().isoformat(),
        "note": "Auto-cached GPU prices (lowest-average) from GPU Poet. Retailers block scraping; non-GPU parts keep their baked-in/flagged prices.",
        "prices": prices, "sources": sources,
    }
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    json.dump(out, open(DATA, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"wrote {os.path.relpath(DATA, ROOT)} — {len(prices)} prices"
          + (f", {len(missing)} missing" if missing else ""))

    if "--no-patch" not in sys.argv and prices:
        n = patch_builds(prices)
        print(f"patched {n} build row(s). Run ./generate-all.sh to refresh the pickers.")

if __name__ == "__main__":
    main()
