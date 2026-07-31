#!/usr/bin/env python3
"""
Indian Deals — static site generator.

Reads article definitions from articles/*.json, renders them with the templates,
writes category + budget index pages, generates sitemap.xml + robots.txt.

Usage:
  python3 build.py                 # builds everything
  python3 build.py --only-new      # only generates articles not already on disk
"""
import json
import sys
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent
TEMPLATES = ROOT / "templates"
OUT = ROOT  # articles go straight into the repo for GitHub Pages

ARTICLE_TEMPLATE = (TEMPLATES / "article.html").read_text()
CATEGORY_TEMPLATE = (TEMPLATES / "category.html").read_text()
BUDGET_TEMPLATE = (TEMPLATES / "category.html").read_text()  # same template, different content

# ---- Source-of-truth registry ----
# Every article lives here. Adding a new one = add a JSON file in articles/.
ARTICLES_DIR = ROOT / "articles"

CATEGORIES = {
    "laptops": {"title": "Laptops", "icon": "💻", "desc": "Buying guides for every budget — from study laptops to creator workhorses.", "crumb": "Laptops"},
    "earbuds": {"title": "Earbuds & Headphones", "icon": "🎧", "desc": "TWS, ANC, sound quality — what actually matters at each price.", "crumb": "Earbuds"},
    "smartphones": {"title": "Smartphones", "icon": "📱", "desc": "Best phones by budget — camera, battery, performance ranked.", "crumb": "Smartphones"},
    "air-fryers": {"title": "Air Fryers", "icon": "🍟", "desc": "Honest air fryer reviews — capacity, real cooking performance, noise.", "crumb": "Air Fryers"},
    "ac": {"title": "Air Conditioners", "icon": "❄️", "desc": "Split, window, inverter — pick the right AC for your room and budget.", "crumb": "ACs"},
    "refrigerator": {"title": "Refrigerators", "icon": "🧊", "desc": "Direct cool vs frost free, capacity guides, energy ratings.", "crumb": "Fridges"},
    "washing-machine": {"title": "Washing Machines", "icon": "🌀", "desc": "Top load, front load, semi-auto — what works for Indian homes.", "crumb": "Washing Machines"},
    "smartwatch": {"title": "Smartwatches", "icon": "⌚", "desc": "AMOLED, GPS, health tracking — value picks at every budget.", "crumb": "Smartwatches"},
    "water-purifier": {"title": "Water Purifiers", "icon": "💧", "desc": "RO, UV, alkaline — TDS levels, maintenance, real costs.", "crumb": "Water Purifiers"},
    "mixer-grinder": {"title": "Mixer Grinders", "icon": "🥤", "desc": "Indian kitchens need real power. Top picks across budgets.", "crumb": "Mixer Grinders"},
    "soundbar": {"title": "Soundbars", "icon": "🔊", "desc": "Cinema at home — Dolby Atmos, subwoofers, what fits your TV.", "crumb": "Soundbars"},
    "vacuum": {"title": "Vacuums", "icon": "🧹", "desc": "Robot vacuums, handheld, wet/dry — tested for Indian dust.", "crumb": "Vacuums"},
    "microwave": {"title": "Microwaves", "icon": "🍲", "desc": "Solo, grill, convection — what to buy for your cooking style.", "crumb": "Microwaves"},
    "geyser": {"title": "Geysers", "icon": "♨️", "desc": "Instant vs storage — tank size, electricity cost, safety.", "crumb": "Geysers"},
    "trimmer": {"title": "Trimmers", "icon": "✂️", "desc": "Beard and body trimmers — battery, blades, water resistance.", "crumb": "Trimmers"},
}

BUDGETS = {
    "1000":   {"label": "Under ₹1,000",   "max": 1000},
    "2000":   {"label": "Under ₹2,000",   "max": 2000},
    "5000":   {"label": "Under ₹5,000",   "max": 5000},
    "10000":  {"label": "Under ₹10,000",  "max": 10000},
    "20000":  {"label": "Under ₹20,000",  "max": 20000},
    "30000":  {"label": "Under ₹30,000",  "max": 30000},
    "50000":  {"label": "Under ₹50,000",  "max": 50000},
    "75000":  {"label": "Under ₹75,000",  "max": 75000},
    "100000": {"label": "Under ₹1,00,000", "max": 100000},
}


