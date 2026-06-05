# Criteria: technical SEO

Site-level and HTTP-level checks. These read the per-page inventories plus the
fetched `robots.txt` and `sitemap.xml` (see `procedures/discover-urls.md`).

## robots.txt (fetched separately)
- **Present and reachable** at `/robots.txt`. A 404 is tolerable (everything is
  allowed by default) but a draft `robots.txt` is recommended → **P2** if absent.
- **Not blocking the whole site** — a `Disallow: /` under `User-agent: *` on a
  site that should rank is a **P0**. Verify it's not a leftover staging rule.
- **References the sitemap** — should contain a `Sitemap:` line with the absolute
  sitemap URL. Missing → **P2**.
- (AI-crawler directives are judged in `criteria/ai-discoverability.md`.)

## sitemap.xml (fetched separately)
- **Present** at `/sitemap.xml` (or referenced from robots.txt). Missing → **P1**.
- **Matches reality** — URLs in the sitemap should return 200 (not redirect or
  404). Compare against the crawled inventories: pages that exist but are absent
  from the sitemap → **P2**; sitemap URLs that 404/redirect → **P1**.
- **Canonical, absolute URLs** — no `http://` or relative entries → **P2**.

## HTTP status & redirects (`http_status`, `redirect_chain`, `fetched_url`)
- **200 for in-scope pages** — any in-scope page returning 4xx/5xx → **P1** (or
  **P0** if it's a key landing page).
- **Clean redirects** — `redirect_chain` length > 1 (a redirect hop chain) →
  **P2**; a redirect that lands on a 404 → **P1**.
- **HTTPS** — `fetched_url` should be `https://`. An http:// final URL → **P1**.

## Canonicalization across the site
- **One canonical host** — all pages resolve to a single host+scheme (no mix of
  `www`/non-`www` or `http`/`https` serving 200s). Mixed → **P1**.

## hreflang (`hreflang`)
- **Only if multilingual** — if `hreflang` entries exist they must be reciprocal
  and include an `x-default`. Malformed/one-way hreflang → **P2**. If the site is
  single-language, this section does not apply.

## Severity
- **P0** — site-wide deindex risk (robots `Disallow: /`).
- **P1** — missing sitemap, broken key pages, mixed canonical host, http final URL.
- **P2** — redirect chains, sitemap drift, missing robots/sitemap reference.
