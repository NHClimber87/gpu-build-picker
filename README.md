# gpu-build-picker

**A dead-simple, offline, data-driven parts picker for GPU / AI rigs.** One JSON catalog, one self-contained HTML page with live cost math, a *provenance badge on every price*, a budget readout, a capability estimator, and a *paste-a-URL→grab-the-price* button. No build step to use it, no framework, no tracking, no account — open the HTML and go.

> Built while speccing a 192GB 8× RTX 3090 inference server for under $25k. That build and three other reference rigs live in [`catalog.json`](catalog.json); the generated pickers are in [`pickers/`](pickers/).

<!-- TODO before posting: open pickers/8x3090-192gb.html, screenshot it, save as docs/screenshot.png, and uncomment the line below -->
<!-- ![gpu-build-picker — interactive cost picker](docs/screenshot.png) -->


## Why

PCPartPicker is great until you're pricing *used 3090s on eBay*, *refurb EPYC on a server-surplus site*, and *RDIMMs on Newegg* in the same build — none of which it tracks well. I wanted something that:

- keeps the **parts as data** (`catalog.json`) and the HTML a dumb renderer,
- puts a **freshness badge on every price** — sourced (green) / estimate (amber) / stale (red) — so a number is never silently wrong,
- does the **tax + shipping + "am I under budget" math** live,
- **tells you what models the build will run, and how fast** — a built-in capability estimator,
- can **auto-refresh** the volatile prices weekly, and let buyers **submit prices they paid** — all with no backend.

That's the whole thing. Vanilla JS, no dependencies.

## The catalog is the database

Everything hangs off [`catalog.json`](catalog.json) — the single source of truth:

```jsonc
{
  "schema_version": 1,
  "repo": "owner/repo",                 // enables the 💬 price-report deep-link
  "parts": [
    { "id": "gpu-rtx3090",              // IMMUTABLE, append-only — saved builds depend on it
      "category": "gpu",                // closed enum: gpu|cpu|motherboard|ram|psu|storage|case|accessory
      "name": "NVIDIA RTX 3090 24GB (used)",
      "specs": { "vram_gb": 24, "bw_gbs": 936, "tflops": 71 },   // closed vocab; feeds the estimator
      "price": {                        // a provenance-stamped record — never a bare number
        "value": 1126, "estimated": false,
        "sources": [{ "url": "https://gpupoet.com/...", "value": 1126,
                      "sourced_at": "2026-06-27", "method": "gpupoet", "confidence": "medium" }],
        "history": [{ "week": "2026-06-27", "value": 1126 }]      // → sparkline
      } } ],
  "builds": [
    { "id": "8x3090-192gb", "name": "...", "tax_pct": 8, "shipping": 140, "budget": 25000,
      "items": [
        { "part_id": "gpu-rtx3090", "qty": 8,
          "price_override": { "value": 850, "estimated": false, "note": "Deal price; market ~$1,050.",
            "sources": [{ "value": 850, "sourced_at": "2026-06-26", "method": "deal-as-bought", "confidence": "medium" }] } }
      ] } ]
}
```

Why this shape:

