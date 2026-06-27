#!/usr/bin/env python3
"""
priceit build — inject a priced BOM into the picker template.

Usage:
  build.py <bom.json> [out.html]

bom.json schema:
{
  "title":    "My Build",                      # required
  "subtitle": "one-line summary",              # optional
  "tax_pct":  8,                               # optional (default 0)
  "shipping": 0,                               # optional (default 0)
  "budget":   25000,                           # optional; 0/absent hides the budget line
  "sys_bw_gbs": 90,                            # optional; system-RAM bandwidth (GB/s) for the capability calc
  "rows": [
    {"name":"Item","spec":"notes","qty":1,"price":0,"url":"https://...","flag":"verify",
     # optional hardware hints feed the Capability Estimator (per unit, x qty):
     "vram_gb":24, "bw_gbs":936, "tflops":71,  # for GPU rows
     "ram_gb":64}                               # for RAM rows
  ]
}

No price is ever invented here — whatever is in the JSON is what ships. Leave price 0 +
flag "needs price" for anything you couldn't ground. Source URLs make every row auditable
and feed the in-page ⤓ autofill.
"""
import json, sys, re, os, html

def esc(s): return html.escape(str(s if s is not None else ""), quote=True)

def slugify(title):
    return re.sub(r"[^a-z0-9]+", "-", str(title).lower()).strip("-") or "picker"

def normalize_rows(rows):
    """Strip rows to the fields the template uses (carrying hardware hints + flags)."""
    norm = []
    for r in rows:
        row = {
            "name":  r.get("name", ""),
            "spec":  r.get("spec", ""),
            "qty":   r.get("qty", 1),
            "price": r.get("price", 0),
            "url":   r.get("url", ""),
        }
        if r.get("flag"):
            row["flag"] = r["flag"]
        for hw in ("vram_gb", "bw_gbs", "tflops", "ram_gb"):  # carry hardware hints through
            if r.get(hw):
                row[hw] = r[hw]
        norm.append(row)
    return norm

def build_record(spec, slug=None, norm=None):
    """One build's data, the shape the template's BUILDS array expects."""
    slug = slug or slugify(spec.get("title", "Price Picker"))
    norm = norm if norm is not None else normalize_rows(spec.get("rows", []))
    return {
        "slug":     slug,
        "title":    spec.get("title", "Price Picker"),
        "subtitle": spec.get("subtitle", ""),
        "menu":     spec.get("menu", spec.get("title", "Build")),
        "tax":      spec.get("tax_pct", spec.get("tax", 0)),
        "ship":     spec.get("shipping", 0),
        "budget":   spec.get("budget", 0) or 0,
        "sysbw":    spec.get("sys_bw_gbs", 0) or 0,
        "rows":     norm,
    }

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    out  = sys.argv[2] if len(sys.argv) > 2 else "price-picker.html"

    title = spec.get("title", "Price Picker")
    slug  = slugify(title)
    norm  = normalize_rows(spec.get("rows", []))

    tpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.html")
    tpl = open(tpl_path, encoding="utf-8").read()

    build_obj = build_record(spec, slug, norm)
    repl = {
        "__TITLE__":       esc(title),
        "__SUBTITLE__":    esc(spec.get("subtitle", "")),
        "__BUILDS_JSON__": json.dumps([build_obj], ensure_ascii=False, indent=2),
    }
    for k, v in repl.items():
        tpl = tpl.replace(k, v)

    open(out, "w", encoding="utf-8").write(tpl)

    sub = sum((r.get("qty", 0) or 0) * (r.get("price", 0) or 0) for r in norm)
    tax = sub * float(spec.get("tax_pct", spec.get("tax", 0)) or 0) / 100
    ship = float(spec.get("shipping", 0) or 0)
    grand = sub + tax + ship
    missing = sum(1 for r in norm if not r.get("price"))
    print(f"wrote {out} — {len(norm)} rows")
    print(f"subtotal ${sub:,.0f} · tax ${tax:,.0f} · ship ${ship:,.0f} · GRAND ${grand:,.0f}")
    if spec.get("budget"):
        head = spec["budget"] - grand
        verdict = f"${head:,.0f} under" if head >= 0 else f"${-head:,.0f} OVER"
        print(f"budget ${spec['budget']:,.0f} → {verdict}")
    if missing:
        print(f"⚠ {missing} row(s) have no price (flagged for manual fill)")

if __name__ == "__main__":
    main()
