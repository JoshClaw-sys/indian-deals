# Third-Party Publishing Setup

Indian Deals articles auto-cross-post to multiple platforms to amplify SEO and capture traffic from day 1.

## Current platform status (verified 2026-08-01)

| Platform | Status | Free? | Notes |
|---|---|---|---|
| **Dev.to** | ✅ Active | Yes | API key works. 5-min title cooldown between posts. Bot detection requires User-Agent header. |
| **Medium** | ❌ API access closed | — | Medium's API is now partner-only (not self-service). Re-evaluate when they reopen. |
| **LinkedIn** | ⏸️ Skipped per user | — | OAuth setup is involved; user opted out. |
| **Hashnode** | ❌ Free API closed | — | Hashnode closed free-tier GraphQL API in May 2026 — requires $15/mo Pro plan now. |

The auto-publish cron calls `publish_third_party.py` after every article ships. Any platform without credentials or with closed APIs is **gracefully skipped** (logs a warning, doesn't fail the build).

## What got fixed in this session

1. **Dev.to 403 Forbidden Bots**: Dev.to detects Python's urllib as a bot. Fixed by adding a custom User-Agent header.
2. **Dev.to V1 API**: Endpoint requires `Accept: application/vnd.forem.api-v1+json` header. Added.
3. **Dev.to tag rules**: Tags must be alphanumeric only (no dashes/spaces). Now sanitized automatically.
4. **Dev.to canonical URL duplicates**: Each cross-post gets a `?utm_source=devto` query param to avoid the "canonical url already taken" error.
5. **Dev.to title cooldown**: Same title can't be posted twice within 5 minutes. The script sleeps 35s between each platform and 35s between articles.

## How to get Dev.to credentials (already configured)

1. Go to https://dev.to/settings/extensions
2. Click "Generate API Key" (or https://dev.to/settings/account → "DEV Community API Key")
3. Set in `~/.bashrc`:
   ```bash
   export DEVTO_API_KEY="your-key-here"
   ```

## How to get Hashnode credentials (requires Pro plan)

Skip unless willing to pay $15/mo:
1. Upgrade to Pro: https://hashnode.com/settings/billing
2. Generate token: https://hashnode.com/settings/developer
3. Create publication: https://hashnode.com → "Create publication"
4. Get publication ID from the publication URL
5. Set in `~/.bashrc`:
   ```bash
   export HASHNODE_TOKEN="your-token"
   export HASHNODE_PUBLICATION_ID="your-pub-id"
   ```

## How to get Medium credentials (requires partner access)

**Skip for now.** Medium closed self-service API access in 2024. To get API access you need to apply to their partner program (invite-only). For most publishers, importing articles via Medium's web UI is the only option — not automatable.

## Where to set the credentials

For the auto-publish cron (running daily at 9 AM IST), set them in `~/.bashrc`:

```bash
echo '
# Indian Deals — third-party publishing
export DEVTO_API_KEY="..."
export HASHNODE_TOKEN="..."
export HASHNODE_PUBLICATION_ID="..."
' >> ~/.bashrc
```

The cron job loads `~/.bashrc` via the bash environment.

## How it works (the canonical-URL strategy)

When an article is published to any third-party platform, the `canonicalUrl` field is set to your Indian Deals URL (with a `?utm_source=...` query param to avoid duplicates). This means:

- ✅ Google knows the original is on your site → all SEO juice flows to your domain
- ✅ Each platform version is a duplicate but doesn't compete for ranking
- ✅ You get traffic from Dev.to (and Hashnode, when enabled) readers
- ✅ Each platform's audience sees the article in their feed

Without canonicalUrl, Google would either (a) pick one platform as canonical and ignore yours, or (b) split ranking signals between multiple versions. We avoid both.

## Re-publishing (e.g. article rewrite)

```bash
cd ~/projects/indian-deals
python3 publish_third_party.py <slug> --force
```

The `--force` flag re-posts even if already published. Useful when you've updated an article and want the third-party versions updated too.

## Tracking

Every publish attempt is logged to `publish_log.json`:

```bash
cat publish_log.json | python3 -m json.tool
```

## Backfilling (publish everything that's already on the site)

```bash
cd ~/projects/indian-deals
python3 publish_third_party.py --all
```

Takes ~10 minutes for 13 articles due to Dev.to's rate limits (35s sleep between each).

## Future platforms to add (when APIs open)

- **Substack Notes** — when they add an API
- **Ghost** — self-hosted newsletter with native API
- **WordPress.com** — if we set up a secondary blog there
- **Telegram channel** — instant broadcast, no API limits (uses bot)
- **Twitter/X** — shareable cards, but limited text. Useful for hooks.

