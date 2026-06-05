---
name: seo-audit
description: Audit a live website for SEO best practices and AI-agent discoverability (structured data / JSON-LD, GEO/AEO), then propose fixes with platform-specific paste instructions. Crawls the rendered published HTML as ground truth and enriches via the Webflow MCP when available; ships Webflow, Squarespace, WordPress, and Wix adapters. Use when reviewing a marketing site's titles, meta tags, headings, canonical/hreflang, robots.txt, sitemap, schema.org markup, and AI-crawler readiness. Do not use for Core Web Vitals / performance profiling, for sites needing authenticated crawling, or to write changes back to the live site.
user-invocable: false
allowed-tools:
  - Read
  - Bash
  - Grep
  - Glob
  - WebFetch
---

# seo-audit

Audit a live website and propose (never apply) SEO and AI-discoverability
fixes. The deliverable is a prioritized report plus ready-to-paste artifacts
(JSON-LD, meta values, `robots.txt`, `llms.txt`) with platform-specific "where
to paste" instructions.

## The one rule that makes this reliable

**Ground truth is the rendered, published HTML — not any CMS API.** A CMS API
or MCP returns the *data model* (configured fields, content, custom-code
registrations); it does **not** return what a crawler or AI bot actually sees.
JSON-LD, the heading outline, canonical/hreflang, and robots directives all live
in the *rendered* page. So:

1. **Always crawl the live site for raw HTML** via the shared
   `../../core/tools/site_extract.py` (it uses `curl`-equivalent `urllib`, not
   `WebFetch` — `WebFetch` summarizes through a small model and drops the exact
   bytes you need).
2. **Every finding must be traceable to a field** in the extractor's JSON
   inventory. Do not eyeball HTML or assert facts the inventory doesn't show.
3. **A CMS/MCP is enrichment only** — it tells you the *configured* value (so a
   fix can name the exact field to edit) and can reveal a configured-vs-rendered
   mismatch. It is never the sole source.

## Inputs

Required:
- **base URL** of the site (or one or more specific page URLs to limit scope).

Optional:
- specific pages → audit only those instead of the whole site.
- `--platform=webflow|squarespace|wordpress|wix|generic` → override auto-detection.
- known business facts (legal name, logo URL, social profiles, products/FAQs) →
  used to fill JSON-LD templates; otherwise the templates are emitted with
  clearly marked `TODO` placeholders.

## Workflow

The shared crawl (detection, discovery, the extractor) lives in the plugin's
`../../core/` and is reused by every skill in the suite.

### 1. Detect the platform
Fetch the homepage and follow `../../core/adapters/_detection.md` to pick an
adapter (`../../core/adapters/{webflow,squarespace,wordpress,wix,generic}.md`).
A `--platform` override wins over detection.

### 2. Discover URLs
Follow `../../core/procedures/discover-urls.md`: `sitemap.xml` first, then
adapter enrichment (Webflow MCP `pages_list` when connected), then homepage link
extraction as a fallback. Also fetch `robots.txt`. Default scope is the whole
site; explicit page arguments narrow it.

### 3. Extract a JSON inventory per page
Follow `../../core/procedures/extract-and-parse.md` to run
`../../core/tools/site_extract.py` on each URL and save one inventory JSON per
page to a scratch dir. Read the inventories, not the raw HTML.

### 4. Enrich (optional, adapter-driven)
The Webflow adapter pulls read-only MCP data (configured SEO/OG, CMS structure,
existing custom code). Squarespace/generic skip this. Degrade cleanly if the
MCP is absent — never block the audit on it.

### 5. Judge against the criteria
Two concerns, judged against `criteria/`:
- **Classic SEO** → `criteria/seo-onpage.md` + `criteria/seo-technical.md`
- **AI discoverability** → `criteria/structured-data.md` + `criteria/ai-discoverability.md`

When invoked through the `/marketing:site-audit` command these two concerns run
as the `seo-technical-auditor` and `ai-discoverability-auditor` sub-agents in
parallel (alongside the suite's security and link-health agents). When the skill
is invoked directly, work through both concern sets yourself.

### 6. Report and propose fixes
Follow `../../core/procedures/report-and-fixes.md`: merge findings, dedupe shared concerns,
prioritize **P0 / P1 / P2**, and emit `seo-audit-<date>.md` plus a
`proposed-fixes/` directory. Fill JSON-LD from `templates/jsonld/` and draft
`templates/llms.txt`. Every fix carries the selected adapter's exact paste
instructions. **Do not write anything back to the live site.**

## Stop conditions

- **Success** — every discovered in-scope page has an inventory (or a recorded
  fetch error), every applicable criterion has been judged, and the report +
  `proposed-fixes/` are written with platform-specific instructions.
- **Partial** — some pages failed to fetch or the sitemap was unreachable. Report
  what was covered, list the gaps explicitly, and never imply full coverage.

## Skill-level Do Not

- Do not write to the live site, the CMS, or any MCP (audit + propose only).
- Do not treat MCP/CMS data as ground truth; the rendered HTML wins.
- Do not assert findings the extractor inventory doesn't support.
- Do not flag blocked AI crawlers as an error — surface it as a policy decision
  for the owner (see `criteria/ai-discoverability.md`).
- Do not claim Core Web Vitals / performance results; that needs a tool this
  skill doesn't ship (note PageSpeed Insights as an optional follow-up).