def parse_price_max(price_str: str) -> int:
    """Extract upper bound from price string like '₹3,500–₹5,000'."""
    nums = re.findall(r"[\d,]+", price_str)
    if not nums:
        return 0
    last = int(nums[-1].replace(",", ""))
    return last


def render_article(meta: dict, body_html: str, related: list) -> str:
    """Fill the article template."""
    cat = meta["category"]
    cat_title = CATEGORIES[cat]["title"]
    cat_singular = cat_title.rstrip("s") if cat_title.endswith("s") and not cat_title.endswith("ss") else cat_title

    # Build FAQ schema (JSON string for inline script)
    faq_items = meta.get("faq", [])
    faq_schema = json.dumps([{
        "@type": "Question",
        "name": faq["q"],
        "acceptedAnswer": {"@type": "Answer", "text": faq["a"]}
    } for faq in faq_items], ensure_ascii=False)

    # Build TOC from h2/h3
    toc_html = '<div class="toc"><h2>📑 In this guide</h2><ol>'
    for h in meta.get("headings", []):
        toc_html += f'<li><a href="#{h["id"]}">{h["text"]}</a></li>'
    toc_html += '</ol></div>'

    # Build FAQ HTML
    faq_html = ''
    if faq_items:
        faq_html = '<div class="faq"><h2>❓ Frequently asked questions</h2>'
        for faq in faq_items:
            faq_html += f'<div class="faq-item"><h3>{faq["q"]}</h3><p>{faq["a"]}</p></div>'
        faq_html += '</div>'

    # Related CTA at bottom
    related_cta = ''
    if meta.get("cta"):
        related_cta = f'<div class="cta-block"><h3 style="margin-bottom: 8px;">{meta["cta"]["headline"]}</h3><p style="margin-bottom: 16px;">{meta["cta"]["sub"]}</p><a href="{meta["cta"]["link"]}" class="cta">{meta["cta"]["button"]}</a></div>'

    # Related articles card list
    related_js = json.dumps([{"slug": r["slug"], "title": r["title"], "tag": r.get("tag", "Guide")} for r in related], ensure_ascii=False)

    out = ARTICLE_TEMPLATE
    replacements = {
        "ARTICLE_TITLE": meta["title"],
        "ARTICLE_SHORT_TITLE": meta["short_title"],
        "ARTICLE_DESC": meta["description"],
        "ARTICLE_KEYWORDS": ", ".join(meta.get("keywords", [])),
        "ARTICLE_CATEGORY": cat,
        "ARTICLE_CATEGORY_TITLE": cat_title,
        "ARTICLE_SLUG": meta["slug"],
        "ARTICLE_DATE": meta["date"],
        "ARTICLE_MODIFIED": meta["modified"],
        "ARTICLE_DATE_DISPLAY": meta["date_display"],
        "ARTICLE_TIME": meta["read_time"],
        "ARTICLE_BODY": body_html,
        "FAQ_SCHEMA": faq_schema,
        "ARTICLE_TOC": toc_html,
        "ARTICLE_FAQ": faq_html,
        "ARTICLE_RELATED_CTA": related_cta,
        "RELATED_ARTICLES": related_js,
    }
    for k, v in replacements.items():
        out = out.replace(k, v)
    return out


def render_category(cat_key: str, articles: list) -> str:
    cat = CATEGORIES[cat_key]
    articles_js = json.dumps([{
        "slug": a["slug"],
        "title": a["title"],
        "desc": a["short_desc"],
        "tag": a["tag"],
        "price": a["price"],
        "time": a["read_time"],
    } for a in articles], ensure_ascii=False)

    out = CATEGORY_TEMPLATE
    replacements = {
        "CATEGORY_TITLE": cat["title"],
        "CATEGORY_DESC": cat["desc"],
        "CATEGORY_KEYWORDS": f"best {cat_key} India 2026, {cat['title'].lower()} buying guide, best {cat_key} under budget India",
        "CATEGORY_CRUMB": cat["crumb"],
        "CATEGORY_URL": f"category/{cat_key}.html",
        "CATEGORY_ARTICLES": articles_js,
    }
    for k, v in replacements.items():
        out = out.replace(k, v)
    return out


