#!/usr/bin/env python3
"""
Ping search engines whenever new content is published.

Sends:
- Google sitemap ping (for old-school index refresh)
- Bing IndexNow (faster indexing)

Usage:
  python3 ping_search_engines.py                # ping with current sitemap
  python3 ping_search_engines.py <sitemap_url>  # ping a specific URL
"""
import sys
import urllib.request
import urllib.parse
from pathlib import Path

DEFAULT_SITEMAP = "https://joshclaw-sys.github.io/indian-deals/sitemap.xml"


def ping_google(sitemap_url):
    """Notify Google that the sitemap was updated."""
    url = f"https://www.google.com/ping?sitemap={urllib.parse.quote(sitemap_url)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return ("Google", r.status, "OK" if r.status == 200 else f"HTTP {r.status}")
    except Exception as e:
        return ("Google", "ERR", str(e))


def ping_bing_indexnow(sitemap_url):
    """Notify Bing's IndexNow API."""
    # IndexNow takes individual URLs; for simplicity, ping with the sitemap URL
    url = f"https://www.bing.com/ping?sitemap={urllib.parse.quote(sitemap_url)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return ("Bing", r.status, "OK" if r.status == 200 else f"HTTP {r.status}")
    except Exception as e:
        return ("Bing", "ERR", str(e))


def main():
    sitemap = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SITEMAP
    print(f"Pinging search engines with: {sitemap}\n")

    results = [
        ping_google(sitemap),
        ping_bing_indexnow(sitemap),
    ]

    for engine, code, msg in results:
        icon = "✓" if code == 200 else "✗"
        print(f"  {icon} {engine}: {code} — {msg}")


if __name__ == "__main__":
    main()
