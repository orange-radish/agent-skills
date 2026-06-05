# Criteria: link & redirect health

Judge the `link_check.py` results (status / redirects / final_url per unique
link) joined with each page's `links` + `link_counts` + `redirect_chain`, and
the discovered sitemap/URL set. Cite the field/value in every finding.

Build the link set by unioning every inventory's `links[].href` (the extractor
already resolves them to absolute URLs and tags `internal`/`scheme`), dedupe,
and run `link_check.py` over it. Note which page(s) each broken link appears on
(from the `links` arrays) so fixes are actionable.

## Broken links (`link_check` status ≥ 400 or `ok:false`)
- **Internal broken links** — any internal link (`internal:true`) whose check
  returns 4xx/5xx or a connection error → **P1**. These are within the site's
  control and hurt users and crawlers. Cite the URL, its status, and the pages
  it appears on.
- **Outbound broken links** — external links returning 4xx/5xx → **P2** (you
  don't control the target, but a dead citation signals staleness — especially
  for a content/blog site). 5xx may be transient; note that a re-check is wise.
- **Connection errors / timeouts** — `status:null` with an `error` → **P2**
  (could be transient or bot-blocking); flag for manual confirmation rather than
  asserting "broken."

## Redirect hygiene (`redirects`, `final_url`, page `redirect_chain`)
- **Links to redirects** — an internal link whose check shows `redirects ≥ 1`
  (it points at a URL that then redirects) → **P2**: link directly to the
  `final_url` to save a hop. Worse for chains of 2+.
- **Redirect to error** — a link that redirects and lands on `ok:false` (e.g.
  301 → 404) → **P1**.
- **Redirect chains on the page itself** — `redirect_chain` length > 1 on a
  crawled page → **P2** (covered with technical SEO; surface if link-related).

## Protocol downgrades (`link_counts.http`, link `scheme`)
- **`http://` links from `https://` pages** — any link with `scheme:"http"` →
  **P2**: update to `https://`. (These usually redirect, adding a hop, and look
  insecure.) Count from `link_counts.http`; list examples.

## Canonical-host consistency
- **Links to non-canonical host variants** — internal links pointing at a
  different host than the site's canonical (e.g. non-`www` when the site is
  `www`, or a bare apex) → **P2**: they force a redirect and split signals.

## Orphan / coverage (sitemap vs. crawled link graph)
- **Orphan pages** — URLs present in `sitemap.xml` but not linked from any
  crawled page's `links` → **P2** (hard to reach, weak internal linking). State
  this is best-effort: only links on *crawled* pages were seen, so confirm
  before calling a page truly orphaned.

## Out of scope (state honestly, don't fake)
- JavaScript-driven and `<meta refresh>` redirects aren't visible to an HTTP
  check — note that client-side redirects weren't evaluated.
- Anchor (`#fragment`) targets and `mailto:`/`tel:` links aren't reachability-
  checked (the extractor marks them `internal:null` / a non-http `scheme`).

## Severity
- **P1** — broken internal link, link that redirects into an error.
- **P2** — broken outbound link, redirect-hop links, `http://` links, non-
  canonical-host links, orphan pages, unconfirmed connection errors.
