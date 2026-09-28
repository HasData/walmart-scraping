import csv
import json
import os

import requests
from bs4 import BeautifulSoup

API_KEY = os.environ["HASDATA_API_KEY"]

def fetch(url):
    # residential exit required: Walmart serves the challenge to datacenter IPs
    r = requests.post(
        "https://api.hasdata.com/scrape/web",
        headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        json={"url": url, "proxyType": "residential", "proxyCountry": "US",
              "outputFormat": ["html"]},
        timeout=120,
    )
    return r.text

def parse_card(html):
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("script", id="__NEXT_DATA__")
    product = (json.loads(tag.text)["props"]["pageProps"]
               ["initialData"]["data"]["product"])
    price = (product.get("priceInfo") or {}).get("currentPrice") or {}
    return {
        "title": product.get("name"),
        "price": price.get("price"),
        "rating": product.get("averageRating"),
        "reviews": product.get("numberOfReviews"),
        "image": (product.get("imageInfo") or {}).get("thumbnailUrl"),
    }

with open("links.csv") as f:
    links = [line.strip() for line in f if line.strip()]

with open("result.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["title", "price", "rating", "reviews", "image"])
    writer.writeheader()
    for link in links:
        try:
            writer.writerow(parse_card(fetch(link)))
        except (KeyError, TypeError, ValueError, AttributeError) as e:
            print(f"skipped {link}: {e}")

print(f"done, {len(links)} links processed")
