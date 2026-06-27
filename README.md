# gpu-build-picker

**A dead-simple, offline, single-file parts picker for GPU / AI rigs.** Edit a tiny JSON, get a self-contained HTML page with live cost math, a source link per line, a budget readout, and a *paste-a-URL→grab-the-price* button. No build step, no framework, no tracking, no account — open the HTML and go.

> Built while speccing a 192GB 8× RTX 3090 inference server for under $25k. The pickers for that and a few other reference builds are in [`pickers/`](pickers/).

<!-- TODO before posting: open pickers/8x3090-192gb.html, screenshot it, save as docs/screenshot.png, and uncomment the line below -->
<!-- ![gpu-build-picker — interactive cost picker](docs/screenshot.png) -->


## Why

PCPartPicker is great until you're pricing *used 3090s on eBay*, *refurb EPYC on a server-surplus site*, and *RDIMMs on Newegg* in the same build — none of which it tracks well. I wanted something that:

- lives in **one HTML file** you can keep in a repo / email / Syncthing,
- keeps a **source URL on every line** so the price is auditable later,
- does the **tax + shipping + "am I under budget" math** live,
- can **read a price straight off a product URL** when the store exposes it,
- and **tells you what models the build will actually run, and how fast** — a built-in capability estimator.

That's the whole thing. Vanilla JS, no dependencies.

## 🧮 Capability estimator — "what will it run?"

Every buyer's real question. The picker derives **total VRAM, system RAM, GPU memory bandwidth, and FP16 TFLOPS** from the parts, then you pick a **target model** (7B → 235B, dense or MoE) and a **quant** (Q4 → FP16) and it tells you:

- **Does it fit?** — entirely in VRAM ✓ / spills to system RAM ◐ / won't fit ✗
- **Estimated decode** (tokens/sec, single user) and **prefill** speed
- A **0–100 capability score** with a one-line tier read

The speed math is **memory-bandwidth-bound** — which is what actually governs LLM decode, not raw FLOPs — and **calibrated to measured single-RTX-3090 numbers** (27B ≈ 40, 35B-A3B ≈ 87, 70B ≈ 18, 120B-A12B ≈ 12 t/s). Spill-to-RAM correctly drags the estimate toward system-RAM bandwidth (the real wall for big-MoE on consumer boards). FLOPs drive the prefill estimate. The calibration constants are right there in the source — tune them to your own measurements.

> These are **rough estimates**, labeled as such in-app. They're for "will a 4×3090 box run a 70B comfortably?" decisions, not benchmark claims.

## ▶ Try it live (no install)

