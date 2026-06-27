#!/usr/bin/env python3
"""
build-index — generate index.html: ONE app with a dropdown to switch between all
reference builds. Reuses build.py's helpers + the same template (the template shows
the build selector automatically when given more than one build).

Usage:  python3 build-index.py
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as B  # build.py in the same directory

HERE = os.path.dirname(os.path.abspath(__file__))

# dropdown order + short labels (falls back to the build title)
ORDER = [
    "budget-1x3090-starter",
    "g2-4x3090-workstation",
    "8x3090-192gb",
    "highend-4x5090-threadripper",
]
MENU = {
    "budget-1x3090-starter":        "💻  Budget 1× RTX 3090  (~$2k)",
    "g2-4x3090-workstation":        "🖥️  G2 — 4× RTX 3090  (96GB)",
    "8x3090-192gb":                 "🗄️  8× RTX 3090 Server  (192GB)",
    "highend-4x5090-threadripper":  "🔥  4× RTX 5090 High-End  (128GB)",
}

def main():
    builds = []
    for slug in ORDER:
        path = os.path.join(HERE, "builds", slug + ".json")
        if not os.path.exists(path):
            continue
        spec = json.load(open(path, encoding="utf-8"))
        rec = B.build_record(spec, slug)
        rec["menu"] = MENU.get(slug, rec["title"])
        builds.append(rec)
    # include any builds not in ORDER, appended
    seen = {b["slug"] for b in builds}
    import glob
    for path in sorted(glob.glob(os.path.join(HERE, "builds", "*.json"))):
        slug = os.path.basename(path)[:-5]
        if slug in seen:
            continue
        spec = json.load(open(path, encoding="utf-8"))
        builds.append(B.build_record(spec, slug))

    tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    repl = {
        "__TITLE__":       "GPU Build Picker",
        "__SUBTITLE__":    "Pick a reference build above, or edit any line. Live cost + capability score + a machine that builds itself.",
        "__BUILDS_JSON__": json.dumps(builds, ensure_ascii=False, indent=2),
    }
    for k, v in repl.items():
        tpl = tpl.replace(k, v)
    open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(tpl)
    print(f"wrote index.html — {len(builds)} builds: " + ", ".join(b["slug"] for b in builds))

if __name__ == "__main__":
    main()
