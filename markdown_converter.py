"""Clean HTML → Markdown converter for AI Tools Hub articles.

Article bodies use a consistent HTML structure:
  - <h2 id="...">Title</h2>
  - <p>text <strong>bold</strong> text</p>
  - <blockquote>quote</blockquote>
  - <div class="product-card">
      <span class="badge top">⭐ Top Pick</span>
      <h3>1. Tool Name</h3>
      <div class="price-line">$X</div>
      <div class="quick-specs">
        <div><strong>Label1</strong>Value1</div>
        <div><strong>Label2</strong>Value2</div>
      </div>
      <p>description</p>
      <div class="pros-cons">
        <div class="pros"><h4>✓ What works</h4><ul><li>item</li></ul></div>
        <div class="cons"><h4>✗ Trade-offs</h4><ul><li>item</li></ul></div>
      </div>
    </div>

We use regex pattern-matching for known structures rather than HTMLParser.
"""
import re


# Badge class → display label
BADGE_LABELS = {
    'top': '⭐ Top Pick',
    'runner': '🥈 Runner-up',
    'budget': '💰 Best Value',
    'skip': '⚠️ Skip',
}


def html_to_markdown(html):
    """Convert article body HTML to clean Markdown for cross-posting."""
    md = html

    # 1. Strip script/style/comments entirely
    md = re.sub(r'<script[^>]*>.*?</script>', '', md, flags=re.DOTALL)
    md = re.sub(r'<style[^>]*>.*?</style>', '', md, flags=re.DOTALL)
    md = re.sub(r'<!--.*?-->', '', md, flags=re.DOTALL)

    # 2. Convert badges (inside product cards)
    def replace_badge(match):
        cls = match.group(1)
        text = match.group(2).strip()
        for key, label in BADGE_LABELS.items():
            if key in cls:
                # Strip the emoji prefix if the text duplicates the badge
                clean = text
                # Remove "Top Pick", "Runner-up" etc. from text if present
                for badge_text in BADGE_LABELS.values():
                    short = badge_text.split(' ', 1)[1] if ' ' in badge_text else badge_text
                    for variant in [badge_text, short]:
                        if clean.lower().startswith(variant.lower()):
                            clean = clean[len(variant):].lstrip(' —-')
                            break
                if clean.strip():
                    return f'**{label}** — {clean}'
                return f'**{label}**'
        return f'**{text}**'

    md = re.sub(
        r'<span class="badge\s+([^"]+)"[^>]*>([^<]+)</span>',
        replace_badge,
        md,
    )

    # 3. Convert product cards — extract clean content
    def extract_product_card(match):
        block = match.group(0)

        # Title (h3)
        title_match = re.search(r'<h3>([^<]+)</h3>', block)
        title = clean_inline(title_match.group(1)) if title_match else ''

        # Price
        price_match = re.search(r'<div class="price-line">([^<]+)</div>', block)
        price = clean_inline(price_match.group(1)) if price_match else ''

        # Specs (quick-specs div with rows) — match all 4 inner divs + closing div
        specs_text = ''
        specs_match = re.search(
            r'<div class="quick-specs">((?:\s*<div><strong>[^<]+</strong>[^<]+</div>)+)\s*</div>',
            block, re.DOTALL,
        )
        if specs_match:
            spec_items = re.findall(r'<div><strong>([^<]+)</strong>([^<]+)</div>', specs_match.group(1))
            if spec_items:
                specs_text = '\n'.join(
                    f'- **{label.strip()}**: {value.strip()}'
                    for label, value in spec_items
                )

        # Description (first <p> after price-line, before pros-cons)
        desc_text = ''
        # Find description by looking for <p> after price-line and before pros-cons
        desc_match = re.search(
            r'<div class="price-line">.*?</div>\s*<p>(.*?)</p>',
            block, re.DOTALL,
        )
        if desc_match:
            desc_text = clean_inline(desc_match.group(1))

        # Pros (inside pros-cons)
        pros_text = ''
        pros_match = re.search(
            r'<div class="pros">.*?<h4>([^<]+)</h4>\s*<ul>(.*?)</ul>',
            block, re.DOTALL,
        )
        if pros_match:
            pros_label = pros_match.group(1).strip()
            pros_items = re.findall(r'<li>([^<]+)</li>', pros_match.group(2))
            pros_text = '\n\n**' + pros_label + '**\n\n' + '\n'.join(
                f'- {clean_inline(item.strip())}'
                for item in pros_items
            )

        # Cons (inside pros-cons)
        cons_text = ''
        cons_match = re.search(
            r'<div class="cons">.*?<h4>([^<]+)</h4>\s*<ul>(.*?)</ul>',
            block, re.DOTALL,
        )
        if cons_match:
            cons_label = cons_match.group(1).strip()
            cons_items = re.findall(r'<li>([^<]+)</li>', cons_match.group(2))
            cons_text = '\n\n**' + cons_label + '**\n\n' + '\n'.join(
                f'- {clean_inline(item.strip())}'
                for item in cons_items
            )

        # Compose the section
        parts = [f'\n\n---\n\n### {title}\n']
        if price:
            parts.append(f'\n**Price:** {price}\n')
        if specs_text:
            parts.append(f'\n**Specs:**\n\n{specs_text}\n')
        if desc_text:
            parts.append(f'\n{desc_text}\n')
        if pros_text:
            parts.append(f'{pros_text}\n')
        if cons_text:
            parts.append(f'{cons_text}\n')
        parts.append('\n')

        return ''.join(parts)

    # Match each product-card — everything from <div class="product-card"> up to either:
    # - the next <div class="product-card"> (start of next card)
    # - or a section-ending tag (h2, hr, or the closing of article body)
    md = re.sub(
        r'<div class="product-card">.*?(?=<div class="product-card">|</article>|<h2\s|<hr\s)',
        extract_product_card,
        md,
        flags=re.DOTALL,
    )

    # 4. Convert headers
    md = re.sub(r'<h2[^>]*>(.*?)</h2>', lambda m: '\n\n## ' + clean_inline(m.group(1)) + '\n\n', md)
    md = re.sub(r'<h3[^>]*>(.*?)</h3>', lambda m: '\n\n### ' + clean_inline(m.group(1)) + '\n\n', md)
    md = re.sub(r'<h4[^>]*>(.*?)</h4>', lambda m: '\n\n#### ' + clean_inline(m.group(1)) + '\n\n', md)

    # 5. Convert blockquotes
    md = re.sub(
        r'<blockquote[^>]*>(.*?)</blockquote>',
        lambda m: '\n\n> ' + clean_inline(m.group(1)).strip() + '\n\n',
        md,
        flags=re.DOTALL,
    )

    # 6. Convert unordered lists
    def replace_ul(match):
        items = re.findall(r'<li[^>]*>(.*?)</li>', match.group(1), re.DOTALL)
        if not items:
            return match.group(0)
        return '\n\n' + '\n'.join(
            f'- {clean_inline(item.strip())}'
            for item in items
        ) + '\n\n'
    md = re.sub(r'<ul[^>]*>(.*?)</ul>', replace_ul, md, flags=re.DOTALL)

    # 7. Convert paragraphs (after all nested tags extracted)
    def replace_p(match):
        content = clean_inline(match.group(1)).strip()
        if not content:
            return ''
        return f'\n\n{content}\n\n'
    md = re.sub(r'<p[^>]*>(.*?)</p>', replace_p, md, flags=re.DOTALL)

    # 8. Strip remaining HTML tags
    md = re.sub(r'<[^>]+>', '', md)

    # 9. Convert <br> to line breaks
    md = re.sub(r'<br\s*/?>', '  \n', md)

    # 10. Clean up whitespace
    md = re.sub(r'\n{3,}', '\n\n', md)
    md = '\n'.join(line.rstrip() for line in md.split('\n'))

    return md.strip()


def clean_inline(text):
    """Strip inline HTML tags, normalize whitespace, decode entities."""
    # Convert <strong>bold</strong> → **bold**
    text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
    text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text, flags=re.DOTALL)
    # Convert <em>italic</em> → *italic*
    text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
    text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text, flags=re.DOTALL)
    # Convert <a href="URL">text</a> → [text](URL)
    text = re.sub(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL)
    # Strip remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode common HTML entities
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    text = text.replace('&mdash;', '—')
    text = text.replace('&nbsp;', ' ')
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text
