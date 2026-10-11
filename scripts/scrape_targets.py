#!/usr/bin/env python3
"""SeedFinder Phase 1 — scrape the 31 priority cultivars (polite, 1 req / ~2.5s).
Output: targets.json in the script's directory.
"""
import json, os, re, time, random
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

# (display_name, primary_slug, primary_breeder, alternates[(slug, breeder)])
TARGETS = [
    ("Permanent Marker", "permanent-marker", "seed-junky-genetics", []),
    ("Jealousy", "jealousy", "barneys-farm", [("jealousy", "seed-junky-genetics")]),
    ("RS11", "rs11", "barneys-farm", [("rs-11", "clone-only-strains")]),
    ("Rainbow Belts", "rainbow-belts", "archive-seed-bank", [("rainbow-belts", "zamnesia")]),
    ("Lemon Cherry Gelato", "lemon-cherry-gelato", "barneys-farm", [("lemon-cherry-gelato", "unknown-or-legendary")]),
    ("Super Boof", "super-boof", "royal-queen-seeds", [("super-boof", "growers-choice")]),
    ("Blue Lobster", "blue-lobster", "compound-genetics", []),
    ("Gary Payton", "gary-payton", "cookie-fam-genetics", [("gary-payton", "barneys-farm")]),
    ("Zoap", "zoap", "barneys-farm", [("zoap", "unknown-or-legendary")]),
    ("Red Pop", "red-pop", "exotic-genetix", []),
    ("Georgia Pie", "georgia-pie", "seed-junky-genetics", []),
    ("Devil Driver", "devil-driver", "tiki-madman", [("devil-driver", "strain-station-seeds")]),
    ("Honey Banana", "honey-bananas", "elemental-seeds", []),  # SeedFinder names it "Honey Bananas"
    ("GMO", "gmo", "barneys-farm", [("gmo", "apothecary-genetics")]),
    ("Don Mega", "the-don-mega", "solfire-gardens", []),  # SeedFinder: "The Don Mega"
    ("Dante's Inferno", "dantes-inferno", "tiki-madman", [("dantes-inferno", "clearwater-genetics")]),
    ("Ice Cream Cake", "ice-cream-cake", "seed-junky-genetics", []),
    ("Jokerz", "jokerz", "compound-genetics", []),
    ("The Soap", "the-soap", "seed-junky-genetics", []),
    ("Cereal Milk", "cereal-milk", "cookie-fam-genetics", []),
    ("Runtz", "runtz", "barneys-farm", [("runtz", "humboldt-seed-organisation")]),
    ("White Runtz", "white-runtz", "cookie-fam-genetics", [("white-runtz", "clone-only-strains")]),
    ("Pink Runtz", "pink-runtz", "clone-only-strains", [("pink-runtz", "copycat-genetix")]),
    ("Rainbow Sherb", "rainbow-sherb", "maui-jane-seed-co", [("rainbow-sherbet", "barneys-farm")]),
    ("Sherbanger", "sherbanger", "seedsman", [("sherbanger", "unknown-or-legendary")]),
    ("Grape Gas", "grape-gas", "twenty-20-genetics", [("grape-gas", "true-canna-genetics")]),
    ("Kush Mints", "kush-mints", "seed-junky-genetics", []),
    ("Cap Junky", "cap-junky", "seed-junky-genetics", []),
    ("MAC V2", "mac-v2", "capulator", []),
    ("Alien Mints", "alien-mints", "alienlabs", []),
    ("Compound Z", "compound-z", "compound-genetics", []),
]

def fetch(url, sess, retries=4):
    for attempt in range(retries):
        try:
            r = sess.get(url, timeout=30)
            if r.status_code == 429:
                wait = 15 * (attempt + 1)
                print(f"  429 -> sleeping {wait}s", flush=True)
                time.sleep(wait)
                continue
            if r.status_code in (403, 503):
                print(f"  HTTP {r.status_code} (blocked?) -> backoff", flush=True)
                time.sleep(20 * (attempt + 1))
                continue
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            print(f"  attempt {attempt+1} failed: {e}", flush=True)
            time.sleep(3 * (attempt + 1))
    return None

def clean(s):
    s = re.sub(r'<[^>]+>', ' ', s or '')
    s = re.sub(r'\s+', ' ', s)
    return s.strip(' |,').strip()

