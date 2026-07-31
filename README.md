# Indian Deals

Static SEO site for "best products under ₹X in India" buying guides.

## Architecture

- **No build tools, no Node, no frameworks.** Just HTML + CSS + vanilla JS.
- **Articles** live as JSON metadata + HTML body pairs in `articles/<slug>/`.
- **`build.py`** renders articles through templates → writes category/budget index pages → generates `sitemap.xml` + `robots.txt`.
- **Hosted on GitHub Pages** (free) — point a custom domain at it later.

## Project structure

```
indian-deals/
├── articles/             # source: each article is its own folder
│   └── <slug>/
│       ├── meta.json     # title, description, FAQ, headings, CTA
│       └── body.html     # the actual article content
├── templates/
│   ├── article.html      # article page template
│   └── category.html     # category/budget index template
├── articles/             # generated: rendered article HTMLs
├── category/             # generated: category index pages
├── budget/               # generated: budget index pages
├── index.html            # homepage
├── about.html            # about page
├── disclosure.html       # affiliate disclosure
├── privacy.html          # privacy policy
├── contact.html          # contact page
├── sitemap.xml           # generated
├── robots.txt            # generated
├── build.py              # the build script
├── generate_content.py   # auto-content pipeline (planned.json)
└── planned.json          # content roadmap
```

## Local development

```bash
# Generate new articles (if planned.json has them)
python3 generate_content.py

# Build everything
python3 build.py

# Serve locally
python3 -m http.server 8000
# Then visit http://localhost:8000
```

## Adding a new article

1. Create folder `articles/<slug>/`
2. Write `meta.json` (use existing meta.json as template)
3. Write `body.html` (HTML body, h2/h3 with id="..." attributes)
4. Run `python3 build.py`
5. Commit + push to GitHub

## Deployment

The site is fully static. Deploy any way you like:
- GitHub Pages (free, automatic on push to main)
- Netlify (drag-and-drop the folder)
- Cloudflare Pages
- Or just `python3 -m http.server 8000` and use a tunnel

## Roadmap

- [ ] 50 buying guides across 15 categories
- [ ] Each guide refreshed every 60-90 days
- [ ] Google AdSense + Amazon Associates integration
- [ ] Email signup for "weekly deals" newsletter (after 100 articles)
- [ ] Comparison tables (side-by-side specs)
