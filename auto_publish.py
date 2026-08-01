#!/usr/bin/env python3
"""
Auto-publish pipeline for Indian Deals.

Reads planned.json, picks the next N articles to write, generates them from
seed libraries or LLM (when wired), runs the build, commits, pushes.

Designed to run as a cron job daily. Writes 2-3 articles per day.
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent
PLANNED = ROOT / "planned.json"


def get_todo(limit=3):
    """Get next N articles from the roadmap that aren't done yet."""
    planned = json.loads(PLANNED.read_text())
    todo = [p for p in planned if p.get("status") != "done"][:limit]
    return planned, todo


def mark_done(planned, slugs_done):
    """Mark items as done in planned.json."""
    for p in planned:
        if p["slug"] in slugs_done:
            p["status"] = "done"
            p["done_at"] = datetime.now(timezone.utc).isoformat()
    PLANNED.write_text(json.dumps(planned, indent=2, ensure_ascii=False))


def has_seed(slug):
    """Check if a seed library exists for this slug. Seeds are added by
    hand or by an LLM call (TODO: wire LLM generation)."""
    seed_path = ROOT / "seeds" / f"{slug}.json"
    return seed_path.exists()


def load_seed(slug):
    return json.loads((ROOT / "seeds" / f"{slug}.json").read_text())


def write_article(slug, seed):
    out_dir = ROOT / "articles" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "meta.json").write_text(json.dumps(seed["meta"], indent=2, ensure_ascii=False))
    (out_dir / "body.html").write_text(seed["body"])


def run_build():
    """Run the build script."""
    res = subprocess.run(["python3", "build.py"], cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"BUILD FAILED:\n{res.stderr}")
        sys.exit(1)
    # Print last few lines
    print(res.stdout.split("\n")[-3])


def git_commit_and_push(message):
    """Commit and push changes."""
    subprocess.run(["git", "add", "-A"], cwd=ROOT)
    res = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0 and "nothing to commit" not in res.stdout + res.stderr:
        print(f"COMMIT FAILED:\n{res.stderr}")
        return False
    res = subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"PUSH FAILED:\n{res.stderr}")
        return False
    return True


def main():
    print("=" * 50)
    print("Indian Deals — auto-publish pipeline")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 50)

    planned, todo = get_todo(limit=3)
    if not todo:
        print("No articles in the queue. Add to planned.json.")
        return

    written = []
    skipped = []
    for p in todo:
        slug = p["slug"]
        if not has_seed(slug):
            skipped.append(slug)
            print(f"  ⚠ No seed for {slug} — skipping")
            continue
        seed = load_seed(slug)
        write_article(slug, seed)
        written.append(slug)
        print(f"  ✓ {slug}")

    if not written:
        print(f"\nNo articles written. {len(skipped)} skipped (no seed).")
        print("To add seeds: drop JSON files in seeds/<slug>.json with {meta, body}.")
        return

    print(f"\nBuilding site ({len(written)} new articles)...")
    run_build()

    print("\nCommitting + pushing...")
    msg = f"Auto-publish {len(written)} articles: {', '.join(written)}"
    if git_commit_and_push(msg):
        mark_done(planned, written)
        print(f"\n✅ Published {len(written)} articles, marked as done in planned.json")
        # Ping search engines so new articles get indexed faster
        try:
            from ping_search_engines import ping_google, ping_bing_indexnow
            sitemap = "https://joshclaw-sys.github.io/indian-deals/sitemap.xml"
            print("\nPinging search engines...")
            for label, code, msg in [ping_google(sitemap), ping_bing_indexnow(sitemap)]:
                icon = "✓" if code == 200 else "✗"
                print(f"  {icon} {label}: {code}")
        except Exception as e:
            print(f"  ⚠ Ping failed (non-blocking): {e}")

        # Cross-post to third-party platforms (Medium, LinkedIn, Hashnode, Dev.to)
        # Will gracefully skip any platform whose credentials aren't set yet.
        try:
            from publish_third_party import publish_one
            print("\nCross-posting to third-party platforms...")
            for slug in written:
                publish_one(slug)
        except Exception as e:
            print(f"  ⚠ Third-party publishing failed (non-blocking): {e}")
    else:
        print(f"\n⚠ Build succeeded but git push failed")


if __name__ == "__main__":
    main()
