#!/usr/bin/env python3
"""
build.py — generate a single-build picker by baking the catalog into the template.

Usage:
  build.py <build-id> [out.html]      # one build, full parts catalog for the dropdowns
  build.py --index   [out.html]       # all builds with the switcher (same as build-index.py)

The picker bakes the WHOLE catalog (so the category dropdowns work offline on file://),
then tries fetch('catalog.json') at runtime so GitHub Pages auto-updates from the cron.
A single-build page sets FOCUS_BUILD_ID so only that build shows in the switcher.

No price is ever invented here — the catalog is the single source of truth, and every
price is a provenance-stamped record (see catalog.json / catalog.schema.json).
"""
import json, sys, os, html

HERE = os.path.dirname(os.path.abspath(__file__))

def esc(s): return html.escape(str(s if s is not None else ""), quote=True)

def load_catalog():
    return json.load(open(os.path.join(HERE, "catalog.json"), encoding="utf-8"))

def part_index(cat):
    return {p["id"]: p for p in cat.get("parts", [])}

def norm_price(p):
    if isinstance(p, (int, float)):
        return {"value": p, "estimated": True,
                "sources": [{"value": p, "sourced_at": "", "method": "build-override", "confidence": "low"}]}
    return p

def build_total(cat, build):
    """Subtotal/tax/ship/grand for the console summary (mirrors the in-page math)."""
    parts = part_index(cat)
    sub = 0.0
    missing = 0
    for it in build.get("items", []):
        part = parts.get(it["part_id"], {})
        rec = norm_price(it.get("price_override")) or part.get("price") or {"value": 0}
        v = float(rec.get("value", 0) or 0)
        if not v:
            missing += 1
        sub += (it.get("qty", 0) or 0) * v
    tax = sub * float(build.get("tax_pct", 0) or 0) / 100
    ship = float(build.get("shipping", 0) or 0)
    return sub, tax, ship, sub + tax + ship, missing

def render(cat, title, subtitle, focus_id):
    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    repl = {
        "__TITLE__":        esc(title),
        "__SUBTITLE__":     esc(subtitle),
        "__CATALOG_JSON__": json.dumps(cat, ensure_ascii=False, indent=2),
        "__FOCUS_JSON__":   json.dumps(focus_id, ensure_ascii=False),
    }
    for k, v in repl.items():
        tpl = tpl.replace(k, v)
    return tpl

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    cat = load_catalog()

    if sys.argv[1] in ("--index", "-i"):
        out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "index.html")
        title = "GPU Build Picker"
        subtitle = "Pick a reference build above, or edit any line. Live cost + provenance + capability score + a machine that builds itself."
        open(out, "w", encoding="utf-8").write(render(cat, title, subtitle, None))
        print(f"wrote {out} — index ({len(cat.get('builds',[]))} builds)")
        return

    build_id = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, build_id + ".html")
    build = next((b for b in cat.get("builds", []) if b["id"] == build_id), None)
    if not build:
        print(f"no build with id {build_id!r}. Known: " + ", ".join(b["id"] for b in cat.get("builds", [])))
        sys.exit(1)

    open(out, "w", encoding="utf-8").write(render(cat, build["name"], build.get("subtitle", ""), build_id))

    sub, tax, ship, grand, missing = build_total(cat, build)
    print(f"wrote {out} — build {build_id!r}, {len(build.get('items',[]))} items")
    print(f"subtotal ${sub:,.0f} · tax ${tax:,.0f} · ship ${ship:,.0f} · GRAND ${grand:,.0f}")
    if build.get("budget"):
        head = build["budget"] - grand
        verdict = f"${head:,.0f} under" if head >= 0 else f"${-head:,.0f} OVER"
        print(f"budget ${build['budget']:,.0f} → {verdict}")
    if missing:
        print(f"⚠ {missing} item(s) resolve to no price")

if __name__ == "__main__":
    main()
