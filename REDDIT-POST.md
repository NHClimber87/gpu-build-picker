# Reddit post — gpu-build-picker

**Target:** r/LocalLLaMA (flair: Resources / Tutorial | Guide)
**Before posting:** add the screenshot inline (the on-fire 4× RTX PRO 6000 build is the money shot).
**Links:** Pages → https://nhclimber87.github.io/gpu-build-picker · Repo → https://github.com/NHClimber87/gpu-build-picker

---

**Title:** I made an offline, single-file GPU build picker that estimates what local models a rig will run — and at what tok/s

**TLDR:** One HTML file, no backend. Pick parts, it tells you what models fit and the decode speed, calibrated to real measured 3090 numbers.

I keep speccing 3090 boxes and the eternal question is never "what does it cost" — PCPartPicker does that — it's *will this thing actually run the model I want, and how fast*. So I built a picker that answers that.

It's a single self-contained HTML page. No build step, no framework, no account, no tracking. Opens on `file://`. The whole thing is a dumb renderer over one `catalog.json`.

**What it does**
- **Capability estimator** — pick a model class + quant, it gives you resident size, fit (VRAM / spills to RAM / won't fit), estimated decode and prefill, and a capability score. Decode is modeled as memory-bandwidth-bound and calibrated to numbers I actually measured on 3090s.
- **Prices are records, not numbers** — every line carries provenance: sourced (green) / estimate (amber) / stale (red), so a number is never silently wrong. Live tax + shipping + under/over-budget math.
- **Paste a product URL → it grabs the price** (via a CORS proxy; if it can't read it, it says so — never fabricates).
- Weekly auto-refresh of the volatile prices via a GitHub Action. No backend anywhere.

**On the decode calibration** — first pass I had MoE wrong: it estimated off *total* params, so my 120B-A12B box read ~13 t/s. Reality is ~67 t/s because decode only moves the *active* params (A12B) when the model's resident in VRAM. Fixed it to track active params and checked it against the real number. Single-3090 anchors it's calibrated to: dense 27B ≈ 40, 35B-A3B ≈ 87, 70B ≈ 18 t/s; 120B-A12B MoE ≈ 67 t/s resident on 4×3090.

**Reference builds included:** a $2.2k single-3090 starter, my actual 4×3090 96GB workstation, a 192GB 8×3090 server under $25k, and a 4× RTX PRO 6000 384GB rig (~$43k — the tool draws the machine, and that one literally renders on fire).

MIT, runs on GitHub Pages: [link] · repo: [link]

Happy to add model presets or correct my bandwidth assumptions if anyone's measured different.
