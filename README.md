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
- and can **read a price straight off a product URL** when the store exposes it.

That's the whole thing. It's ~250 lines of vanilla JS.

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
| [High-end 4× RTX 5090](builds/highend-4x5090-threadripper.json) | 128 GB | **~$18.2k** | all-new Threadripper contrast build |

**These prices are a 2026-06-26 snapshot and will go stale — that's exactly what the editable fields + ⤓ autofill are for.** Headline parts (GPUs, CPUs) are live-sourced with a URL; supporting parts (board / RAM / PSU / case) are flagged `est — verify`. Open a picker, hit ⤓ on the parts you care about, done.

## Honesty rules (baked in)

- **No fabricated prices.** A price is either sourced (with a URL) or left at `0`/flagged. The generator (`build.py`) never invents one, and the autofill refuses to guess.
- **Every line is auditable** — the source URL stays with the part.
- Soft prices are **flagged**, not hidden.

## Companion: serving recipes

This prices the *hardware*. For **how to actually serve models** on multi-3090 boxes (vLLM / llama.cpp / ik_llama configs, quant choices, context tuning), see **[club-3090](https://github.com/noonghunna/club-3090)**.

## License

MIT — see [LICENSE](LICENSE). Use it, fork it, ship your own builds.