def parse(html, url):
    text = re.sub(r'<script.*?</script>', '', html, flags=re.S)
    text = re.sub(r'<style.*?</style>', '', text, flags=re.S)
    out = {"source_url": url}

    # name + breeder from title
    m = re.search(r'<title>(.*?)\s*\(.*?\)\s*::', html)
    out["name"] = clean(m.group(1)) if m else None
    m = re.search(r'<title>.*?\((.*?)\)\s*::', html)
    out["breeder"] = clean(m.group(1)) if m else None

    # Basic infos paragraph
    i = text.find('>Basic infos<')
    basic_raw = ""
    if i != -1:
        j = text.find('Description</h2>', i)
        basic_raw = clean(text[i:j if j != -1 else i + 4000])
    out["basic_infos_raw"] = basic_raw[:600] or None

    mt = re.search(r'is an? (.+?) from', basic_raw)
    out["type"] = mt.group(1).strip() if mt else None
    if 'indoors and outdoors' in basic_raw:
        out["cultivation"] = "indoor+outdoor"
    elif 'indoors' in basic_raw:
        out["cultivation"] = "indoor"
    elif 'outdoors' in basic_raw:
        out["cultivation"] = "outdoor"
    else:
        out["cultivation"] = None
    mf = re.search(r'flowering time of [±~]?(\d+)\s*days', basic_raw)
    out["flowering_days"] = int(mf.group(1)) if mf else None
    if 'never available as feminized' in basic_raw:
        out["seed_type"] = "regular (never feminized)"
    elif 'only available as feminized' in basic_raw:
        out["seed_type"] = "feminized only"
    elif 'autoflowering' in basic_raw.lower():
        out["seed_type"] = "autoflowering"
    else:
        out["seed_type"] = None

    # Lineage — robust: take the HTML between the strain's own "»»»" link and the nested <ul
    out["parent_1"] = out["parent_2"] = None
    out["parent_links"] = []
    out["lineage_raw"] = None
    out["extended_tree"] = []
    li = text.find('id="lineage"')
    if li != -1:
        seg = text[li:li + 40000]
        m = re.search(r'»»?\s*</a>(.*?)<ul', seg, re.S)
        if m:
            cross_html = m.group(1)
            links = re.findall(r'<a[^>]*href="([^"]*?/strain-info/[^"]+)"[^>]*>([^<]+)</a>', cross_html)
            seen = set()
            for url, name in links:
                name = clean(name).replace('»»»', '').strip()
                if url not in seen and name:
                    seen.add(url)
                    out["parent_links"].append({"name": name, "url": url})
            cross_text = re.sub(r'\s+', ' ', clean(cross_html))
            cross_text = re.sub(r'\(\s+', '(', cross_text)
            cross_text = re.sub(r'\s+\)', ')', cross_text)
            out["lineage_raw"] = cross_text or None
            # split into parent_1 / parent_2 (parent_1 may be a nested cross in parentheses)
            pm = re.match(r'^\((.+)\)\s*x\s*(.+)$', cross_text)
            if pm:
                out["parent_1"], out["parent_2"] = f"({pm.group(1).strip()})", pm.group(2).strip()
            else:
                parts = [p.strip() for p in re.split(r'\s+x\s+', cross_text) if p.strip()]
                if len(parts) >= 2:
                    out["parent_1"], out["parent_2"] = parts[0], parts[1]
                elif len(parts) == 1:
                    out["parent_1"] = parts[0]
        # extended tree: consecutive strain links separated by a bare "x"
        strain_links = []
        for lm in re.finditer(r'<a[^>]*href="([^"]*?/strain-info/[^"]+)"[^>]*>([^<]+)</a>', seg):
            nm = clean(lm.group(2)).replace('»»»', '').strip()
            if nm:
                strain_links.append((lm.start(), lm.end(), nm))
        seen_pairs = set()
        for k in range(len(strain_links) - 1):
            between = clean(seg[strain_links[k][1]:strain_links[k + 1][0]]).replace('»»»', '').strip()
            if between == 'x':
                a, b = strain_links[k][2], strain_links[k + 1][2]
                key = (a.lower(), b.lower())
                if key not in seen_pairs:
                    seen_pairs.add(key)
                    out["extended_tree"].append({"a": a, "b": b})

    # Degustation: effect / aroma / taste
    for key, label in [("effect", "Effect/Effectiveness"), ("aroma", "Smell / Aroma"), ("taste", "Taste")]:
        m = re.search(re.escape(label) + r'(.*?)(?:Smell / Aroma|Taste|The Soap Gallery|Gallery|$)', text, re.S)
        val = clean(m.group(1)) if m else ""
        out[f"{key}_data"] = None if ('No data available' in val or not val) else val[:400]

    # Awards
    am = re.search(r'Awards</h3>(.*?)</section>', text, re.S)
    out["awards"] = clean(am.group(1))[:300] if am and 'No ' not in clean(am.group(1))[:10] else None

    # Breeder description (first 800 chars)
    dm = re.search(r'Description</h2>(.*?)<h[23]', text, re.S)
    out["breeder_description"] = clean(dm.group(1))[:800] if dm else None

    return out

def score(rec):
    # completeness heuristic: lineage + flowering + type + degustation
    s = 0
    if rec.get("parent_1"): s += 3
    if rec.get("flowering_days"): s += 2
    if rec.get("type"): s += 1
    if rec.get("effect_data") or rec.get("aroma_data"): s += 1
    if rec.get("breeder_description"): s += 1
    return s

def main():
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    results = []
    for name, slug, breeder, alts in TARGETS:
        print(f"== {name}", flush=True)
        candidates = [(slug, breeder)] + alts
        best, best_score = None, -1
        tried = []
        for cslug, cbreeder in candidates:
            url = f"https://seedfinder.eu/en/strain-info/{cslug}/{cbreeder}"
            html = fetch(url, sess)
            tried.append(url)
            time.sleep(2.5 + random.random())
            if not html:
                print(f"  miss: {url}", flush=True)
                continue
            rec = parse(html, url)
            rec["target_name"] = name
            rec["duplicates_tried"] = tried.copy()
            sc = score(rec)
            print(f"  hit: {url} score={sc} parents={rec['parent_1']} x {rec['parent_2']} flowering={rec['flowering_days']}", flush=True)
            if sc > best_score:
                best, best_score = rec, sc
            if sc >= 6:
                break  # good enough
        if best:
            results.append(best)
        else:
            results.append({"target_name": name, "name": None, "source_url": None,
                            "status": "not_found", "duplicates_tried": tried})
    out_path = os.path.join(BASE, "targets.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    found = sum(1 for r in results if r.get("name"))
    print(f"\nDONE: {found}/{len(results)} found -> {out_path}")

if __name__ == "__main__":
    main()
