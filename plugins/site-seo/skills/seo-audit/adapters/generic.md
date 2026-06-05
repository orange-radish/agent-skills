# Adapter: generic (platform unknown / other)

Used when detection finds neither Webflow nor Squarespace (custom site, Framer,
WordPress, static site, etc.). The audit is unchanged — only the fix-paste
guidance becomes platform-neutral.

## Enrichment
None. There is no assumed API. The live crawl is the sole source.

## Where fixes get applied (generic instructions for the report)

Describe fixes in terms of the rendered output the crawler needs, and let the
reader map them to their stack:

- **Title & meta description** — ensure each page renders a unique `<title>` and
  `<meta name="description">` in the `<head>`. In most CMSs this is a per-page
  "SEO" field; in hand-built sites, edit the page template/head partial.
- **Open Graph / Twitter** — add `og:*` and `twitter:*` `<meta>` tags to `<head>`.
- **Canonical / hreflang** — add `<link rel="canonical" href="...">` (absolute)
  and reciprocal `<link rel="alternate" hreflang="...">` if multilingual.
- **JSON-LD structured data** — add each `<script type="application/ld+json">`
  block to the `<head>` (site-wide blocks like Organization/WebSite in the global
  template; page-specific blocks in the page template).
- **robots.txt** — serve a `/robots.txt` with a `Sitemap:` line and intended
  crawler rules.
- **sitemap.xml** — generate and serve `/sitemap.xml` with absolute canonical
  URLs; reference it from `robots.txt`.
- **llms.txt** — serve a curated `/llms.txt` (see `templates/llms.txt`).
- **Image alt text** — add meaningful `alt` to content images; empty `alt=""` for
  decorative ones.

If you can identify the actual platform (Framer, WordPress, Wix, etc.) from the
HTML, name it in the report and give that platform's panel names where you know
them — but never guess paste paths you're unsure of; default to the `<head>`
description above.
