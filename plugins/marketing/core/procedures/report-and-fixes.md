# Procedure: report and propose fixes (suite-wide)

Merge the findings from every concern that ran (SEO, AI-discoverability,
security headers/TLS, link health) into one deliverable. **Audit + propose only
— never write to the live site, CMS, or MCP.**

## Outputs
Write to the directory the command/user specifies (default: the current working
directory):

```
site-audit-<YYYY-MM-DD>.md         # the unified report
proposed-fixes/
  jsonld/<page-or-template>.json   # ready-to-paste JSON-LD blocks (SEO/AI)
  meta-values.md                   # recommended <title> / description per page
  robots.txt                       # proposed robots.txt (if owner-approved policy)
  llms.txt                         # draft from the seo-audit skill's template
  security-headers.md              # proposed headers + per-platform how/where (or why not)
  broken-links.md                  # broken/redirecting links mapped to the pages that contain them
```
Only emit the artifacts for concerns that actually ran and have findings.

## Report structure (`site-audit-<date>.md`)

1. **Header** — site URL, detected platform + adapter, date, which concerns ran,
   pages audited (count + list), whether MCP enrichment ran, and coverage
   caveats (capped/sampled crawl, unreachable sitemap, unverified TLS, hosts not
   probed, links not reachable-checked).
2. **Executive summary** — 3–6 bullets: the highest-leverage findings across all
   concerns.
3. **Findings table**, sorted by severity, with a concern column:

   | Severity | Concern | Area | Page(s) | Finding (cite the field) | Recommended fix |
   |---|---|---|---|---|---|

   - **P0** — blocks indexing/crawling or is actively dangerous (accidental
     noindex, robots `Disallow: /`, a session cookie exposed over http).
   - **P1** — materially harmful (no canonical, no structured data, broken
     internal links, mixed content, deprecated TLS, near-expiry cert, missing
     HSTS on a sensitive site).
   - **P2** — best-practice gaps.
   Every finding cites the specific field/value it's based on.
4. **AI-discoverability posture** — the current AI-crawler `robots.txt` stance as
   an **owner decision** (allowed vs blocked bots, the trade-off), not a fix.
5. **Security posture summary** — TLS protocol/cipher/cert, which headers are
   present vs absent, and — crucially — **what the platform can vs. cannot set**
   (per the adapter), so absent-but-unfixable items aren't read as easy wins.
5b. **Webflow-native (Data API / Designer)** — *only if the Webflow-native
   fan-out ran* (see `webflow-native.md`). Report each Webflow skill's score +
   summary (site-audit's 0-100, accessibility-audit's WCAG result, asset-audit's
   proposed alt/name improvements — all report-only). **Call out
   configured-vs-rendered gaps explicitly**: where Webflow's Data-API view (field
   is set) disagrees with our rendered crawl (tag missing/duplicate) → flag as a
   likely unpublished change or template override. List any Webflow skill that
   didn't run (not authenticated / Designer not connected / not installed) under
   coverage caveats with the install+auth pointer.
6. **How to apply the fixes** — grouped by concern, using the active adapter's
   paste instructions (`core/adapters/<platform>.md`), pointing at the files in
   `proposed-fixes/`. Include platform caveats (Webflow custom code needs a paid
   plan + republish; Squarespace can't edit robots.txt/headers; etc.).
7. **Out of scope / next steps** — Core Web Vitals / performance (suggest
   PageSpeed Insights), client-rendered content, JS/meta-refresh redirects,
   application-level pentesting.

## Generating `proposed-fixes/`
- **JSON-LD** — for each missing/incomplete type (per the seo-audit
  `criteria/structured-data.md`), copy the matching template from the seo-audit
  skill (`skills/seo-audit/templates/jsonld/*.json`), fill known facts, mark
  unknowns as `"TODO: ..."`, and **validate it parses** (`python3 -m json.tool`)
  before saving.
- **meta-values.md** — proposed `<title>` + description strings with character
  counts, for the pages flagged in `criteria/seo-onpage.md`.
- **robots.txt** — only if warranted and the platform allows editing it; reflect
  the owner's chosen AI-crawler posture, don't impose one.
- **llms.txt** — fill `skills/seo-audit/templates/llms.txt` with the key pages.
- **security-headers.md** — the recommended header set (CSP/HSTS/etc.) with, for
  each, *where* it's set on this platform — or an explicit "not configurable on
  <platform>" note. Never prescribe a header the platform can't set.
- **broken-links.md** — each broken/redirecting link with its checked status and
  the list of pages that link to it, so fixes are actionable.

## Honesty rules
- State coverage plainly; if you capped, sampled, or fell back to homepage-crawl,
  say so. Record discovered-vs-audited counts.
- Don't claim a fix was applied — these are proposals.
- Don't report performance/CWV numbers; out of scope.
- Present AI-crawler blocking as a decision, never an error.
- Pair every security finding with the platform's real fix capability.
- Don't assert a link is broken or a cert expired without the tool result; flag
  unverified/transient cases for manual confirmation.
