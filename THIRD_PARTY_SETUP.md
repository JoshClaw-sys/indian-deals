# Third-Party Publishing Setup

Indian Deals articles auto-cross-post to 4 platforms to amplify SEO and capture traffic from day 1.

## What's already wired (in `publish_third_party.py`)

| Platform | API | Free? | Status |
|---|---|---|---|
| **Medium** | REST | Yes | ✅ Built, needs token |
| **LinkedIn** | REST (ugcPosts) | Yes (free tier) | ✅ Built, needs OAuth |
| **Hashnode** | GraphQL | Yes | ✅ Built, needs token |
| **Dev.to** | REST | Yes | ✅ Built, needs API key |

The auto-publish cron calls `publish_third_party.py` after every article ships. Any platform without credentials is **gracefully skipped** (logs a warning, doesn't fail the build).

## How to get the credentials

### 1. Medium (~5 min, easiest)

1. Go to https://medium.com/me/settings/security
2. Scroll to "Integration tokens"
3. Click "Get integration token" → name it "indian-deals-bot"
4. Copy the token (starts with `eyJ...`)
5. Add to your shell env:
   ```bash
   echo 'export MEDIUM_TOKEN="eyJ..."' >> ~/.bashrc
   source ~/.bashrc
   ```

**Limits:** ~20 posts/day. Each post can be up to ~100KB of HTML.

### 2. LinkedIn (~15 min, hardest)

LinkedIn's API requires an approved developer app:

1. Go to https://www.linkedin.com/developers/apps
2. Click "Create app" → name "Indian Deals"
3. Request access to:
   - `w_member_social` (post on behalf of user)
   - `openid profile email` (basic identity)
4. Verify the app via your LinkedIn profile
5. In "Auth" tab, add redirect URL: `http://localhost:8765/callback`
6. Use OAuth 2.0 authorization code flow with PKCE:
   ```
   https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:8765/callback&scope=w_member_social%20openid%20profile%20email
   ```
7. Exchange the code for an access token
8. Get your author URN:
   ```bash
   curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" https://api.linkedin.com/v2/userinfo | jq .sub
   ```
   This returns your URN like `urn:li:person:abc123`
9. Add to env:
   ```bash
   export LINKEDIN_ACCESS_TOKEN="AQV..."
   export LINKEDIN_AUTHOR_URN="urn:li:person:abc123"
   ```

**Limits:** 100 posts/day per user.

### 3. Hashnode (~10 min, medium)

1. Go to https://hashnode.com/settings/developer
2. Generate a "Personal Access Token"
3. Create a publication (or use your personal blog):
   - Go to https://hashnode.com → "Create publication"
4. Get the publication ID (you'll see it in the URL after creation)
5. Add to env:
   ```bash
   export HASHNODE_TOKEN="your-token"
   export HASHNODE_PUBLICATION_ID="your-pub-id"
   ```

**Limits:** 100 posts/day per token.

### 4. Dev.to (~3 min, easiest)

1. Go to https://dev.to/settings/extensions
2. Generate an "API key" (note: this is the older way; for new accounts use https://dev.to/settings/account → "DEV Community API Key")
3. Add to env:
   ```bash
   export DEVTO_API_KEY="your-key"
   ```

**Limits:** 10 articles/day.

## Where to set the credentials

For the auto-publish cron (running daily at 9 AM IST), set them in `~/.bashrc`:

```bash
echo '
# Indian Deals — third-party publishing
export MEDIUM_TOKEN="..."
export LINKEDIN_ACCESS_TOKEN="..."
export LINKEDIN_AUTHOR_URN="..."
export HASHNODE_TOKEN="..."
export HASHNODE_PUBLICATION_ID="..."
export DEVTO_API_KEY="..."
' >> ~/.bashrc
```

The cron job already loads `~/.bashrc` via the `workdir` + bash environment.

## How it works (the canonical-URL strategy)

When an article is published to any third-party platform, the `canonicalUrl` field is set to your Indian Deals URL. This means:

- ✅ Google knows the original is on your site → all SEO juice flows to your domain
- ✅ Each platform version is a duplicate but doesn't compete for ranking
- ✅ You get traffic from Medium/LinkedIn/Hashnode/Dev.to readers
- ✅ Each platform's audience sees the article in their feed

Without canonicalUrl, Google would either (a) pick one platform as canonical and ignore yours, or (b) split ranking signals between 5 versions. We avoid both.

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

This will publish all 10 currently-live articles to whatever platforms have credentials configured.