- **Specs and price are split.** The estimator reads only `specs`; a broken price scrape can move dollars but never the capability score. A missing spec key is treated as *unknown*, never `0`.
- **A price is a record, not a number** — `{value, estimated, sources[], history[]}`. Provenance travels with the money, so the UI can show *how fresh* and *how trustworthy* every line is, and nothing is ever fabricated.
- **Builds are part-id lists.** The same `gpu-rtx3090` resolves once; each build just references it with a `qty`. A `price_override` freezes a build-local price (e.g. the 8×3090's as-bought $850 deal) while the dropdown part stays live.
- **Ids are immutable + append-only.** Renaming one would orphan saved builds and the reference lists, so [`validate.py`](validate.py) enforces it.

Validate any time:

```bash
python3 validate.py        # VALID — 29 parts, 4 builds, all ids resolve.
```

The validator is the **schema-guardian**: unique append-only ids, categories in the enum, spec keys in the vocab, every build `part_id` resolves, every price carries a dated source. The weekly cron runs it and **fails the commit on drift**.

## Quick start

```bash
# regenerate index.html + every per-build picker from catalog.json
./generate-all.sh

# or one build at a time
python3 build.py 8x3090-192gb my-picker.html     # one build (full parts catalog for the dropdowns)
python3 build.py --index index.html              # all builds with the switcher
```

Each picker **bakes the whole catalog** (so the category dropdowns work offline on `file://`) and then tries `fetch('catalog.json')` at runtime — that's how a GitHub Pages copy auto-updates from the cron while the local file still works. Open a `pickers/*.html` and edit rows, quantities, prices, tax %, and shipping live; everything saves to `localStorage`.

## 🧮 Capability estimator — "what will it run?"

Every buyer's real question. The picker derives **total VRAM, system RAM, GPU memory bandwidth, and FP16 TFLOPS** from the parts' `specs`, then you pick a **target model** (7B → 235B, dense or MoE) and a **quant** (Q4 → FP16) and it tells you:

- **Does it fit?** — entirely in VRAM ✓ / spills to system RAM ◐ / won't fit ✗
- **Estimated decode** (tokens/sec, single user) and **prefill** speed
- A **0–100 capability score** with a one-line tier read

The speed math is **memory-bandwidth-bound** — what actually governs LLM decode — and **calibrated to measured single-RTX-3090 numbers** (27B ≈ 40, 35B-A3B ≈ 87, 70B ≈ 18, 120B-A12B ≈ 12 t/s). Spill-to-RAM correctly drags the estimate toward system-RAM bandwidth. The calibration constants are right in the source.

> Rough estimates, labeled as such in-app — for "will a 4×3090 box run a 70B comfortably?" decisions, not benchmark claims.

## ▶ Try it live (no install)

**▶ [Open the app](https://nhclimber87.github.io/gpu-build-picker/)** — one page, a dropdown to switch between all 4 reference builds, edit any line, watch the cost + provenance badges + capability score + the little machine that escalates from a desktop to an on-fire GPU cluster as you add VRAM.

Single builds: [budget 1×3090](https://nhclimber87.github.io/gpu-build-picker/pickers/budget-1x3090-starter.html) · [G2 4×3090](https://nhclimber87.github.io/gpu-build-picker/pickers/g2-4x3090-workstation.html) · [8×3090 server](https://nhclimber87.github.io/gpu-build-picker/pickers/8x3090-192gb.html) · [4×RTX PRO 6000](https://nhclimber87.github.io/gpu-build-picker/pickers/highend-4x6000-threadripper.html)

## Provenance & freshness (the honesty layer)

You can't make every price live, so the picker makes *staleness visible* instead of silently wrong:

- **Per-price badge** from the freshest source date — <span>● sourced &lt;7d</span> (green), ◌ estimate / 7–21d (amber), ● stale &gt;21d (red). A stale price stays **visible**, never deleted.
- **Low–median–high band** when a price has ≥2 sources (e.g. the cron's recent months, or corroborating community quotes), plus a **sparkline** from the weekly history — "was $X four weeks ago" turns the picker into a *when-to-buy* tool.
- **Build-total confidence badge** — `🟢 grounded $X (n%) · 🟠 estimated $Y (m%) ±$Z` — and the estimated portion carries a ± range into the grand total, instead of one fake-precise figure. Verify a 🟠 line with the ⤓ button to shrink it.
- Edit a price by hand and the badge flips to **✎ your price** — honest about what you changed.

## Reference builds (in [`catalog.json`](catalog.json) → [`pickers/`](pickers/))

| Build | VRAM | Ballpark (2026-06) | Notes |
|---|---|---|---|
| Budget 1× RTX 3090 starter | 24 GB | **~$2.2k** | cheapest sane entry to local LLMs |
| G2 — 4× RTX 3090 workstation | 96 GB | **~$7.5k** | a real, running rig |
| 8× RTX 3090 — 192GB MoE server | 192 GB | **~$22.6k** | Supermicro 4U, every GPU x16 |
| Monster 4× RTX PRO 6000 | **384 GB** | **~$43k** | 96GB GDDR7 per card, frontier models resident 🔥 |

GPU prices are live-sourced (badged green); supporting parts are flagged estimates (amber) until you verify them. Open a picker, hit ⤓ or 💬 on the parts you care about.

## Autofill from a URL (⤓)

Paste a product URL into a row's URL field and click **⤓**. It reads the **price + title** from the page's structured data — schema.org `Product` JSON-LD, then OpenGraph `product:price:amount`, then a plain-text fallback — through a public CORS proxy (`r.jina.ai`, then `corsproxy.io`). It works on stores that expose structured data and clearly says *"couldn't auto-read — enter manually"* when they don't. **It never makes up a number.**

> ⚠️ Under `file://`, the proxy fetch may be CORS-blocked — serve the folder for reliable autofill: `python3 -m http.server` then open `http://localhost:8000/pickers/…`.

## Auto-refreshed prices (weekly, no machine needed)

Retailers (Newegg / Micro Center / Amazon) **block scraping** (403/429), so there's no honest way to live-scrape them. Instead a weekly job pulls the **big movers (GPUs)** from a tracker that *does* serve data and writes **price records** into the catalog:

- [`scripts/update-prices.py`](scripts/update-prices.py) sources tracked GPUs (`part_id` → GPU Poet slug), samples the last few months, **robust-aggregates** them (per-category floor/ceiling gate → ±k·MAD outlier drop → freshest surviving month = the current price), rewrites each part's `price` record, and appends to its `history` ring buffer.
- [`.github/workflows/update-prices.yml`](.github/workflows/update-prices.yml) runs it **every Monday on GitHub's runners**, runs `validate.py` (schema-guardian), regenerates the pickers, and commits.
- **Opt-in is per part** (a GPU id in `PRICE_KEYS`). The 8×3090 server's $850 *deal* is a build `price_override`, so it lives on the build item and is structurally **immune** to the cron — the old "no price_key" trick, done right.
- Non-GPU parts stay flagged estimates you verify with ⤓ / 💬.

**Measure before you build.** [`scripts/probe-feeds.py`](scripts/probe-feeds.py) (run via [`.github/workflows/probe-feeds.yml`](.github/workflows/probe-feeds.yml), manual dispatch) curls candidate aggregators from the *runner's IP* and reports which return a parseable price. Measured result: **gpupoet only** — PCPartPicker returns a junk `$0.00`, Geizhals 403s behind Cloudflare, TechPowerUp has no price. Don't add a feed without proving it from CI first.

## Community write-back (crowdsource around the block)

Click **💬** on any catalog row → it opens a **prefilled GitHub issue** (`part_id`, price, URL, ISO timestamp, `price-quote` label). Zero backend — the browser builds the deep-link.

[`.github/workflows/price-quote.yml`](.github/workflows/price-quote.yml) runs [`scripts/ingest-quote.py`](scripts/ingest-quote.py) on the labeled issue: it parses the fenced quote block, validates (known `part_id`, price inside the per-category sanity band **and** within ±40% of the current price, URL on a domain allowlist), and appends every quote to [`data/quotes.jsonl`](data/) as an audit trail. A single quote is **advisory** (added as a low-confidence source, headline price unchanged); once a **2nd in-band quote corroborates** it, their median nudges the price and the sources go medium-confidence. Then it comments, labels accepted/rejected, and closes — all on GitHub's runners.

## Honesty rules (baked in)

- **No fabricated prices.** Every price is either *sourced* (with a dated URL) or *flagged estimate*. The generator never invents one; autofill refuses to guess; the cron and the quote-ingester only write attributed data.
- **Specs are never mutated by the automated path** — only price records are.
- **Ids are append-only** — the validator blocks reuse and id drift.
- **Degrade visibly** — stale stays on screen, red, with an "as of" date. Never silently.

## Companion: serving recipes

This prices the *hardware*. For **how to serve models** on multi-3090 boxes (vLLM / llama.cpp / ik_llama configs, quant choices, context tuning), see **[club-3090](https://github.com/noonghunna/club-3090)**.

## License

MIT — see [LICENSE](LICENSE). Use it, fork it, ship your own catalog (set `catalog.repo` to your `owner/repo` so the 💬 button targets your issues).
