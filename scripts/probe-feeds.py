#!/usr/bin/env python3
"""
probe-feeds — PROVE which price aggregators are fetchable from a CI runner IP
BEFORE building a scraper against them. (Phase 3, step 0 of the refactor prompt:
"turn the central assumption into measured fact".)

Many candidate feeds (PCPartPicker / Geizhals) sit behind Cloudflare and may block
GitHub Actions runner IPs exactly where we'd need them. This script curls one known
part (RTX 3090) from each candidate, reports the HTTP status, and whether a price is
greppable. Only feeds that return a PARSEABLE price from CI should be wired into
update-prices.py. It mutates nothing.

Run it from the runner via .github/workflows/probe-feeds.yml (manual dispatch), or
locally: python3 scripts/probe-feeds.py
"""
import re, sys, urllib.request, datetime

UA = "Mozilla/5.0 (gpu-build-picker feed-probe)"

def month_slug(off=0):
    d = datetime.date.today()
    m, y = d.month - off, d.year
    while m <= 0:
        m += 12; y -= 1
    return datetime.date(y, m, 1).strftime("%B-%Y").lower()

# (name, url, price_regex). Geizhals/PCPartPicker are the "measure before trusting" ones.
FEEDS = [
    ("gpupoet (known-good)",
     f"https://gpupoet.com/gpu/learn/price/{month_slug()}/nvidia-geforce-rtx-3090",
     r"average price</b>\s*of[^$]*\$([\d,]+)"),
    ("pcpartpicker",
     "https://pcpartpicker.com/products/video-card/#sort=price&c=12",
     r"\$([\d,]+\.\d{2})"),
    ("geizhals",
     "https://geizhals.eu/?fs=rtx+3090&hloc=us",
     r"€\s*([\d.,]+)"),
    ("techpowerup",
     "https://www.techpowerup.com/gpu-specs/geforce-rtx-3090.c3622",
     r"\$([\d,]+)"),
]

def probe(name, url, rx):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            status = r.status
            body = r.read().decode("utf-8", "ignore")
        m = re.search(rx, body)
        price = m.group(1) if m else None
        verdict = "PASS — parseable price" if price else "soft — fetched but no price matched"
        print(f"  [{status}] {name:24s} {verdict}" + (f"  (${price})" if price else ""))
        return bool(price)
    except Exception as e:
        print(f"  [ERR] {name:24s} blocked/failed: {type(e).__name__}: {str(e)[:80]}")
        return False

def main():
    print("Probing candidate price feeds for RTX 3090 from THIS IP:\n")
    passed = [name for name, url, rx in FEEDS if probe(name, url, rx)]
    print(f"\nUsable feeds from here: {passed or '(only build on what passed — do not assume)'}")
    # Non-zero only if even the known-good feed fails (something is wrong with the run).
    sys.exit(0 if any(n.startswith("gpupoet") for n in passed) else 1)

if __name__ == "__main__":
    main()
