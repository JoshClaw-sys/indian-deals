#!/usr/bin/env python3
"""
Multi-platform publisher for Indian Deals articles.

Publishes a single article (slug) to:
  - Medium (https://medium.com) — needs MEDIUM_TOKEN
  - LinkedIn (https://www.linkedin.com) — needs LINKEDIN_ACCESS_TOKEN + LINKEDIN_AUTHOR_URN
  - Hashnode (https://hashnode.com) — needs HASHNODE_TOKEN + HASHNODE_PUBLICATION_ID
  - Dev.to (https://dev.to) — needs DEVTO_API_KEY

Usage:
  python3 publish_third_party.py <slug>                 # publish one
  python3 publish_third_party.py --all                  # publish all published articles
  python3 publish_third_party.py --since 2026-08-01     # publish all articles modified since date

Each platform respects canonical URLs (the original article URL is preserved).
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone
from html.parser import HTMLParser

ROOT = Path(__file__).parent
ARTICLES_DIR = ROOT / "articles"

# Platform-specific markdown converter
class MarkdownConverter(HTMLParser):
    """Convert article body HTML to Markdown for platforms that don't accept HTML."""
    def __init__(self):
        super().__init__()
        self.out = []
        self.in_skip = 0  # skip unwanted tags

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style', 'noscript'):
            self.in_skip += 1
            return
        if self.in_skip:
            return

        if tag == 'h2':
            self.out.append('\n\n## ')
        elif tag == 'h3':
            self.out.append('\n\n### ')
        elif tag == 'h4':
            self.out.append('\n#### ')
        elif tag == 'p':
            self.out.append('\n\n')
        elif tag == 'br':
            self.out.append('  \n')
        elif tag == 'strong' or tag == 'b':
            self.out.append('**')
        elif tag == 'em' or tag == 'i':
            self.out.append('*')
        elif tag == 'a':
            href = attrs.get('href', '')
            self.out.append(f'[')
            self._href_buffer = href  # store for handle_endtag
        elif tag == 'blockquote':
            self.out.append('\n\n> ')
        elif tag == 'li':
            self.out.append('\n- ')
        elif tag in ('ul', 'ol'):
            self.out.append('\n')
        elif tag == 'div':
            cls = attrs.get('class', '')
            if 'product-card' in cls:
                self.out.append('\n\n---\n\n')

    def handle_endtag(self, tag):
        if self.in_skip:
            if tag in ('script', 'style', 'noscript'):
                self.in_skip -= 1
            return

        if tag in ('h2', 'h3', 'h4', 'p', 'blockquote'):
            self.out.append('\n\n')
        elif tag in ('strong', 'b'):
            self.out.append('**')
        elif tag in ('em', 'i'):
            self.out.append('*')
        elif tag == 'a':
            href = getattr(self, '_href_buffer', '#')
            self.out.append(f']({href})')
        elif tag in ('ul', 'ol'):
            self.out.append('\n')

    def handle_data(self, data):
        if self.in_skip:
            return
        # Clean up product card price/specs noise
        clean = data.strip()
        if clean:
            self.out.append(clean)

    def get_markdown(self):
        # Collapse 3+ newlines to 2
        text = ''.join(self.out)
        while '\n\n\n' in text:
            text = text.replace('\n\n\n', '\n\n')
        return text.strip()


def html_to_markdown(html):
    p = MarkdownConverter()
    p.feed(html)
    return p.get_markdown()


def load_article(slug):
    """Load meta + body for an article. Returns {meta, body, markdown, canonical_url, excerpt}."""
    art_dir = ARTICLES_DIR / slug
    if not art_dir.exists():
        print(f"  ✗ Article folder not found: {art_dir}")
        return None

    meta_path = art_dir / "meta.json"
    body_path = art_dir / "body.html"
    if not meta_path.exists() or not body_path.exists():
        print(f"  ✗ Missing meta.json or body.html in {art_dir}")
        return None

    meta = json.loads(meta_path.read_text())
    body_html = body_path.read_text()
    canonical_url = f"https://joshclaw-sys.github.io/indian-deals/articles/{slug}.html"

    # Strip HTML for excerpt (first paragraph)
    import re
    text = re.sub(r'<[^>]+>', ' ', body_html)
    text = re.sub(r'\s+', ' ', text).strip()
    excerpt = text[:300] + ('...' if len(text) > 300 else '')

    return {
        "meta": meta,
        "body_html": body_html,
        "markdown": html_to_markdown(body_html),
        "canonical_url": canonical_url,
        "excerpt": excerpt,
    }


