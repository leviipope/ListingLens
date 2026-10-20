import feedparser
import httpx

url = "https://hardverapro.hu/hirfolyam/aprok/hardver/videokartya/nvidia/geforce_40xx/rss.xml"

response = httpx.get(url, timeout=20, follow_redirects=True)
response.raise_for_status()

feed = feedparser.parse(response.content)

print(f"Entries: {len(feed.entries)}")

for entry in feed.entries[:3]:
    print(entry)
