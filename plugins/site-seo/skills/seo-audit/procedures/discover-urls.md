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
curl -sL --max-time 15 -A "site-seo-audit/1.0" "$BASE/robots.txt"  -o robots.txt  -w "%{http_code}\n"
curl -sL --max-time 15 -A "site-seo-audit/1.0" "$BASE/sitemap.xml" -o sitemap.xml -w "%{http_code}\n"
curl -sL --max-time 15 -A "site-seo-audit/1.0" "$BASE/llms.txt"    -o llms.txt    -w "%{http_code}\n"
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
curl -sL --max-time 15 -A "site-seo-audit/1.0" "$BASE/" \
  | grep -oE 'href="[^"]+"' | sed -E 's/href="//; s/"//' \
  | grep -E "^(/|$BASE)" | sort -u
```
Resolve relative links against `$BASE`, drop fragments/asset URLs, keep HTML
pages. This is a shallow fallback — note in the report that coverage is
homepage-link-depth only, not exhaustive.

## Output
A de-duplicated list of absolute page URLs (capped to a sane number for very
large sites — if you cap, **say so in the report**; never silently truncate),
plus the saved `robots.txt`, `sitemap.xml`, and `llms.txt` (or their 404 status).
