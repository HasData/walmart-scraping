"""How much data each of the three sources yields on the same Walmart product card.

Collects ~100 product URLs from five search pages, fetches every card once through
the Web Scraping API (residential US exit, no JS rendering: the probe showed
datacenter exits and plain requests both get the challenge page), and extracts the
same card three ways offline:

  selectors   the five fields the article's Way 1 teaches (h1/span itemprop, a
              ratingCount, span.rating-number, meta og:image)
  json-ld     every application/ld+json script; a Product-type schema when present,
              its leaf-field count and the five core fields
  __NEXT_DATA__  props.pageProps.initialData.data.product, its leaf-field count and
              the same five core fields

One request at a time with a delay and a 429/challenge retry. Writes
results/sources.json incrementally, one row per card, so a restart resumes.
"""
import json
import os
import pathlib
import sys
import time

import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
S = pathlib.Path(__file__).resolve().parent.parent / "study"
S.mkdir(parents=True, exist_ok=True)
OUT = S / "sources.json"
KEY = os.environ["HASDATA_API_KEY"]
QUERIES = ["laptop", "coffee maker", "running shoes", "lego", "air fryer",
           "headphones", "vacuum cleaner", "office chair", "backpack", "toaster",
           "bluetooth speaker", "winter jacket", "board games", "desk lamp",
           "protein powder", "yoga mat", "microwave", "kids bike"]
PER_QUERY = 15
TARGET = 100


def api_fetch(url, tries=3):
    for attempt in range(tries):
        try:
            r = requests.post("https://api.hasdata.com/scrape/web",
                              headers={"x-api-key": KEY, "Content-Type": "application/json"},
                              json={"url": url, "proxyType": "residential", "proxyCountry": "US",
                                    "outputFormat": ["html"]}, timeout=120)
        except requests.RequestException:
            time.sleep(6)
            continue
        if r.status_code == 429:
            time.sleep(8)
            continue
        html = r.text
        if "Robot or human" in html and attempt < tries - 1:
            time.sleep(3)
            continue
        return html
    return html if "html" in dir() else ""


def leaves(o):
    if isinstance(o, dict):
        return sum(leaves(v) for v in o.values())
    if isinstance(o, list):
        return sum(leaves(v) for v in o)
    return 1


def extract(html):
    soup = BeautifulSoup(html, "lxml")
    row = {"challenge": "Robot or human" in html, "bytes": len(html)}

    # Way 1: the article's selectors
    sel = {}
    t = soup.find("h1", attrs={"itemprop": "name"})
    sel["title"] = bool(t and t.get_text(strip=True))
    p = soup.find("span", attrs={"itemprop": "price"})
    sel["price"] = bool(p and p.get_text(strip=True))
    rv = soup.find("a", attrs={"itemprop": "ratingCount"})
    sel["reviews"] = bool(rv and rv.get_text(strip=True))
    rt = soup.find("span", attrs={"class": "rating-number"})
    sel["rating"] = bool(rt and rt.get_text(strip=True))
    im = soup.find("meta", property="og:image")
    sel["image"] = bool(im and im.get("content"))
    row["selectors"] = sel

    # Way 2: JSON-LD Product schema
    ld = {"present": False, "leaf_fields": 0, "core": {}}
    for sc in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            d = json.loads(sc.text)
        except ValueError:
            continue
        cands = d if isinstance(d, list) else [d]
        for c in cands:
            if isinstance(c, dict) and c.get("@type") == "Product":
                offers = c.get("offers") or {}
                agg = c.get("aggregateRating") or {}
                ld = {"present": True, "leaf_fields": leaves(c), "core": {
                    "title": bool(c.get("name")), "price": offers.get("price") is not None,
                    "reviews": agg.get("reviewCount") is not None,
                    "rating": agg.get("ratingValue") is not None, "image": bool(c.get("image")),
                }}
                break
        if ld["present"]:
            break
    row["json_ld"] = ld

    # __NEXT_DATA__
    nd = {"present": False, "leaf_fields": 0, "core": {}}
    tag = soup.find("script", id="__NEXT_DATA__")
    if tag:
        try:
            prod = (json.loads(tag.text).get("props", {}).get("pageProps", {})
                    .get("initialData", {}).get("data", {}).get("product"))
        except ValueError:
            prod = None
        if prod:
            price = (prod.get("priceInfo") or {}).get("currentPrice") or {}
            nd = {"present": True, "leaf_fields": leaves(prod), "core": {
                "title": bool(prod.get("name")), "price": price.get("price") is not None,
                "reviews": prod.get("numberOfReviews") is not None,
                "rating": prod.get("averageRating") is not None,
                "image": bool((prod.get("imageInfo") or {}).get("thumbnailUrl")),
            }}
    row["next_data"] = nd
    return row


