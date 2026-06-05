---
name: link-audit
description: Audit a live website's link & redirect health and propose fixes — broken internal/outbound links (4xx/5xx), redirect chains, links that redirect into errors, http:// links on https pages, links to non-canonical host variants, and likely orphan pages. Part of the site-audit suite; reuses the shared crawl. Use when checking for dead links, redirect hygiene, or internal-linking gaps. Do not use for full off-site backlink analysis or JS/meta-refresh redirects (HTTP-level only), and it never writes to the site.
user-invocable: false
allowed-tools:
  - Read
  - Bash
  - Grep
  - Glob
---

# link-audit

Judge a site's link graph against `criteria/link-health.md`, then propose fixes.
Audit + propose only; never writes.

## Ground truth
- Each page inventory already lists resolved links: `links`
  (`{href, text, internal, scheme}`) and `link_counts` (see
  `../../core/procedures/extract-and-parse.md`).
- **Reachability** comes from `../../core/tools/link_check.py`: union every
  inventory's `links[].href`, dedupe, pipe to the checker — it returns
  `status` / `ok` / `redirects` / `final_url` per unique link.
- Every finding cites the link, its checked status, and the page(s) it's on.

## Workflow
1. Read `criteria/link-health.md`.
2. Build the deduped link set from all inventories; run `link_check.py` over it.
3. Cross-reference broken/redirecting links back to the pages that contain them
   (from each inventory's `links` array) so fixes are actionable.
4. Compare the sitemap URL set to the crawled link graph for likely orphans.
5. Judge each criterion; assign P0/P1/P2 with the cited status.

## Honesty
- Only links on **crawled** pages were seen — scope orphan claims to that.
- JS-driven and `<meta refresh>` redirects aren't HTTP-visible — say so.
- A `status:null` connection error may be transient or bot-blocking — flag for
  manual confirmation rather than asserting "broken."

When run via `/site-audit:audit-site`, this is the `link-health` sub-agent.

## Do not
- Do not write to the site, CMS, or MCP.
- Do not assert a link is broken without a `link_check.py` result for it.
- Not an off-site backlink/authority audit.
