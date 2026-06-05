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
- **llms.txt** — serve a curated `/llms.txt` (see the seo-audit skill's
  `templates/llms.txt`).
- **Image alt text** — add meaningful `alt` to content images; empty `alt=""` for
  decorative ones.

## Security headers (self-hosted / proxied — full control)
Unlike the hosted builders, a self-hosted or proxied site can set every response
header. Recommend configuring them at the web server / CDN / reverse proxy:
- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (add `preload`
  once you're sure).
- `Content-Security-Policy` (start in report-only mode, then enforce).
- `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN` (or CSP
  `frame-ancestors`), `Referrer-Policy: strict-origin-when-cross-origin`,
  a least-privilege `Permissions-Policy`.
- Cookies: add `Secure; HttpOnly; SameSite=Lax` (or stricter) to session cookies.
- TLS: disable TLS 1.0/1.1, prefer TLS 1.2+/1.3, keep the cert from expiring.
Name the actual server (nginx/Apache/Cloudflare) if the `Server` header reveals
it, and point to that server's header-setting mechanism.

## Links & redirects
- Fix broken internal links at the source; add `301` redirects for moved pages.
- Change `http://` internal links to `https://` or site-relative paths.
- Collapse redirect chains by linking directly to the final URL.
- Serve one canonical host (pick `www` or apex; 301 the other).

If you can identify the actual platform (Framer, WordPress, Wix, etc.) from the
HTML, name it in the report and give that platform's panel names where you know
them — but never guess paste paths you're unsure of; default to the `<head>` /
server-config descriptions above.