rows = []
if OUT.exists():
    saved = json.loads(OUT.read_text(encoding="utf-8"))
    rows = saved.get("rows", [])
done = {r["url"] for r in rows}

urls_path = S / "card_urls.json"
if urls_path.exists():
    urls = json.loads(urls_path.read_text(encoding="utf-8"))
else:
    urls = []
    for q in QUERIES:
        html = api_fetch(f"https://www.walmart.com/search?q={q}")
        soup = BeautifulSoup(html, "lxml")
        links = []
        # the search page is Next.js too: its own __NEXT_DATA__ carries the result items
        tag = soup.find("script", id="__NEXT_DATA__")
        if tag:
            try:
                sr = (json.loads(tag.text).get("props", {}).get("pageProps", {})
                      .get("initialData", {}).get("searchResult", {}))
                for stack in sr.get("itemStacks", []):
                    for item in stack.get("items", []):
                        cu = item.get("canonicalUrl")
                        if cu and "/ip/" in cu:
                            links.append("https://www.walmart.com" + cu.split("?")[0])
            except ValueError:
                pass
        for a in soup.find_all("a", href=True):
            href = a["href"].split("?")[0]
            if "/ip/" in href:
                links.append("https://www.walmart.com" + href if href.startswith("/") else href)
        seen = list(dict.fromkeys(links))[:PER_QUERY]
        print(f"search '{q}': {len(seen)} product links")
        urls += seen
        time.sleep(1)
    urls = list(dict.fromkeys(urls))[:TARGET]
    urls_path.write_text(json.dumps(urls, indent=1), encoding="utf-8")
print(f"cards: {len(urls)}, done: {len(done)}")

for url in urls:
    if url in done:
        continue
    html = api_fetch(url)
    row = {"url": url, **extract(html)}
    rows.append(row)
    OUT.write_text(json.dumps({"rows": rows}, ensure_ascii=False), encoding="utf-8")
    n = len(rows)
    if n % 10 == 0:
        print(f"{n}/{len(urls)} | last: nd={row['next_data']['present']} ld={row['json_ld']['present']} "
              f"sel={sum(row['selectors'].values())}/5 challenge={row['challenge']}")
    time.sleep(1.0)

# aggregate
ok = [r for r in rows if not r["challenge"]]
agg = {
    "cards_fetched": len(rows),
    "challenges": sum(r["challenge"] for r in rows),
    "clean_cards": len(ok),
    "selectors_core_median": sorted(sum(r["selectors"].values()) for r in ok)[len(ok) // 2] if ok else None,
    "selectors_field_rates": {f: round(sum(r["selectors"][f] for r in ok) / len(ok), 3) for f in
                              ("title", "price", "reviews", "rating", "image")} if ok else {},
    "json_ld_present": sum(r["json_ld"]["present"] for r in ok),
    "json_ld_leaf_median": (lambda v: sorted(v)[len(v) // 2] if v else 0)([r["json_ld"]["leaf_fields"] for r in ok if r["json_ld"]["present"]]),
    "next_data_present": sum(r["next_data"]["present"] for r in ok),
    "next_data_leaf_median": (lambda v: sorted(v)[len(v) // 2] if v else 0)([r["next_data"]["leaf_fields"] for r in ok if r["next_data"]["present"]]),
}
data = {"aggregate": agg, "rows": rows}
OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(agg, indent=1))
print("saved sources.json")
