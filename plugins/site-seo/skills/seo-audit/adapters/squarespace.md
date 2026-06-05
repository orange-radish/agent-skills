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
