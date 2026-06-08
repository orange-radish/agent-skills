# Adapter: Wix

## Enrichment
Wix has **no official MCP or public read API** for SEO settings — the live crawl
carries the audit. Do not attempt API/MCP calls for a Wix site.

**Important crawl caveat:** Wix sites are heavily **JavaScript-rendered**. Wix
serves a prerendered version to crawlers, but a plain `curl`/`urllib` fetch may
capture **less content than a browser renders** (lower `word_count`, missing
later-loaded sections). Before raising "thin content / not crawlable" findings on
Wix, note this rendering caveat — verify in a browser's "View Source" (or a
prerender check) rather than asserting from `word_count` alone.

## Where fixes get applied (paste instructions for the report)
- **Title & meta description** — per page in the Wix Editor: **Page menu → SEO
  (Google) / "SEO Basics" tab** → *Title Tag* / *Meta Description*. Site-wide
  defaults: **Settings → SEO → SEO Settings / SEO Dashboard** (title format
  tokens). (Wix Studio: the page **SEO** panel.)
- **Open Graph / social** — same page SEO panel → **Social Share** tab (image,
  title, description).
- **Canonical** — Wix sets a canonical by default; override per page in the page
  SEO panel → **Advanced SEO → Canonical tag**.
- **Indexing** — per page SEO panel → **"Let search engines index this page"**
  toggle (this is how a Wix page becomes noindex — check `meta_robots`).
- **JSON-LD structured data** — Wix supports **custom structured data**: page SEO
  panel → **Advanced SEO → Structured Data Markup** (paste a JSON-LD block per
  page). Site-wide blocks (Organization, WebSite) can also go in **Settings →
  Custom Code → add code to `<head>`** on all pages. Wix auto-emits some schema —
  **check `jsonld_types` before proposing duplicates.**
- **robots.txt** — editable: **Settings → SEO → SEO Tools → Robots.txt Editor**.
  (Unlike Squarespace, Wix lets you edit it — so AI-crawler posture changes ARE
  possible here.)
- **sitemap.xml** — auto-generated at `/sitemap.xml`; not directly editable.
  Verify it resolves.
- **llms.txt** — not natively hostable; note it would require an external host /
  proxy.
- **Image alt text** — select the image → **Settings → "What's in the image?"
  (alt text)**.

Note that some SEO features (custom canonical, structured data) require a
**Premium plan with a connected domain**; flag that where relevant.

## Security headers (what Wix can vs. cannot set)
Wix is a **fully managed platform with no response-header control** — same honest
caveat as Squarespace:
- **Cannot** set `Content-Security-Policy`, `X-Frame-Options`, `Referrer-Policy`,
  `Permissions-Policy`, or custom headers. Wix **Custom Code** injects markup into
  the HTML `<head>` (or body); it does **not** set HTTP response headers. (A
  `<meta http-equiv>` CSP is a weak partial substitute, not a real fix.)
- **HSTS / TLS** are managed by Wix (modern TLS + HSTS generally provided), not
  tunable.
- **Cookies** are set by Wix; their flags aren't owner-configurable.
For most missing-header findings on Wix, the correct recommendation is to
**report it as a platform limitation**, not a settings change. Don't prescribe a
header Wix can't set.

## Links & redirects
- **Internal broken links** — fix the link in the Editor; for moved/renamed pages
  add a 301 via **Settings → SEO → URL Redirect Manager** (`/old-url → /new-url`).
- **`http://` internal links** — update links to `https://` or site-relative.
  Wix serves HTTPS and redirects http→https at the platform level.
- **Redirect chains** — point the URL Redirect Manager rule directly at the final
  URL to avoid hops.
- `www`/non-`www` canonicalization is handled by Wix.
