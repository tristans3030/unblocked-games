from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
import urllib.request

INDEX_URL = "https://orteil.dashnet.org/cookieclicker/img/"  # Your exact index URL
OUT_DIR = Path("img")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": INDEX_URL,
}


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href)


html = fetch_bytes(INDEX_URL).decode("utf-8", errors="replace")
parser = LinkExtractor()
parser.feed(html)

base_parsed = urlparse(INDEX_URL)
OUT_DIR.mkdir(parents=True, exist_ok=True)

downloaded = 0
for href in parser.hrefs:
    if href.startswith("?") or href.startswith("/") or href.endswith("/"):
        continue

    file_url = urljoin(INDEX_URL, href)
    file_parsed = urlparse(file_url)

    if file_parsed.netloc != base_parsed.netloc:
        continue
    if not file_parsed.path.startswith(base_parsed.path):
        continue

    dest = OUT_DIR / Path(file_parsed.path).name
    try:
        dest.write_bytes(fetch_bytes(file_url))
        downloaded += 1
        print(f"Saved: {dest}")
    except Exception as exc:
        print(f"Failed ({href}): {exc}")

print(f"Done. Downloaded {downloaded} files to '{OUT_DIR}'.")