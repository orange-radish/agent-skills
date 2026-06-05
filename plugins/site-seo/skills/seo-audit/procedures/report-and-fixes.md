# Procedure: report and propose fixes

Merge the two concern sets into one deliverable. **Audit + propose only — never
write to the live site, CMS, or MCP.**

## Outputs
Write to the directory the command/user specifies (default: the current working
directory):

```
seo-audit-<YYYY-MM-DD>.md        # the report
proposed-fixes/
  jsonld/<page-or-template>.json # ready-to-paste JSON-LD blocks
  meta-values.md                 # recommended <title> / description per page
  robots.txt                     # proposed robots.txt (if owner-approved policy)
  llms.txt                       # draft from templates/llms.txt
```

## Report structure (`seo-audit-<date>.md`)

1. **Header** — site URL, detected platform + adapter used, date, pages audited
   (count + list), whether MCP enrichment ran, and any coverage caveats (capped
   crawl, unreachable sitemap, unverified TLS).
2. **Executive summary** — 3–6 bullets: the highest-leverage findings.
3. **Findings table**, sorted by severity:

   | Severity | Area | Page(s) | Finding (cite the inventory field) | Recommended fix |
   |---|---|---|---|---|

   - **P0** — blocks indexing/crawling (missing title, accidental noindex,
     robots `Disallow: /`).
   - **P1** — materially weakens SEO/AI discoverability (no description/canonical,
     duplicate titles, no structured data, invalid JSON-LD, key page not
     crawlable).
   - **P2** — best-practice gaps.
   Every finding cites the specific field/value it's based on.
4. **AI-discoverability posture** — the current AI-crawler `robots.txt` stance
   presented as an **owner decision** (allowed vs blocked bots, the trade-off),
   not a unilateral fix. Plus llms.txt / structured-data / semantic-structure
   notes.
5. **How to apply the fixes** — the active adapter's paste instructions
   (`adapters/<platform>.md`), pointing at the files in `proposed-fixes/`. Include
   the platform's caveats (e.g. Webflow custom code needs a paid plan + republish;
   Squarespace robots.txt isn't editable).
6. **Out of scope / next steps** — Core Web Vitals / performance (suggest
   PageSpeed Insights), anything the crawl couldn't see (client-rendered widgets).

## Generating `proposed-fixes/`
- **JSON-LD** — for each missing/incomplete type (per `criteria/structured-data.md`),
  copy the matching `templates/jsonld/*.json`, fill known business facts, mark
  unknowns as `"TODO: ..."`, and **validate it parses** (`python3 -m json.tool`)
  before saving. One file per page or per template.
- **meta-values.md** — proposed `<title>` and meta description strings per page,
  with character counts, for the pages flagged in `criteria/seo-onpage.md`.
- **robots.txt** — only if a change is warranted and the platform allows editing
  it; reflect the owner's chosen AI-crawler posture, don't impose one.
- **llms.txt** — fill `templates/llms.txt` with the discovered key pages.

## Honesty rules
- State coverage plainly; if you capped or fell back to homepage-crawl, say so.
- Don't claim a fix was applied — these are proposals.
- Don't report performance/CWV numbers; they're out of scope.
- Present AI-crawler blocking as a decision, never an error.
