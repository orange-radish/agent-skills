# Adapter: Squarespace

## Enrichment

Squarespace has **no official MCP or public read API** for page SEO settings, so
there is no API enrichment step. The live crawl carries the entire audit. Do not
attempt MCP calls for a Squarespace site.

(If the user has the site's content in another connected system — e.g. a CMS
export — you may use it to fill JSON-LD facts, but the rendered HTML remains
ground truth.)

## Where fixes get applied (paste instructions for the report)

- **Title & meta description** — per page: **Pages panel → hover the page →
  gear (⚙) → SEO tab** → *SEO Title* / *SEO Description*. Site-wide title format:
  **Settings → SEO → set the Site Title / Search Engine Description** and the
  title format tokens.
- **Open Graph / social image** — **Settings → Social Sharing** for the default
  image; per-page social image is set in the page's **gear → Social Image**.
- **Canonical / custom meta / hreflang** — Squarespace sets canonical
  automatically; custom meta tags go in **Settings → Advanced → Code Injection →
  Header** (site-wide), or per page via **page gear → Advanced → Page Header Code
  Injection**.
- **JSON-LD structured data** — paste each `<script type="application/ld+json">`
  block into **Settings → Advanced → Code Injection → Header** for site-wide
  blocks (Organization, WebSite), or per page via **page gear → Advanced → Page
  Header Code Injection**. Inside a blog/page body you can also use a **Code
  Block**. *Code Injection requires a Business plan or higher.* Note: Squarespace
  already emits some JSON-LD automatically (e.g. `BlogPosting` on blog posts) —
  check the inventory's `jsonld_types` before proposing duplicates.
- **robots.txt** — Squarespace generates `robots.txt` automatically and it is
  **not directly editable**. Per-page indexing is controlled by **page gear →
  SEO → "Hide this page from search engine results"**. To influence AI-crawler
  access you generally cannot edit `robots.txt`; note this limitation in the
  report rather than proposing a `robots.txt` edit.
- **sitemap.xml** — auto-generated at `/sitemap.xml`; not editable. Verify it
  resolves.
- **llms.txt** — not natively hostable; note it would require an external host /
  proxy.
- **Image alt text** — set in the image block: **edit image → click the image →
  add alt text** (or the filename is used as a fallback).

Always remind the reader which changes require a **Business plan** (Code
Injection) and that Squarespace controls `robots.txt`/`sitemap.xml`
automatically.

## Security headers (what Squarespace can vs. cannot set)
Squarespace gives site owners **almost no response-header control** — this is
the key honest caveat:
- **Cannot** set `Content-Security-Policy`, `X-Frame-Options`, `Referrer-Policy`,
  `Permissions-Policy`, or custom headers. Code Injection adds markup to the HTML
  `<head>`; it does **not** set HTTP response headers. (A `<meta http-equiv>` CSP
  is a weak, partial substitute and worth mentioning, not a real fix.)
- **HSTS / TLS** are managed by Squarespace; HSTS and a modern TLS config are
  generally provided, but not tunable.
- **Cookies** are set by Squarespace; their flags aren't owner-configurable.
So for most missing-header findings on Squarespace, the correct recommendation
is: **report it as a platform limitation** (or "would require moving off
Squarespace / fronting with a proxy"), not a settings change. Don't prescribe a
header Squarespace can't set.

## Links & redirects
- **Internal broken links** — fix the link in the editor, or add a redirect:
  **Settings → Advanced → URL Mappings** (`/old -> /new 301`).
- **`http://` internal links** — edit the link to `https://` or a site-relative
  path. Squarespace serves HTTPS and redirects http→https at the platform level.
- **301 redirects / renamed pages** — use **URL Mappings** to repair links that
  now 404 and to collapse redirect chains.
- `www`/non-`www` canonicalization is handled by Squarespace.
