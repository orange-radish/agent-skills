---
description: Audit a live website for SEO and AI-agent discoverability, then propose fixes (no writes). Crawls the rendered HTML as ground truth and enriches via the Webflow MCP when connected; ships Webflow + Squarespace adapters.
argument-hint: <base-url> [page-url ...] [--platform=webflow|squarespace|generic]
allowed-tools: Bash, Read, Grep, Glob, Task, WebFetch
---

You are orchestrating a website SEO + AI-discoverability audit. Use the
`seo-audit` skill in this plugin as your source of truth for criteria,
procedures, adapters, the extractor tool, and templates — read those files; do
not improvise the checks.

## Arguments
`$ARGUMENTS`

Parse them:
- First bare URL = **base URL**. If none is given, ask the user for it and stop.
- Additional bare URLs = **specific pages** → limit scope to exactly those.
- `--platform=...` = override platform auto-detection.

## Run the audit (follow the skill, in order)

1. **Detect the platform** — fetch the homepage and apply
   `skills/seo-audit/adapters/_detection.md` to pick the adapter (Webflow /
   Squarespace / generic). Honor any `--platform` override. State the result.
2. **Discover URLs** — follow `skills/seo-audit/procedures/discover-urls.md`
   (sitemap → adapter/MCP enrichment → homepage-crawl fallback). Also fetch
   `robots.txt`, `sitemap.xml`, `llms.txt`. If specific pages were passed, skip
   discovery and use those.
3. **Extract inventories** — follow
   `skills/seo-audit/procedures/extract-and-parse.md`: run
   `skills/seo-audit/tools/seo_extract.py` on each URL into a scratch dir, one
   JSON per page. (The skill files are under `${CLAUDE_PLUGIN_ROOT}/skills/seo-audit/`.)
4. **Fan out the two specialists in parallel** — launch BOTH sub-agents in a
   single message (two `Task` calls). They are plugin agents, so use their
   **namespaced** types exactly:
   - `site-seo:seo-technical-auditor`
   - `site-seo:ai-discoverability-auditor`
   Give each: the base URL, the detected platform/adapter, the scratch dir path
   with the inventory JSONs, the paths to `robots.txt`/`sitemap.xml`/`llms.txt`,
   the list of in-scope URLs, and (Webflow only, if connected) any MCP
   enrichment data. Each returns its findings as structured results.
5. **Merge & report** — combine both result sets, dedupe shared concerns,
   prioritize P0/P1/P2, and write the deliverables per
   `skills/seo-audit/procedures/report-and-fixes.md`: `seo-audit-<date>.md` plus
   a `proposed-fixes/` directory with filled JSON-LD (from
   `skills/seo-audit/templates/jsonld/`), recommended meta values, an optional
   `robots.txt`, and a drafted `llms.txt`. Use the active adapter's paste
   instructions for every fix.

## Hard rules
- **Audit + propose only.** Never write to the live site, the CMS, or any MCP.
- **Rendered HTML is ground truth**; MCP/CMS data is enrichment, never the sole
  basis for a finding. Every finding cites an extractor field.
- Present the AI-crawler `robots.txt` posture as an **owner decision**, not a
  defect.
- State coverage honestly (capped crawl, unreachable sitemap, fetch failures,
  unverified TLS). Do not claim Core Web Vitals/performance results — out of scope.
