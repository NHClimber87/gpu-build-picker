#!/usr/bin/env python3
"""
ingest-quote — parse a community price-quote issue, validate it, and (if corroborated)
fold it into catalog.json. Driven by .github/workflows/price-quote.yml on a price-quote
labeled issue. Zero standing backend — the browser opens a prefilled issue, this runs on
the labeled-issue event.

Pipeline:
  1. parse the fenced ```quote block (part_id / price / url / sourced_at) from ISSUE_BODY
  2. validate: known part_id, price in the per-category sanity band AND within ±40% of the
     current price, URL on the domain allowlist
  3. append the quote to data/quotes.jsonl (always — even rejected ones, as an audit trail)
  4. if valid, add a crowdsource SOURCE to the part's price record. A lone quote is ADVISORY
     (confidence low, value unchanged). Once a 2nd in-band quote corroborates it, the
     corroborating quotes' median nudges the headline value (confidence medium).

HARD RULES: never fabricate (a quote is real, attributed data); specs/ids never touched;
out-of-band/malformed quotes change nothing. Verdict + message go to $GITHUB_OUTPUT so the
workflow can comment, label accepted/rejected, and close.

Usage (workflow): ISSUE_BODY="..." ISSUE_NUMBER=NN python3 scripts/ingest-quote.py
"""
import json, os, re, sys, datetime

HERE    = os.path.dirname(os.path.abspath(__file__))
ROOT    = os.path.normpath(os.path.join(HERE, ".."))
CATALOG = os.path.join(ROOT, "catalog.json")
QUOTES  = os.path.join(ROOT, "data", "quotes.jsonl")

ALLOW_DOMAINS = {
    "ebay.com", "amazon.com", "newegg.com", "neweggbusiness.com", "microcenter.com",
    "bestbuy.com", "bhphotovideo.com", "theserverstore.com", "directmacro.com",
    "bestvaluegpu.com", "gpupoet.com", "servethehome.com", "b-stock.com", "provantage.com",
}
FLOOR_CEIL = {"gpu": (200, 20000), "cpu": (40, 12000), "motherboard": (50, 3000),
              "ram": (20, 12000), "psu": (30, 1500), "storage": (20, 3000),
              "case": (20, 8000), "accessory": (1, 1000)}
BAND_FRAC = 0.40       # a quote must be within ±40% of the current price to be in-band
CORROB_DAYS = 120      # corroborating quotes must be this recent
MAX_CROWD_SRC = 4      # cap crowdsource sources kept on a record

def out(verdict, message, applied=False):
    p = os.environ.get("GITHUB_OUTPUT")
    if p:
        with open(p, "a") as f:
            f.write(f"verdict={verdict}\n")
            f.write(f"applied={'true' if applied else 'false'}\n")
            # message can be multiline -> heredoc form
            f.write("message<<EOF\n" + message + "\nEOF\n")
    print(f"[{verdict}] {message}")

def parse_quote(body):
    m = re.search(r"```quote\s*(.*?)```", body or "", re.S)
    blob = m.group(1) if m else (body or "")
    fields = {}
    for line in blob.splitlines():
        mm = re.match(r"\s*([a-z_]+)\s*:\s*(.+?)\s*$", line)
        if mm:
            fields[mm.group(1)] = mm.group(2)
    return fields

def domain_of(url):
    m = re.match(r"https?://([^/]+)/?", url or "")
    if not m:
        return None
    host = m.group(1).lower().split(":")[0]
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host