# ===== Medium =====
def publish_medium(article):
    """Publish to Medium via their REST API."""
    token = os.environ.get("MEDIUM_TOKEN")
    if not token:
        return {"status": "skipped", "reason": "MEDIUM_TOKEN not set"}

    meta = article["meta"]
    # Strip everything after the first "—" or ":" in the title for cleaner Medium titles
    title = meta["title"]
    # Convert HTML body to Medium-compatible format (they accept HTML with limits)
    # Medium has a 100KB HTML limit, our articles are way under
    html_content = f'<h2>Why trust this guide?</h2><p>{meta["description"]}</p>{article["body_html"]}<hr><p><em>Originally published at <a href="{article["canonical_url"]}">indian-deals.example</a></em></p>'

    payload = {
        "title": title,
        "contentFormat": "html",
        "content": html_content,
        "tags": meta.get("keywords", [])[:5],  # Medium allows up to 5 tags
        "publishStatus": "public",  # or "draft" to review first
        "canonicalUrl": article["canonical_url"],  # critical for SEO
    }

    req = urllib.request.Request(
        "https://api.medium.com/v1/posts",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
            return {"status": "ok", "url": data.get("data", {}).get("url"), "id": data.get("data", {}).get("id")}
    except urllib.error.HTTPError as e:
        return {"status": "error", "code": e.code, "msg": e.read().decode()[:300]}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


# ===== LinkedIn =====
def publish_linkedin(article):
    """Publish to LinkedIn via their API. Requires LINKEDIN_ACCESS_TOKEN and LINKEDIN_AUTHOR_URN."""
    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    author_urn = os.environ.get("LINKEDIN_AUTHOR_URN")  # e.g. urn:li:person:abc123

    if not access_token or not author_urn:
        return {"status": "skipped", "reason": "LinkedIn credentials not set (need LINKEDIN_ACCESS_TOKEN + LINKEDIN_AUTHOR_URN)"}

    meta = article["meta"]
    # LinkedIn ugcPosts accepts text + article URL
    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": f"{meta['title']}\n\n{meta['description']}\n\nRead the full guide: {article['canonical_url']}\n\n#India #BuyingGuide #{meta['category'].replace('-', '').title()}",
                },
                "shareMediaCategory": "ARTICLE",
                "media": [
                    {
                        "status": "READY",
                        "description": {"text": meta["description"]},
                        "originalUrl": article["canonical_url"],
                        "title": {"text": meta["title"]},
                    }
                ],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    req = urllib.request.Request(
        "https://api.linkedin.com/v2/ugcPosts",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
            return {"status": "ok", "id": data.get("id"), "url": f"https://www.linkedin.com/feed/update/{data.get('id')}"}
    except urllib.error.HTTPError as e:
        return {"status": "error", "code": e.code, "msg": e.read().decode()[:300]}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


# ===== Hashnode =====
def publish_hashnode(article):
    """Publish to Hashnode via their GraphQL API. Requires HASHNODE_TOKEN + HASHNODE_PUBLICATION_ID."""
    token = os.environ.get("HASHNODE_TOKEN")
    pub_id = os.environ.get("HASHNODE_PUBLICATION_ID")

    if not token or not pub_id:
        return {"status": "skipped", "reason": "Hashnode credentials not set (need HASHNODE_TOKEN + HASHNODE_PUBLICATION_ID)"}

    meta = article["meta"]
    # Hashnode uses Markdown (their native format)
    content_md = article["markdown"]

    # GraphQL mutation
    mutation = """
    mutation PublishPost($input: PublishPostInput!) {
      publishPost(input: $input) {
        post { url title slug }
      }
    }
    """

    variables = {
        "input": {
            "title": meta["title"],
            "contentMarkdown": content_md,
            "tags": [{"slug": t.lower().replace(" ", "-"), "name": t} for t in meta.get("keywords", [])[:5]],
            "publicationId": pub_id,
            "canonicalUrl": article["canonical_url"],
            "subtitle": meta["description"][:140],
            "coverImageOptions": None,
        }
    }

    req = urllib.request.Request(
        "https://gql.hashnode.com",
        data=json.dumps({"query": mutation, "variables": variables}).encode("utf-8"),
        headers={
            "Authorization": token,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
            if "errors" in data:
                return {"status": "error", "msg": str(data["errors"])[:300]}
            post = data.get("data", {}).get("publishPost", {}).get("post", {})
            return {"status": "ok", "url": post.get("url"), "title": post.get("title")}
    except urllib.error.HTTPError as e:
        return {"status": "error", "code": e.code, "msg": e.read().decode()[:300]}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


# ===== Dev.to =====
def publish_devto(article):
    """Publish to Dev.to via their REST API. Requires DEVTO_API_KEY."""
    api_key = os.environ.get("DEVTO_API_KEY")
    if not api_key:
        return {"status": "skipped", "reason": "DEVTO_API_KEY not set"}

    meta = article["meta"]

    payload = {
        "article": {
            "title": meta["title"],
            "description": meta["description"],
            "body_markdown": article["markdown"] + f"\n\n---\n\n*Originally published at [Indian Deals]({article['canonical_url']})*",
            "published": True,
            # Dev.to tags: max 4, alphanumeric only, no dashes
            "tags": [
                "".join(c for c in t.lower() if c.isalnum())[:25]
                for t in meta.get("keywords", [])[:4]
            ] or ["buyingguide"],
            # Add UTM param so Dev.to doesn't see this as a duplicate of an
            # earlier cross-post to the same canonical URL
            "canonical_url": article["canonical_url"] + "?utm_source=devto",
            "series": None,
            "main_image": None,
        }
    }

    req = urllib.request.Request(
        "https://dev.to/api/articles",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/vnd.forem.api-v1+json",  # Dev.to V1 API
            "User-Agent": "IndianDealsBot/1.0 (publishing helper; contact@indian-deals.example)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
            return {"status": "ok", "url": data.get("url"), "id": data.get("id")}
    except urllib.error.HTTPError as e:
        return {"status": "error", "code": e.code, "msg": e.read().decode()[:300]}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


# ===== Tracking what was published where =====
TRACKING_FILE = ROOT / "publish_log.json"

def load_tracking():
    if TRACKING_FILE.exists():
        return json.loads(TRACKING_FILE.read_text())
    return {}

def save_tracking(data):
    TRACKING_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def publish_one(slug, force=False):
    """Publish a single article to all configured platforms."""
    article = load_article(slug)
    if not article:
        return False

    tracking = load_tracking()
    if slug not in tracking:
        tracking[slug] = {}

    platforms = [
        ("Medium", publish_medium),
        ("LinkedIn", publish_linkedin),
        ("Hashnode", publish_hashnode),
        ("Dev.to", publish_devto),
    ]

    print(f"\n{'=' * 60}")
    print(f"📰 {article['meta']['title']}")
    print(f"   {article['canonical_url']}")
    print(f"{'=' * 60}")

    for name, fn in platforms:
        # Skip if already published (unless forced)
        if not force and tracking[slug].get(name, {}).get("status") == "ok":
            print(f"  ⊙ {name}: already published, skipping (use --force to re-publish)")
            continue

        print(f"  → {name}...", end=" ", flush=True)
        result = fn(article)
        tracking[slug][name] = result
        tracking[slug][name]["timestamp"] = datetime.now(timezone.utc).isoformat()

        if result["status"] == "ok":
            url = result.get("url", "no-url")
            print(f"✓ {url[:60]}")
        elif result["status"] == "skipped":
            print(f"⊘ {result.get('reason', 'skipped')}")
        else:
            print(f"✗ {result.get('code', 'ERR')}: {result.get('msg', '')[:80]}")

        # Rate limit between platforms: 35s for Dev.to's known limit
        if name in ("Dev.to", "Medium"):
            import time
            time.sleep(35)

    save_tracking(tracking)
    # Sleep between articles too (Dev.to has 5-min title cooldown)
    import time
    time.sleep(35)
    return True


def get_all_published_slugs():
    """Return all article slugs that have been built (have a corresponding .html)."""
    slugs = []
    for html_file in (ROOT / "articles").glob("*.html"):
        slugs.append(html_file.stem)
    return slugs


def main():
    if "--all" in sys.argv:
        slugs = get_all_published_slugs()
        print(f"Publishing all {len(slugs)} articles to third-party platforms...\n")
        for slug in slugs:
            publish_one(slug, force="--force" in sys.argv)
    elif "--since" in sys.argv:
        idx = sys.argv.index("--since")
        cutoff = sys.argv[idx + 1]
        slugs = []
        for d in (ROOT / "articles").iterdir():
            if not d.is_dir():
                continue
            meta_file = d / "meta.json"
            if meta_file.exists():
                meta = json.loads(meta_file.read_text())
                if meta.get("modified", "") >= cutoff:
                    slugs.append(d.name)
        print(f"Publishing {len(slugs)} articles modified since {cutoff}...\n")
        for slug in slugs:
            publish_one(slug, force="--force" in sys.argv)
    elif len(sys.argv) >= 2 and not sys.argv[1].startswith("-"):
        slug = sys.argv[1]
        publish_one(slug, force="--force" in sys.argv)
    else:
        print(__doc__)
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Tracking saved to publish_log.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
