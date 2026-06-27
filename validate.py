#!/usr/bin/env python3
"""
validate.py — the schema-guardian for catalog.json. Dependency-free.

Enforces the invariants the data-driven picker (and the weekly cron) rely on:
  - ids are unique, append-only-shaped (lowercase/dash), IMMUTABLE in spirit
  - every category is in the closed enum
  - every spec key is in the closed vocab
  - every build item resolves to a real part
  - price records carry provenance (value + >=1 source with the required fields)

Exit 0 = valid (the cron is allowed to commit). Non-zero = drift; the commit must fail.
Usage:  python3 validate.py [catalog.json]
"""
import json, re, sys, os

CATEGORIES = {"gpu", "cpu", "motherboard", "ram", "psu", "storage", "case", "accessory"}
SPEC_VOCAB = {"vram_gb", "bw_gbs", "tflops", "ram_gb", "watts"}
METHODS    = {"gpupoet", "manual", "hardcoded-estimate", "deal-as-bought", "crowdsource", "build-override"}
CONF       = {"low", "medium", "high"}
ID_RE      = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE_RE    = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def check_price(price, where, errs, allow_number=False):
    if allow_number and isinstance(price, (int, float)):
        return
    if not isinstance(price, dict):
        errs.append(f"{where}: price must be an object"); return
    if not isinstance(price.get("value"), (int, float)):
        errs.append(f"{where}: price.value must be a number")
    if not isinstance(price.get("estimated"), bool):
        errs.append(f"{where}: price.estimated must be a bool")
    srcs = price.get("sources")
    if not isinstance(srcs, list) or not srcs:
        errs.append(f"{where}: price.sources must be a non-empty list"); return
    for j, s in enumerate(srcs):
        sw = f"{where}.sources[{j}]"
        if not isinstance(s.get("value"), (int, float)):
            errs.append(f"{sw}: source.value must be a number")
        if not DATE_RE.match(str(s.get("sourced_at", ""))):
            errs.append(f"{sw}: sourced_at must be YYYY-MM-DD (got {s.get('sourced_at')!r})")
        if s.get("method") not in METHODS:
            errs.append(f"{sw}: method {s.get('method')!r} not in {sorted(METHODS)}")
        if s.get("confidence") not in CONF:
            errs.append(f"{sw}: confidence {s.get('confidence')!r} not in {sorted(CONF)}")

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog.json")
    try:
        cat = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        print(f"FATAL: cannot parse {path}: {e}"); sys.exit(2)

    errs = []
    if not isinstance(cat.get("schema_version"), int):
        errs.append("schema_version must be an integer")

    ids = set()
    for i, p in enumerate(cat.get("parts", [])):
        w = f"parts[{i}]({p.get('id','?')})"
        pid = p.get("id")
        if not isinstance(pid, str) or not ID_RE.match(pid or ""):
            errs.append(f"{w}: id must match {ID_RE.pattern}")
        elif pid in ids:
            errs.append(f"{w}: duplicate id (ids are append-only — never reuse)")
        else:
            ids.add(pid)
        if p.get("category") not in CATEGORIES:
            errs.append(f"{w}: category {p.get('category')!r} not in {sorted(CATEGORIES)}")
        if not p.get("name"):
            errs.append(f"{w}: name required")
        for k in (p.get("specs") or {}):
            if k not in SPEC_VOCAB:
                errs.append(f"{w}: spec key {k!r} not in vocab {sorted(SPEC_VOCAB)}")
        check_price(p.get("price"), w, errs)

    build_ids = set()
    for i, b in enumerate(cat.get("builds", [])):
        w = f"builds[{i}]({b.get('id','?')})"
        bid = b.get("id")
        if not isinstance(bid, str) or not ID_RE.match(bid or ""):
            errs.append(f"{w}: id must match {ID_RE.pattern}")
        elif bid in build_ids:
            errs.append(f"{w}: duplicate build id")
        else:
            build_ids.add(bid)
        items = b.get("items")
        if not isinstance(items, list) or not items:
            errs.append(f"{w}: items must be a non-empty list"); continue
        for j, it in enumerate(items):
            iw = f"{w}.items[{j}]"
            ref = it.get("part_id")
            if ref not in ids:
                errs.append(f"{iw}: part_id {ref!r} does not resolve to any part (id drift)")
            if not isinstance(it.get("qty"), (int, float)):
                errs.append(f"{iw}: qty must be a number")
            if "price_override" in it:
                check_price(it["price_override"], f"{iw}.price_override", errs, allow_number=True)

    if errs:
        print(f"INVALID — {len(errs)} problem(s) in {os.path.basename(path)}:")
        for e in errs:
            print(f"  ✗ {e}")
        sys.exit(1)
    print(f"VALID — {os.path.basename(path)}: {len(ids)} parts, {len(build_ids)} builds, all ids resolve.")

if __name__ == "__main__":
    main()
