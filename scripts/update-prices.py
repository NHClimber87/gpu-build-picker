#!/usr/bin/env python3
"""
update-prices — weekly price sourcing for the catalog (Phase 3 engine).

Writes provenance-stamped PRICE RECORDS straight into catalog.json. Only GPU parts
that opt in (PRICE_KEYS below, mapping part_id -> GPU Poet slug) are touched. For each:

  1. fetch the last few months of GPU Poet "lowest-average" prices,
  2. robust-aggregate them: per-category floor/ceiling sanity gate, then a ±k·MAD
     outlier drop, headline value = the freshest surviving month (current price),
  3. rewrite parts[i].price = a record whose sources are the surviving monthly
     datapoints (so the in-page low-median-high band reflects recent volatility),
  4. append the headline to parts[i].price.history (a 12-week ring buffer -> sparkline).

HARD RULES honored:
  - specs, ids, categories are NEVER touched (only price records).
  - build overrides (e.g. the 8x3090 $850 deal) live on the build ITEM, not the part,
    so they are structurally immune to this path — the old "no price_key" trick, done right.
  - feeds that don't return a parseable, sane price leave the part exactly as-is.
  - the proven feed set is gpupoet ONLY (see scripts/probe-feeds.py: pcpartpicker returns
    junk $0.00, geizhals 403s, techpowerup has no price). Do not add a feed without proving it.

Run weekly by .github/workflows/update-prices.yml, or locally:
  python3 scripts/update-prices.py [--dry-run]
Then `bash generate-all.sh` to rebuild the pickers (the workflow does this for you).
"""
import json, re, os, sys, urllib.request, datetime

HERE    = os.path.dirname(os.path.abspath(__file__))
ROOT    = os.path.normpath(os.path.join(HERE, ".."))
CATALOG = os.path.join(ROOT, "catalog.json")
DATA    = os.path.join(ROOT, "data", "prices.json")

# part_id -> GPU Poet slug. Only these parts auto-update.
PRICE_KEYS = {
    "gpu-rtx3090":    "nvidia-geforce-rtx-3090",
    "gpu-rtx3090-ti": "nvidia-geforce-rtx-3090-ti",
    "gpu-rtx5090":    "nvidia-geforce-rtx-5090",
}
# per-category sanity band — drops absurd parses (e.g. a placeholder $0.00).
FLOOR_CEIL = {"gpu": (200, 20000)}
MAD_K   = 3.0     # ±k·MAD outlier gate
MONTHS  = 3       # how many recent months to sample
HIST_MAX = 12     # weeks kept in the sparkline ring buffer
UA = "Mozilla/5.0 (gpu-build-picker price-cache)"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "ignore")

def recent_months(n=MONTHS):
    d = datetime.date.today()
    for i in range(n):
        m, y = d.month - i, d.year
        while m <= 0:
            m += 12; y -= 1
        first = datetime.date(y, m, 1)
        yield first.strftime("%B-%Y").lower(), first.isoformat()

def median(xs):
    s = sorted(xs); n = len(s)
    if not n: return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

def gpupoet_samples(slug):
    """[(value, iso_date, url)] across the last few months."""
    out = []
    for mo, iso in recent_months():
        url = f"https://gpupoet.com/gpu/learn/price/{mo}/{slug}"
        try:
            html = fetch(url)
        except Exception:
            continue
        m = re.search(r"average price</b>\s*of[^$]*\$([\d,]+)", html)
        if m:
            out.append((int(m.group(1).replace(",", "")), iso, url))
    return out

def robust(samples, floor, ceil):
    """floor/ceiling gate -> ±k·MAD drop. Returns (headline_value, surviving_samples)."""
    vals = [s for s in samples if floor <= s[0] <= ceil]
    if not vals:
        return None, []
    nums = [v[0] for v in vals]
    m = median(nums)
    mad = median([abs(v - m) for v in nums]) or 0
    kept = [s for s in vals if mad == 0 or abs(s[0] - m) <= MAD_K * mad] or vals
    kept.sort(key=lambda s: s[1], reverse=True)   # freshest month first
    return kept[0][0], kept                        # current price = freshest survivor

def make_record(headline, survivors, today, old):
    sources = [{"url": u, "value": v, "sourced_at": iso, "method": "gpupoet", "confidence": "medium"}
               for (v, iso, u) in survivors]
    rec = {"value": headline, "estimated": False, "sources": sources}
    # carry forward a usage note if the old record had one
    if isinstance(old, dict) and old.get("note"):
        rec["note"] = old["note"]
    # history ring buffer (dedupe by week), newest last
    prev_hist = (old.get("history") or []) if isinstance(old, dict) else []
    hist = [h for h in prev_hist if h.get("week") != today]
    hist.append({"week": today, "value": headline})
    rec["history"] = hist[-HIST_MAX:]
    return rec

def main():
    dry = "--dry-run" in sys.argv
    today = datetime.date.today().isoformat()
    cat = json.load(open(CATALOG, encoding="utf-8"))
    parts = {p["id"]: p for p in cat.get("parts", [])}

    touched, log_prices, log_sources = 0, {}, {}
    print("sourcing tracked GPU prices (gpupoet only — the proven feed):")
    for pid, slug in PRICE_KEYS.items():
        part = parts.get(pid)
        if not part:
            print(f"  {pid:16s} (not in catalog — skipped)"); continue
        floor, ceil = FLOOR_CEIL.get(part.get("category", ""), (1, 10**7))
        samples = gpupoet_samples(slug)
        headline, survivors = robust(samples, floor, ceil)
        if headline is None:
            print(f"  {pid:16s} (no sane price — left unchanged)"); continue
        new_rec = make_record(headline, survivors, today, part.get("price"))
        if part.get("price") != new_rec:
            part["price"] = new_rec; touched += 1
        log_prices[pid] = headline
        log_sources[pid] = survivors[0][2]
        band = f" (band ${min(s[0] for s in survivors):,}-${max(s[0] for s in survivors):,}, {len(survivors)} mo)" if len(survivors) > 1 else ""
        print(f"  {pid:16s} ${headline:,}{band}")

    if dry:
        print("\n--dry-run: catalog.json NOT written.")
        return

    json.dump(cat, open(CATALOG, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    open(CATALOG, "a").write("\n")
    print(f"\nwrote catalog.json — {touched} price record(s) updated.")

    # secondary human-readable log (handy for eyeballing a run)
    os.makedirs(os.path.dirname(DATA), exist_ok=True)
    json.dump({"updated": today,
               "note": "Cron cache of gpupoet GPU prices. catalog.json is the source of truth; this is a log.",
               "prices": log_prices, "sources": log_sources},
              open(DATA, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"wrote {os.path.relpath(DATA, ROOT)} (log). Run ./generate-all.sh to rebuild the pickers.")

if __name__ == "__main__":
    main()
