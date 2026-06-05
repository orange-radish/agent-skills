# Procedure: discover URLs to audit

Goal: produce the list of in-scope page URLs, plus fetch `robots.txt` and
`sitemap.xml` for the technical/AI criteria.

## Scope
- **Explicit pages given** (command args or skill input) → audit exactly those;
  skip discovery. Still fetch `robots.txt` / `sitemap.xml` for site-level checks.
- **No pages given** → whole-site discovery below.

## 1. robots.txt and sitemap
```sh
BASE="https://example.com"   # scheme + host, no trailing path
curl -sL --max-time 15 -A "site-audit/1.0" "$BASE/robots.txt"  -o robots.txt  -w "%{http_code}\n"
curl -sL --max-time 15 -A "site-audit/1.0" "$BASE/sitemap.xml" -o sitemap.xml -w "%{http_code}\n"
curl -sL --max-time 15 -A "site-audit/1.0" "$BASE/llms.txt"    -o llms.txt    -w "%{http_code}\n"
```
Record each status. If `robots.txt` contains a `Sitemap:` line pointing
elsewhere, fetch that instead.

## 2. Extract page URLs from the sitemap (preferred)
```sh
grep -oE '<loc>[^<]+</loc>' sitemap.xml | sed -E 's/<\/?loc>//g'
```
Handle sitemap **index** files (a `<sitemap>` list of child sitemaps): fetch each
child and union their `<loc>` entries. De-duplicate. This is the primary URL
source.

## 3. Adapter enrichment (Webflow only)
If the active adapter is Webflow and the MCP is connected, also list pages via
the MCP (see `adapters/webflow.md`) and union them with the sitemap set —
surface any page present in one source but not the other as a finding.

## 4. Fallback: crawl the homepage
If there is no usable sitemap and no MCP page list, fetch the homepage and
extract same-host links from nav/footer:
```sh
curl -sL --max-time 15 -A "site-audit/1.0" "$BASE/" \
  | grep -oE 'href="[^"]+"' | sed -E 's/href="//; s/"//' \
  | grep -E "^(/|$BASE)" | sort -u
```
Resolve relative links against `$BASE`, drop fragments/asset URLs, keep HTML
pages. This is a shallow fallback — note in the report that coverage is
homepage-link-depth only, not exhaustive.

## 5. Scope the discovered set (which URLs to actually audit)
The raw URL set can include many low-value, template-generated pages. Apply this
deterministic heuristic so runs are reproducible — and **disclose every choice
in the report's coverage caveats** (never drop URLs silently):

1. **Always audit, individually:** the homepage, primary nav pages (about,
   team, services/practice-areas, contact, pricing, etc.), and every section
   **index** page (e.g. `/blog`).
2. **Always audit, individually:** every real **content** page — blog posts,
   articles, product/service detail pages, case studies. These hold the SEO and
   structured-data value.
3. **Sample, don't enumerate, template-generated listing pages** — taxonomy
   pages (`/blog/tag/*`, `/blog/category/*`, author/date archives), paginated
   `?page=N` variants, and faceted/query-param URLs. Audit **one representative
   of each kind** (one tag page, one category page) and state in the report how
   many of each were skipped and why. They share a template, so one sample
   characterizes the set; auditing all of them mostly burns tokens.
4. **Include known duplicate-serving variants** when they exist (e.g. a CMS that
   serves the homepage at both `/` and `/home`) — auditing both is how the
   duplicate/canonical findings surface.
5. **Drop** non-HTML and utility URLs the extractor can't meaningfully judge
   (feeds, `*.xml`, `/search`, `/cart`, `robots`/`sitemap` themselves).
6. **Hard cap** for very large sites: if step 2 still yields more than ~50
   content pages, audit the first ~50 (sitemap order) and **report the cap and
   the count skipped**. Offer to re-run on the remainder or a named subset.

When the user passed explicit pages, this section does not apply — audit exactly
what they named.

## Output
A de-duplicated, **scoped** list of absolute page URLs (per section 5), plus the
saved `robots.txt`, `sitemap.xml`, and `llms.txt` (or their 404 status). Record
the discovery source (sitemap / MCP / homepage-crawl), the total discovered vs.
audited counts, and what was sampled or capped — all of which belong in the
report's coverage caveats.