def render_budget(budget_key: str, articles: list) -> str:
    b = BUDGETS[budget_key]
    articles_js = json.dumps([{
        "slug": a["slug"],
        "title": a["title"],
        "desc": a["short_desc"],
        "tag": a["tag"],
        "price": a["price"],
        "time": a["read_time"],
    } for a in articles], ensure_ascii=False)

    out = BUDGET_TEMPLATE
    replacements = {
        "CATEGORY_TITLE": b["label"],
        "CATEGORY_DESC": f"Best products {b['label'].lower()} in India (2026). We ranked every guide we publish so the best value-for-money picks surface first.",
        "CATEGORY_KEYWORDS": f"best under {b['label'].split()[-1]} India, cheap {b['label'].lower()} India 2026",
        "CATEGORY_CRUMB": b["label"],
        "CATEGORY_URL": f"budget/under-{budget_key}.html",
        "CATEGORY_ARTICLES": articles_js,
    }
    for k, v in replacements.items():
        out = out.replace(k, v)
    return out


def render_related(article: dict, all_articles: list) -> list:
    """Pick 4 related articles: same category first, then same budget tier."""
    cat = article["category"]
    same_cat = [a for a in all_articles if a["slug"] != article["slug"] and a["category"] == cat]
    other_cat = [a for a in all_articles if a["slug"] != article["slug"] and a["category"] != cat]
    return (same_cat + other_cat)[:4]


def build():
    # Load all article JSONs (each article lives in its own folder)
    articles = []
    for d in sorted(ARTICLES_DIR.iterdir()):
        if d.is_dir():
            meta = d / "meta.json"
            if meta.exists():
                data = json.loads(meta.read_text())
                articles.append(data)
    print(f"Loaded {len(articles)} articles")

    # ---- Render articles ----
    (OUT / "articles").mkdir(exist_ok=True)
    for art in articles:
        body_html = (ARTICLES_DIR / art["slug"] / "body.html").read_text()
        related = render_related(art, articles)
        html = render_article(art, body_html, related)
        out_path = OUT / "articles" / f"{art['slug']}.html"
        out_path.write_text(html)
        print(f"  ✓ articles/{art['slug']}.html")

    # ---- Render category pages ----
    (OUT / "category").mkdir(exist_ok=True)
    for cat_key in CATEGORIES:
        cat_articles = [a for a in articles if a["category"] == cat_key]
        html = render_category(cat_key, cat_articles)
        (OUT / "category" / f"{cat_key}.html").write_text(html)
        print(f"  ✓ category/{cat_key}.html ({len(cat_articles)} articles)")

    # ---- Render budget pages ----
    (OUT / "budget").mkdir(exist_ok=True)
    for budget_key, b in BUDGETS.items():
        budget_articles = [a for a in articles if parse_price_max(a["price"]) <= b["max"]]
        html = render_budget(budget_key, budget_articles)
        (OUT / "budget" / f"under-{budget_key}.html").write_text(html)
        print(f"  ✓ budget/under-{budget_key}.html ({len(budget_articles)} articles)")

    # ---- Build sitemap ----
    base = "https://indian-deals.example"
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>']
    sitemap.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    sitemap.append(f'  <url><loc>{base}/</loc><priority>1.0</priority><changefreq>daily</changefreq></url>')
    for art in articles:
        sitemap.append(f'  <url><loc>{base}/articles/{art["slug"]}.html</loc><lastmod>{art["modified"]}</lastmod><priority>0.8</priority></url>')
    for cat_key in CATEGORIES:
        sitemap.append(f'  <url><loc>{base}/category/{cat_key}.html</loc><priority>0.7</priority></url>')
    for budget_key in BUDGETS:
        sitemap.append(f'  <url><loc>{base}/budget/under-{budget_key}.html</loc><priority>0.6</priority></url>')
    sitemap.append('</urlset>')
    (OUT / "sitemap.xml").write_text("\n".join(sitemap))
    print(f"  ✓ sitemap.xml")

    # ---- robots.txt ----
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    print(f"  ✓ robots.txt")

    print(f"\n✅ Build complete — {len(articles)} articles, {len(CATEGORIES)} categories, {len(BUDGETS)} budgets")


if __name__ == "__main__":
    build()
