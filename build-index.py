#!/usr/bin/env python3
"""
build-index — generate index.html: ONE app with a dropdown to switch between all
reference builds. Thin wrapper around build.py --index (the template shows the build
selector automatically when given more than one build).

Usage:  python3 build-index.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build as B

def main():
    cat = B.load_catalog()
    out = os.path.join(B.HERE, "index.html")
    title = "GPU Build Picker"
    subtitle = "Pick a reference build above, or edit any line. Live cost + provenance + capability score + a machine that builds itself."
    open(out, "w", encoding="utf-8").write(B.render(cat, title, subtitle, None))
    print(f"wrote index.html — {len(cat.get('builds',[]))} builds: " + ", ".join(b["id"] for b in cat.get("builds", [])))

if __name__ == "__main__":
    main()