def median(xs):
    s = sorted(xs); n = len(s)
    return None if not n else (s[n//2] if n % 2 else (s[n//2-1]+s[n//2])/2)

def main():
    body = os.environ.get("ISSUE_BODY", "")
    issue = os.environ.get("ISSUE_NUMBER", "")
    today = datetime.date.today().isoformat()
    cat = json.load(open(CATALOG, encoding="utf-8"))
    parts = {p["id"]: p for p in cat.get("parts", [])}

    f = parse_quote(body)
    pid, raw_price, url, sourced = f.get("part_id"), f.get("price"), f.get("url"), f.get("sourced_at")

    # --- validate ---
    reason, accepted = None, False
    try:
        price = float(re.sub(r"[^0-9.]", "", raw_price or "")) if raw_price else 0
    except ValueError:
        price = 0
    part = parts.get(pid)
    dom = domain_of(url)

    if not pid or not part:
        reason = f"unknown part_id {pid!r} — must be one of the catalog ids"
    elif price <= 0:
        reason = f"unparseable/zero price {raw_price!r}"
    else:
        floor, ceil = FLOOR_CEIL.get(part["category"], (1, 10**7))
        cur = float((part.get("price") or {}).get("value", 0) or 0)
        if not (floor <= price <= ceil):
            reason = f"${price:,.0f} outside the {part['category']} sanity band (${floor:,}-${ceil:,})"
        elif cur and abs(price - cur) > BAND_FRAC * cur:
            reason = f"${price:,.0f} is >{int(BAND_FRAC*100)}% off the current ${cur:,.0f} — needs review, not auto-applied"
        elif not dom or dom not in ALLOW_DOMAINS:
            reason = f"URL domain {dom!r} not on the allowlist"
        else:
            accepted = True

    rec = {"part_id": pid, "price": price, "url": url, "domain": dom,
           "sourced_at": sourced or today, "ingested_at": today,
           "accepted": accepted, "reason": reason, "issue": issue}

    os.makedirs(os.path.dirname(QUOTES), exist_ok=True)
    with open(QUOTES, "a", encoding="utf-8") as q:
        q.write(json.dumps(rec, ensure_ascii=False) + "\n")

    if not accepted:
        out("rejected", f"Quote not applied: {reason}. Stored in quotes.jsonl as an audit record. "
                        f"Fix the fields and reopen if this was a mistake.")
        return

    # --- corroboration: count prior accepted in-band quotes for this part ---
    prior = []
    if os.path.exists(QUOTES):
        for line in open(QUOTES, encoding="utf-8"):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("part_id") == pid and r.get("accepted") and r.get("issue") != issue:
                if abs(float(r["price"]) - price) <= BAND_FRAC * price:
                    try:
                        age = (datetime.date.fromisoformat(today) -
                               datetime.date.fromisoformat(r.get("ingested_at", today))).days
                    except Exception:
                        age = 0
                    if age <= CORROB_DAYS:
                        prior.append(float(r["price"]))
    corroborated = len(prior) >= 1     # this quote + >=1 prior in-band = corroborated

    # --- fold into the catalog price record ---
    price_rec = part.setdefault("price", {"value": price, "estimated": False, "sources": []})
    srcs = price_rec.setdefault("sources", [])
    srcs.append({"url": url, "value": price, "sourced_at": sourced or today,
                 "method": "crowdsource", "confidence": "medium" if corroborated else "low"})
    # keep at most MAX_CROWD_SRC crowdsource sources (newest), preserve non-crowdsource sources
    crowd = [s for s in srcs if s.get("method") == "crowdsource"][-MAX_CROWD_SRC:]
    price_rec["sources"] = [s for s in srcs if s.get("method") != "crowdsource"] + crowd
    price_rec["estimated"] = False

    if corroborated:
        price_rec["value"] = round(median(prior + [price]))
        msg = (f"✅ Accepted **and corroborated** ({len(prior)+1} in-band quotes). "
               f"`{pid}` price nudged to **${price_rec['value']:,}** (median of corroborating quotes). Thank you!")
        applied_strong = True
    else:
        msg = (f"✅ Accepted as an **advisory** quote for `{pid}` (${price:,.0f} via {dom}). "
               f"It's added as a low-confidence source; the headline price changes once a 2nd "
               f"in-band quote corroborates it.")
        applied_strong = True

    json.dump(cat, open(CATALOG, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    open(CATALOG, "a").write("\n")
    out("accepted", msg, applied=applied_strong)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        out("error", f"ingest crashed: {type(e).__name__}: {e}")
        # don't fail the workflow — let it comment/close gracefully
        sys.exit(0)
