#!/usr/bin/env python3
"""
Auto-content pipeline.

Reads a list of planned article topics from planned.json, generates the meta
+ body for each using the templates, then runs build.py.

Usage:
  python3 generate_content.py           # generate all planned articles
  python3 generate_content.py --count N  # generate first N from the list
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# Same model as before. In production this would be a fine-tuned model.
# For now, content is generated from the seed library below.

# The seed library: each entry has the meta + body content.
# New seeds are added by hand or by an LLM call.
SEED_LIBRARY = []

def load_planned():
    """Read planned.json — a list of {slug, category, target_keywords, status}."""
    planned = ROOT / "planned.json"
    if not planned.exists():
        return []
    return json.loads(planned.read_text())


def load_seed(slug):
    """Return the seed data for a slug, or None."""
    for s in SEED_LIBRARY:
        if s["slug"] == slug:
            return s
    return None


def main():
    planned = load_planned()
    todo = [p for p in planned if p.get("status") != "done"]
    if "--count" in sys.argv:
        idx = sys.argv.index("--count")
        n = int(sys.argv[idx + 1])
        todo = todo[:n]

    print(f"Found {len(todo)} planned articles to generate")

    # For each planned article, generate it
    for p in todo:
        slug = p["slug"]
        seed = load_seed(slug)
        if not seed:
            print(f"  ⚠ No seed for {slug} — skip")
            continue

        out_dir = ROOT / "articles" / slug
        out_dir.mkdir(parents=True, exist_ok=True)

        # Write meta.json
        meta_path = out_dir / "meta.json"
        meta_path.write_text(json.dumps(seed["meta"], indent=2, ensure_ascii=False))

        # Write body.html
        body_path = out_dir / "body.html"
        body_path.write_text(seed["body"])

        # Mark as done
        p["status"] = "done"

        print(f"  ✓ {slug}")

    # Save updated planned.json
    (ROOT / "planned.json").write_text(json.dumps(planned, indent=2, ensure_ascii=False))

    print(f"\n✅ Generated {len(todo)} articles")
    print("Run: python3 build.py")


if __name__ == "__main__":
    main()
