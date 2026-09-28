import os

import requests

API_KEY = os.environ["HASDATA_API_KEY"]

response = requests.post(
    "https://api.hasdata.com/scrape/web",
    headers={"x-api-key": API_KEY, "Content-Type": "application/json"},
    json={
        "url": "https://www.walmart.com/ip/771229626",
        "proxyType": "residential",   # datacenter exits get the challenge page
        "proxyCountry": "US",         # prices and availability differ by region
        "outputFormat": ["html"],     # the response body is the raw page
    },
    timeout=120,
)

html = response.text
print(response.status_code, "|", len(html), "bytes of product page")
