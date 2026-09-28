import os

import requests
from bs4 import BeautifulSoup

API_KEY = os.environ["HASDATA_API_KEY"]

r = requests.post(
    "https://api.hasdata.com/scrape/web",
    headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
    json={"url": "https://www.walmart.com/ip/771229626",
          "proxyType": "residential", "proxyCountry": "US", "outputFormat": ["html"]},
    timeout=120,
)
soup = BeautifulSoup(r.text, "lxml")

title = soup.find("h1", attrs={"itemprop": "name"})
price = soup.find("span", attrs={"itemprop": "price"})
reviews = soup.find("a", attrs={"itemprop": "ratingCount"})
rating = soup.find("span", attrs={"class": "rating-number"})
image = soup.find("meta", property="og:image")

for label, node in [("title", title), ("price", price), ("reviews", reviews),
                    ("rating", rating), ("image", image)]:
    value = None
    if node is not None:
        value = node.get("content") if label == "image" else node.get_text(strip=True)
    print(f"{label}: {value}")
