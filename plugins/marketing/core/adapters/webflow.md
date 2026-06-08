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

**Prefer Webflow's own audit for the config-side view.** If the user has the
`webflow-skills` plugin installed and the Webflow MCP authenticated, don't
hand-roll deep CMS/structure analysis via raw MCP calls — the orchestrator fans
out to `webflow-skills:site-audit` (and `asset-audit` report-only,
`accessibility-audit`) per `../procedures/webflow-native.md`, which cover the
configured data model far more thoroughly. Use the raw MCP calls above only for
the quick configured-vs-rendered cross-check when that fan-out isn't available.

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

## Security headers (what Webflow can vs. cannot set)
Webflow's header control is **limited** — it is not a general reverse proxy:
- **Can set via Project Settings → Hosting → Custom security headers** (on paid
  Site plans / Enterprise): a curated set including `Content-Security-Policy`,
  `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`,
  `Permissions-Policy`, and `Strict-Transport-Security` for the hosted domain.
  Availability varies by plan — verify what the account exposes.
- **TLS / HSTS** are managed by Webflow hosting; you can't tune cipher suites or
  protocol versions.
- **Cannot** set arbitrary per-route or per-asset response headers the way a
  self-hosted server or a Cloudflare Worker in front of the site could.
- **Cookies** are set by Webflow/third-party scripts, not by you; you can't add
  `Secure`/`HttpOnly`/`SameSite` flags directly — the fix is to remove/replace
  the script.
For anything Webflow can't set, the honest recommendation is to **front the site
with a reverse proxy / Cloudflare** (which can inject any header) or note it as a
platform limitation. Never tell the reader to set a header Webflow can't.

## Links & redirects
- **Internal broken links** — fix the link in the Designer (the element's link
  settings) or restore/redirect the missing page.
- **301 redirects** — **Project Settings → Publishing → 301 Redirects** (path →
  path). Use to repair links that 404 and to collapse redirect chains.
- **`http://` internal links** — edit the element link to `https://` or a
  root-relative path (`/page`) so it inherits the secure scheme.
- Webflow auto-handles `www`/non-`www` canonicalization at the hosting level.
