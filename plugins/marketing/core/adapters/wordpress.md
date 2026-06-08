# Adapter: WordPress

WordPress is **plugin- and host-dependent** — *where* a setting lives depends on
which SEO/security/redirect plugins are installed and whether the site is
self-hosted or managed (WordPress.com / WP Engine / etc.). Detect the SEO plugin
from the rendered HTML and tailor the fix locations:
- **Yoast SEO** — `<!-- This site is optimized with the Yoast SEO plugin ... -->`
  comment wrapping the `<head>` SEO block.
- **Rank Math** — `<!-- Search Engine Optimization by Rank Math ... -->` comment.
- **All in One SEO (AIOSEO)** — `<!-- All in One SEO ... -->` comment.
Name the detected plugin in the report; if none is detected, SEO output is the
theme's and fixes are theme/`functions.php`-level.

## Enrichment (read-only, often available)
WordPress usually exposes a public **REST API** for *published* content with no
auth — use it to enrich (never to write):
- `GET /wp-json/` → confirms the API is on; lists namespaces.
- `GET /wp-json/wp/v2/pages?per_page=100&_fields=link,title,status` and
  `.../posts?...` → enumerate pages/posts; cross-check against the sitemap and the
  crawled set (pages in one but not the other).
- The API may be disabled, auth-walled, or rate-limited — if it 401s/404s, skip
  and rely on the crawl. Don't block on it.

## Where fixes get applied (paste instructions for the report)
- **Title & meta description** — per post/page in the **SEO plugin meta box**
  below the editor (Yoast/Rank Math/AIOSEO → *SEO title* / *Meta description*).
  Site-wide templates: the plugin's **Titles & Metas / Search Appearance**
  settings. With no plugin, it's the theme's `wp_title`/`<title>` — recommend
  installing an SEO plugin.
- **Open Graph / social** — the same SEO plugin's **Social** tab (per-post
  override + site default image).
- **Canonical / custom meta / hreflang** — SEO plugins emit a canonical
  automatically (**check the inventory before flagging a missing canonical**);
  per-post override is in the plugin meta box (Advanced). hreflang needs a
  multilingual plugin (Polylang/WPML).
- **JSON-LD structured data** — Yoast and Rank Math **auto-emit a schema graph**
  (Organization/WebSite/WebPage/Article/BreadcrumbList). **Check `jsonld_types`
  first and do not propose duplicates** — instead recommend completing it in the
  plugin (e.g. set the Organization logo/social profiles in the plugin's
  Knowledge Graph settings). For types the plugin doesn't cover, add custom
  JSON-LD via a snippet plugin (WPCode) or the theme `header.php`.
- **robots.txt** — editable: a physical `robots.txt` at the web root, or via the
  SEO plugin (Yoast → Tools → File editor; Rank Math → General Settings → Edit
  robots.txt).
- **sitemap.xml** — Yoast/Rank Math generate `/sitemap_index.xml`; WordPress core
  generates `/wp-sitemap.xml`. Verify which is live and that it's referenced from
  robots.txt.
- **llms.txt** — self-hosted: drop a static `/llms.txt` at the web root (or a
  snippet/redirect). Managed plans may not allow arbitrary root files.
- **Image alt text** — Media Library → the image's **Alt Text** field, or the
  block editor's image settings.

Always name the detected SEO plugin (or its absence) so the reader knows which
panel to open, and note self-hosted vs. managed where it changes what's possible.

## Security headers (what WordPress can vs. cannot set)
Depends entirely on **hosting**:
- **Self-hosted** → **full control.** Set headers at the web server
  (nginx `add_header`, Apache `.htaccess`/`Header set`), at a CDN/proxy
  (Cloudflare), or via a plugin (e.g. "HTTP Headers", or security suites like
  Wordfence). Recommend `Content-Security-Policy`, `Strict-Transport-Security`,
  `X-Content-Type-Options: nosniff`, `X-Frame-Options`/CSP `frame-ancestors`,
  `Referrer-Policy`, `Permissions-Policy`. CSP is hard if the theme/plugins use
  inline scripts — start report-only.
- **Managed (WordPress.com, some hosts)** → header control may be **limited or
  unavailable**; check the host's docs or front with Cloudflare. Report the
  limitation rather than prescribing an impossible change.
- **Cookies** — WordPress sets `wordpress_*`/`wp-settings-*` cookies mainly for
  logged-in users; ensure session cookies are `Secure; HttpOnly` (the server/
  plugin layer), but on a brochure site there may be none for anonymous visitors.

## Links & redirects
- **Internal broken links** — fix in the block editor; for moved content add a
  301 via the **Redirection** plugin, Rank Math → Redirections, Yoast Premium, or
  `.htaccess`/nginx rules (self-hosted).
- **`http://` internal links** — update links to `https://` (a search-replace
  plugin like Better Search Replace can fix legacy http:// in post content).
- **Redirect chains** — collapse by pointing the redirect rule directly at the
  final URL.
- **Canonical host** — enforce one host (`www` vs apex, https) at the server/CDN;
  WordPress's Site Address (Settings → General) should match.
