import requests
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"}

r = requests.get("https://www.walmart.com/ip/771229626", headers=headers, timeout=40)
soup = BeautifulSoup(r.text, "lxml")

print(r.status_code, "|", soup.title.get_text(strip=True), "|", len(r.text), "bytes")