**▶ [Open the app](https://nhclimber87.github.io/gpu-build-picker/)** — one page, a dropdown to switch between all 4 reference builds, edit any line, watch the cost + capability score + the little machine that escalates from a desktop to an on-fire GPU cluster as you add VRAM.

Or jump straight to a single build: [budget 1×3090](https://nhclimber87.github.io/gpu-build-picker/pickers/budget-1x3090-starter.html) · [G2 4×3090](https://nhclimber87.github.io/gpu-build-picker/pickers/g2-4x3090-workstation.html) · [8×3090 server](https://nhclimber87.github.io/gpu-build-picker/pickers/8x3090-192gb.html) · [4×RTX PRO 6000](https://nhclimber87.github.io/gpu-build-picker/pickers/highend-4x6000-threadripper.html)

(Served over https, so the URL autofill works here — unlike opening the file locally.)

## Quick start

```bash
# generate one picker from a build file
python3 build.py builds/8x3090-192gb.json my-picker.html
# open my-picker.html in any browser

# or regenerate all the reference builds
./generate-all.sh
```

You can also just **open a `pickers/*.html` directly** and start editing in the browser — rows, quantities, prices, tax %, and shipping are all live, and everything saves to `localStorage` (so your edits survive a refresh).

## The build file

A build is a small JSON (`builds/*.json`):

```json
{
  "title": "Budget 1× RTX 3090 — Local LLM Starter",
  "subtitle": "24GB VRAM · cheapest sane way into local LLMs",
  "tax_pct": 8,
  "shipping": 0,
  "budget": 2200,
  "rows": [
    {"name": "GPU", "spec": "RTX 3090 24GB (used)", "qty": 1, "price": 1050,
     "url": "https://bestvaluegpu.com/...", "flag": "used market — shop around"}
  ]
}
```

- `budget` is optional — set it and you get a live **"$X under / over"** readout; omit (or `0`) to hide it.
- `flag` is optional per row — shows a small ⚠ caption under the price (use it for "estimate — verify", "search-page price", etc. — see the honesty note below).
- `price: 0` is fine — it just shows as unpriced. Nothing is ever invented for you.

## Autofill from a URL

Each row has a **⤓** button. Paste a product URL into the row's URL field, click ⤓, and it tries to read the **price + title** from the page's structured data:

1. schema.org `Product` JSON-LD (`offers.price`)
2. OpenGraph / `product:price:amount` meta tags
3. a plain-text "Price: $…" fallback

It fetches through a public CORS proxy (`r.jina.ai`, then `corsproxy.io`). **It works on stores that expose structured data and clearly says _"couldn't auto-read — enter manually"_ when they don't. It never makes up a number.**

> ⚠️ Under `file://`, the proxy fetch may be blocked by browser CORS — that's expected; the manual picker still works fully. For reliable autofill, serve the folder: `python3 -m http.server` and open `http://localhost:8000/pickers/…`.

## Reference builds (in [`builds/`](builds/) → [`pickers/`](pickers/))

| Build | VRAM | Ballpark (2026-06) | Notes |
|---|---|---|---|
| [Budget 1× RTX 3090 starter](builds/budget-1x3090-starter.json) | 24 GB | **~$2.1k** | cheapest sane entry to local LLMs |
| [G2 — 4× RTX 3090 workstation](builds/g2-4x3090-workstation.json) | 96 GB | **~$6.7k** | a real, running rig |
| [8× RTX 3090 — 192GB MoE server](builds/8x3090-192gb.json) | 192 GB | **~$22.6k** | Supermicro 4U, 16-ch ~400 GB/s, every GPU x16 |
| [Monster 4× RTX PRO 6000](builds/highend-4x6000-threadripper.json) | **384 GB** | **~$43k** | no-limits build — 96GB GDDR7 per card, frontier models fully resident 🔥 |

**These prices are a 2026-06-26 snapshot and will go stale — that's exactly what the editable fields + ⤓ autofill are for.** Headline parts (GPUs, CPUs) are live-sourced with a URL; supporting parts (board / RAM / PSU / case) are flagged `est — verify`. Open a picker, hit ⤓ on the parts you care about, done.

## Auto-refreshed prices (weekly)

Retailers (Newegg / Micro Center / Amazon) **block scraping** — direct fetches 403/429, so there's no honest way to live-scrape them. Instead, a weekly job pulls the **big movers (GPUs)** from a price-tracker that *does* serve data, and patches the builds:

- [`scripts/update-prices.py`](scripts/update-prices.py) fetches GPU prices (lowest-average) and writes [`data/prices.json`](data/prices.json), then patches any build row that opted in via a `price_key`.
- [`.github/workflows/update-prices.yml`](.github/workflows/update-prices.yml) runs it **every Monday on GitHub's runners** (no local machine needed), regenerates the pickers, and commits.
- Opt-in is per row: a row only auto-updates if it has a `price_key` (e.g. `"rtx-3090"`). The 8×3090 server's GPU line has **no** key, so its $850 *deal* price is never overwritten by market price.
- Non-GPU parts (CPU/RAM/board/PSU) aren't auto-priced — retailers block them and trackers don't cover them well — so those stay as flagged estimates you verify with the ⤓ button.

Run it yourself anytime: `python3 scripts/update-prices.py && ./generate-all.sh`.

## Honesty rules (baked in)

- **No fabricated prices.** A price is either sourced (with a URL) or left at `0`/flagged. The generator (`build.py`) never invents one, and the autofill refuses to guess.
- **Every line is auditable** — the source URL stays with the part.
- Soft prices are **flagged**, not hidden.

## Companion: serving recipes

This prices the *hardware*. For **how to actually serve models** on multi-3090 boxes (vLLM / llama.cpp / ik_llama configs, quant choices, context tuning), see **[club-3090](https://github.com/noonghunna/club-3090)**.

## License

MIT — see [LICENSE](LICENSE). Use it, fork it, ship your own builds.
