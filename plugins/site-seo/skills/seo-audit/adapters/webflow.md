# Adapter: Webflow

## Enrichment (optional, read-only via the Webflow MCP)

If the Webflow MCP is connected, use it to enrich the audit — never to write.
If it is **not** connected, skip this section entirely; the live crawl already
carries the full audit. Do not block on the MCP and do not ask the user to
connect it unless they want the configured-vs-rendered comparison.

Useful read-only MCP calls (names vary slightly by MCP version — discover them
via tool search for "webflow pages / sites / collections"):
- **list sites** → resolve the site id.
- **list pages** → enumerate pages + slugs; cross-check against `sitemap.xml`
  (pages missing from the sitemap, or sitemap URLs with no page).
- **get page metadata / SEO settings** → the *configured* title, meta
  description, and Open Graph values. Compare against the rendered inventory:
  - configured value set but rendered tag missing → likely an unpublished change
    or a template override; flag it.
  - rendered ≠ configured → something downstream is rewriting it.
- **list CMS collections + fields** → for templated/Collection pages, map fields
  to JSON-LD properties so the proposed `Article`/`Product` markup can reference
  the right dynamic fields.
- **list registered custom code / scripts** → see whether JSON-LD is already
  injected site-wide vs per-page (explains rendered findings).

## Where fixes get applied (paste instructions for the report)

Webflow has **native SEO fields** — prefer them over custom code for the basics:

- **Title & meta description** — Webflow Designer → open the page → **Page
  Settings (gear)** → **SEO Settings** → *Title Tag* / *Meta Description*. For
  Collection (templated) pages, set these in the **Collection page settings**
  using dynamic field bindings.
- **Open Graph** — same Page Settings panel → **Open Graph Settings** (title,
  description, image). There's a "same as SEO" toggle.
- **Canonical / hreflang / custom meta** — Page Settings → **Custom Code** →
  *Inside <head> tag*, or site-wide in **Project Settings → Custom Code → Head Code**.
- **JSON-LD structured data** — paste each `<script type="application/ld+json">`
  block into **Page Settings → Custom Code → Inside <head> tag** (per page), or
  **Project Settings → Custom Code → Head Code** for site-wide blocks
  (Organization, WebSite). For Collection pages, embed the script in the
  Collection page template and bind dynamic fields. *Custom code requires a paid
  Site plan and a republish to go live.*
- **robots.txt** — **Project Settings → SEO → Indexing → robots.txt**.
- **sitemap.xml** — **Project Settings → SEO → Sitemap** (auto-generated; toggle
  on). Webflow does not support a hosted `/llms.txt` natively — note that it must
  be added via a reverse proxy / Cloudflare Worker, or hosted elsewhere.
- **Image alt text** — set per asset in the **Asset panel** or on the image
  element's settings.

Always remind the reader: changes require **Publish** to appear on the live site,
and JSON-LD/custom-code embeds need a paid plan.
