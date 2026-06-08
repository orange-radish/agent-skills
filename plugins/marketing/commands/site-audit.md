---
description: Audit a live website across SEO, AI-agent discoverability, security headers/TLS, and link health — then propose fixes (no writes). Crawls the rendered HTML once as ground truth, with Webflow, Squarespace, WordPress, and Wix adapters for platform-specific fix guidance.
argument-hint: <base-url> [page-url ...] [--platform=webflow|squarespace|wordpress|wix|generic] [--only=seo,ai,security,links]
allowed-tools: Bash, Read, Grep, Glob, Task, WebFetch
---

You are orchestrating a multi-dimension website audit (the `site-audit` suite).
The shared crawl + adapters + tools live in `${CLAUDE_PLUGIN_ROOT}/core/`; the
per-concern criteria live in `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/criteria/`.
Read those files as the source of truth — do not improvise the checks.

## Arguments
`$ARGUMENTS`

Parse them:
- First bare URL = **base URL**. If none is given, ask the user and stop.
- Additional bare URLs = **specific pages** → limit scope to exactly those.
- `--platform=...` = override platform auto-detection.
- `--only=...` = run just those concerns (comma list of `seo,ai,security,links`).
  Default = all four.

## Run the audit (in order)

1. **Detect the platform** — fetch the homepage and apply
   `core/adapters/_detection.md` to pick the adapter (Webflow / Squarespace /
   WordPress / Wix / generic). Honor any `--platform` override. State the result.
2. **Discover URLs** — follow `core/procedures/discover-urls.md` (sitemap →
   adapter/MCP enrichment → homepage-crawl fallback) and apply its **scoping
   heuristic** (audit nav + index + content pages, sample template/taxonomy
   pages, disclose what's sampled/capped). Also fetch `robots.txt`,
   `sitemap.xml`, `llms.txt`. If specific pages were passed, skip discovery.
3. **Crawl once** — follow `core/procedures/extract-and-parse.md`: run
   `core/tools/site_extract.py` on each in-scope URL into a scratch dir (one JSON
   per page). This single inventory feeds every concern. Then, for the concerns
   that will run:
   - security → run `core/tools/tls_check.py <host>` once per host into the dir.
   - links → union every inventory's `links[].href`, dedupe to a file, and run
     `core/tools/link_check.py --file <that file>` into the dir.
4. **Fan out the specialists in parallel** — launch them in a single message
   (one `Task` per concern). Use the **namespaced** agent types exactly:
   - seo → `marketing:seo-technical-auditor`
   - ai → `marketing:ai-discoverability-auditor`
   - security → `marketing:security-auditor`
   - links → `marketing:link-health-auditor`
   Give each: the base URL, the detected platform/adapter, the scratch dir path,
   the relevant artifact paths (inventories; `robots.txt`/`sitemap.xml`/`llms.txt`
   for seo/ai; `tls_check` JSON for security; `link_check` JSON for links), the
   in-scope URL list, and (Webflow only, if connected) any MCP enrichment data.
   Each returns structured findings.

   **Webflow-native add-on (only when platform = Webflow):** also follow
   `core/procedures/webflow-native.md` — run its preflight, and if the
   `webflow-skills` plugin is installed and the Webflow MCP is authenticated,
   add to the SAME parallel fan-out one `marketing:webflow-native-auditor`
   sub-agent per Webflow skill (`webflow-skills:site-audit`,
   `webflow-skills:accessibility-audit`, `webflow-skills:asset-audit` in
   report-only mode). These run foreground and are **report-only** — never apply
   changes. If the plugin isn't installed / MCP isn't authenticated, skip them,
   show the install+auth pointer from that procedure, and proceed with the four
   core concerns. Non-Webflow platforms skip this entirely.
5. **Merge & report** — combine all result sets (core + any Webflow-native),
   dedupe shared concerns, prioritize P0/P1/P2, and write the deliverables per
   `core/procedures/report-and-fixes.md`: `site-audit-<date>.md` (with its
   **Webflow-native** section + configured-vs-rendered cross-checks) plus a
   `proposed-fixes/` directory (JSON-LD from `skills/seo-audit/templates/jsonld/`,
   meta values, optional `robots.txt`, drafted `llms.txt`, `security-headers.md`,
   `broken-links.md`). Use the active adapter's paste instructions for every fix.

## Hard rules
- **Audit + propose only.** Never write to the live site, the CMS, or any MCP.
- **Rendered HTML / tool output is ground truth.** Every finding cites a field
  from an inventory or a tool's JSON. MCP/CMS data is enrichment, never the sole
  basis.
- Present the AI-crawler `robots.txt` posture as an **owner decision**, not a
  defect.
- **Pair every security finding with the platform's real fix capability** (the
  adapter says what Webflow/Squarespace can vs. cannot set) — don't prescribe an
  impossible header.
- Don't assert a link is broken or a cert expired without the tool result; flag
  unverified/transient cases for manual confirmation.
- State coverage honestly (sampled/capped crawl, unreachable sitemap, fetch
  failures, unverified TLS, hosts not probed). Do not claim Core Web
  Vitals/performance results — out of scope.
