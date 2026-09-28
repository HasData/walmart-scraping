import os
import urllib.parse

import requests
from bs4 import BeautifulSoup

API_KEY = os.environ["HASDATA_API_KEY"]

with open("keywords.txt") as f:
    keywords = [line.strip() for line in f if line.strip()]

product_links = []
related_searches = []

for keyword in keywords:
    search_url = "https://www.walmart.com/search?q=" + urllib.parse.quote(keyword)
    r = requests.post(
        "https://api.hasdata.com/scrape/web",
        headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
        json={"url": search_url, "proxyType": "residential", "proxyCountry": "US",
              "outputFormat": ["html"]},
        timeout=120,
    )
    soup = BeautifulSoup(r.text, "lxml")

    for a in soup.find_all("a", href=True):
        href = a["href"].split("?")[0]
        if "/ip/" in href:
            full = "https://www.walmart.com" + href if href.startswith("/") else href
            if full not in product_links:
                product_links.append(full)

    carousel = soup.find("ul", {"data-testid": "carousel-container"})
    if carousel:
        related_searches += [li.get_text(strip=True) for li in carousel.find_all("li")]

with open("links.csv", "w") as f:
    f.write("\n".join(product_links))

print(len(product_links), "product links,", len(related_searches), "related searches")
