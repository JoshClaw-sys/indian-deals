#!/usr/bin/env python3
"""
IndexNow submission for faster indexing.

IndexNow lets you submit individual URLs as they're published, and Bing/Yandex
index them within minutes. Google does NOT use IndexNow but discovers via
sitemap + Search Console.

Setup:
1. Generate a key at https://www.bing.com/indexnow (or use a random UUID)
2. Save it to .indexnow_key
3. Host <key>.txt at https://yourdomain/<key>.txt (proves you own the domain)

Usage:
  python3 indexnow.py <url1> [url2 ...]
  python3 indexnow.py --all   # submit all article URLs from sitemap
"""
import json
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).parent
KEY_FILE = ROOT / ".indexnow_key"

# IndexNow API endpoint
INDEXNOW_URL = "https://api.indexnow.org/indexnow"

# Where to host the verification key file
SITE_BASE = "https://joshclaw-sys.github.io/indian-deals"


def load_key():
    """Load or generate the IndexNow key."""
    if KEY_FILE.exists():
        return KEY_FILE.read_text().strip()
    # Generate a random 32-char hex key
    import secrets
    key = secrets.token_hex(16)
    KEY_FILE.write_text(key)
    print(f"Generated new IndexNow key: {key}")
    print(f"Save this in your static dir as {key}.txt (one-line file)")
    return key


def write_key_file(key):
    """Write the verification key file to the static dir."""
    out = ROOT / f"{key}.txt"
    out.write_text(key)
    print(f"  ✓ Wrote {out.name}")
    return out


def submit_urls(urls, key):
    """POST to IndexNow."""
    payload = {
        "host": "joshclaw-sys.github.io",
        "key": key,
        "keyLocation": f"https://joshclaw-sys.github.io/{key}.txt",
        "urlList": urls,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        INDEXNOW_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode()
            return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def get_sitemap_urls():
    """Parse sitemap.xml and return all URLs."""
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.exists():
        return []
    tree = ET.parse(sitemap)
    root = tree.getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [el.text for el in root.findall(".//sm:loc", ns)]


def main():
    if "--all" in sys.argv:
        sitemap_urls = get_sitemap_urls()
        # Replace placeholder domain with actual GitHub Pages URL
        urls = [u.replace("https://indian-deals.example", "https://joshclaw-sys.github.io/indian-deals") for u in sitemap_urls]
        print(f"Submitting all {len(urls)} URLs from sitemap...")
    elif len(sys.argv) > 1:
        raw_urls = sys.argv[1:]
        urls = [u.replace("https://indian-deals.example", "https://joshclaw-sys.github.io/indian-deals") for u in raw_urls]
        print(f"Submitting {len(urls)} URLs...")
    else:
        print("Usage: indexnow.py <url1> [url2 ...] | --all")
        sys.exit(1)

    if not urls:
        print("No URLs to submit")
        return

    key = load_key()

    # Make sure the verification key file is in the static dir
    key_path = write_key_file(key)

    # Submit in batches of 10,000 (IndexNow limit)
    BATCH = 10000
    for i in range(0, len(urls), BATCH):
        batch = urls[i:i + BATCH]
        status, body = submit_urls(batch, key)
        if status == 200:
            print(f"  ✓ Batch {i//BATCH + 1}: {len(batch)} URLs submitted")
        else:
            print(f"  ✗ Batch {i//BATCH + 1}: HTTP {status} — {body[:200]}")


if __name__ == "__main__":
    main()
