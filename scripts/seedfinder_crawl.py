#!/usr/bin/env python3
"""SeedFinder Phase 2 crawler — sitemap-based, resumable, polite.

Usage:
    python3 seedfinder_crawl.py [--urls FILE] [--limit N] [--delay SEC]

- Reads canonical strain URLs (one per line), skips pages already saved in pages/.
- Saves one JSON per page: pages/<slug>__<breeder>.json
- Polite: delay between requests (default 2.5s + jitter), neutral UA (never GPTBot),
  retries with backoff on 429/503/403; aborts loudly on repeated blocks.
- Resume-safe: re-running continues where it stopped.
"""
import argparse, json, os, re, sys, time, random
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(BASE, "pages")
os.makedirs(PAGES, exist_ok=True)
sys.path.insert(0, BASE)
from scrape_targets import parse  # reuse the Phase-1 parser

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

def page_path(url):
    m = re.search(r'/strain-info/([^/]+)/([^/]+)/?$', url)
    slug = m.group(1) if m else "unknown"
    breeder = m.group(2) if m else "unknown"
    safe = re.sub(r'[^a-z0-9_-]', '_', f"{slug}__{breeder}".lower())
    return os.path.join(PAGES, safe + ".json")

def fetch(url, sess):
    for attempt in range(5):
        try:
            r = sess.get(url, timeout=30)
            if r.status_code == 429:
                wait = 20 * (attempt + 1)
                print(f"  429 -> backoff {wait}s", flush=True)
                time.sleep(wait)
                continue
            if r.status_code in (403, 503):
                wait = 30 * (attempt + 1)
                print(f"  HTTP {r.status_code} -> backoff {wait}s", flush=True)
                time.sleep(wait)
                continue
            if r.status_code == 404:
                return "NOT_FOUND"
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            # Throttle probable (timeouts en rafale) : backoff exponentiel long
            # pour laisser le rate-limit retomber au lieu d'abandonner la page.
            wait = min(30 * (2 ** attempt), 480)
            print(f"  attempt {attempt+1}: {e} -> backoff {wait}s", flush=True)
            time.sleep(wait)
    return "BLOCKED"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", default=os.path.join(BASE, "en_strain_canonical.txt"))
    ap.add_argument("--limit", type=int, default=0, help="0 = no limit")
    ap.add_argument("--delay", type=float, default=2.5)
    args = ap.parse_args()

    urls = [u.strip() for u in open(args.urls, encoding="utf-8") if u.strip().startswith("http")]
    pending = [u for u in urls if not os.path.exists(page_path(u))]
    todo = pending[:args.limit] if args.limit else pending
    print(f"total={len(urls)} pending={len(pending)} todo_this_run={len(todo)}", flush=True)

    sess = requests.Session()
    sess.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    done, failed, blocked = 0, [], 0
    for n, url in enumerate(todo, 1):
        res = fetch(url, sess)
        if res == "BLOCKED":
            blocked += 1
            print(f"[{n}/{len(todo)}] BLOCKED repeatedly -> STOPPING: {url}", flush=True)
            break
        if res == "NOT_FOUND":
            failed.append(url)
        else:
            try:
                rec = parse(res, url)
                with open(page_path(url), "w", encoding="utf-8") as f:
                    json.dump(rec, f, ensure_ascii=False, indent=1)
                done += 1
            except Exception as e:
                print(f"[{n}] parse error {url}: {e}", flush=True)
                failed.append(url)
        if n % 20 == 0:
            print(f"[{n}/{len(todo)}] done={done} failed={len(failed)}", flush=True)
        time.sleep(args.delay + random.random())
    print(f"FINISHED: done={done} failed={len(failed)} blocked_stop={blocked}")
    if failed:
        with open(os.path.join(BASE, "crawl_failed.txt"), "a", encoding="utf-8") as f:
            f.write("\n".join(failed) + "\n")

if __name__ == "__main__":
    main()
