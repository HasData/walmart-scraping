import json
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

state = json.loads(soup.find("script", id="__NEXT_DATA__").text)
product = state["props"]["pageProps"]["initialData"]["data"]["product"]

def count_leaves(node):
    if isinstance(node, dict):
        return sum(count_leaves(v) for v in node.values())
    if isinstance(node, list):
        return sum(count_leaves(v) for v in node)
    return 1

print(product["name"])
print(product["priceInfo"]["currentPrice"]["priceString"],
      "|", product["averageRating"], "stars,", product["numberOfReviews"], "reviews")
print("fields in the product node:", count_leaves(product))
