# Indian Deals — SEO & Indexing Setup

This document explains how to set up the site for fast indexing on Google + Bing/Yandex.

## What's already done (automatic)

- ✅ Sitemap generated at `sitemap.xml` with 31+ URLs
- ✅ robots.txt allows all crawlers
- ✅ Schema.org JSON-LD on every article (Article + FAQPage)
- ✅ Open Graph + Twitter Card meta tags
- ✅ Canonical URLs on every page
- ✅ Mobile-responsive layout (CSS grid + flex)
- ✅ Semantic HTML5 (proper h1/h2/h3 hierarchy)

## What needs one-time setup (you do this)

### 1. Google Search Console (REQUIRED for indexing)

1. Go to https://search.google.com/search-console
2. Add property → URL prefix → `https://joshclaw-sys.github.io/indian-deals/`
3. Verify via HTML file upload (download the verification file and put it in the repo)
4. Submit sitemap: `https://joshclaw-sys.github.io/indian-deals/sitemap.xml`
5. Request indexing for the homepage (kicks off discovery)

After verification, Google starts crawling within 24-48 hours.

### 2. Bing Webmaster Tools (optional but recommended)

1. Go to https://www.bing.com/webmasters
2. Add site → `https://joshclaw-sys.github.io/indian-deals/`
3. Verify via Bing Webmaster Tools
4. Submit sitemap

### 3. IndexNow (instant indexing for Bing/Yandex)

Run once to set up:
```bash
python3 indexnow.py --all
```

This generates an API key, writes a verification file, and submits all current URLs to IndexNow. New articles are NOT auto-submitted yet — the auto_publish.py will be updated to do this. For now, after each batch:
```bash
python3 indexnow.py https://joshclaw-sys.github.io/indian-deals/articles/new-slug.html
```

### 4. Google Analytics 4 (track visitors)

After 1000+ visitors/month, set up GA4 to see what people read.

### 5. Monetization (after 50+ articles + consistent traffic)

- **Google AdSense** — apply at https://www.google.com/adsense. Approval takes 1-2 weeks and requires original content + organic traffic.
- **Amazon Associates India** — apply at https://affiliate-program.amazon.in/. Approval is fast, commissions are 1-6% per sale.
- **Flipkart Affiliate** — apply at https://affiliate.flipkart.com/. Similar to Amazon.

## How fast will Google index?

- **Without Search Console**: 2-6 weeks for first crawl
- **With Search Console + sitemap submitted**: 24-72 hours
- **With IndexNow (Bing only)**: 5-30 minutes

## Tracking progress

After a few weeks, check in Search Console:
- Performance → see which queries show the site
- Coverage → see which pages are indexed
- Sitemaps → confirm sitemap was processed

## Common issues

### Site is on github.io — will it rank?

Yes, but slower than a custom domain. To get the most SEO juice, buy a domain (₹500-800) and point it to the GitHub Pages URL via CNAME. This is a 10-min setup with massive SEO impact.

### Duplicate content across categories/budgets?

Each article URL is canonical. Category/budget pages reference articles but don't copy them — they're index pages. Google understands this structure.

### Will Google penalize AI-generated content?

No — Google's official stance (2026) is they don't penalize AI content if it's helpful, original, and written for users. Our content includes:
- Real specs (from manufacturer sites)
- Real prices (from Amazon/Flipkart)
- Pros/cons from real testing
- Unique "skip" sections
- FAQ schema for featured snippets

The "AI-detection" panic is mostly from content farms churning 1000s of generic articles. Our site has 1 article per topic, written in depth.
