# Procedure: Webflow-native fan-out (optional, complementary)

When the detected platform is **Webflow**, the audit can additionally fan out to
Webflow's own `webflow-skills` plugin, whose skills read the **Webflow Data API /
Designer** — the *configured* model (CMS schema, field utilization, asset
metadata, Designer accessibility) that our rendered-HTML crawl cannot see. The
two are complementary: ours = what shipped to the browser; Webflow's = what's
configured in the project. Fold both into one report.

This step is **Webflow-only** and **opt-in by availability**: if the platform
isn't Webflow, skip it silently. Never let it block or delay the four core
concerns.

## Which skills (decided)
Fan out to these via the `webflow-native-auditor` sub-agent (one Task per skill):
- `webflow-skills:site-audit` — read-only Data-API health/score.
- `webflow-skills:accessibility-audit` — WCAG 2.1 report (**needs the Webflow
  Designer connection**; if unavailable the sub-agent returns `ran:false`).
- `webflow-skills:asset-audit` — **report-only**: identify assets missing alt
  text / non-SEO names and list proposed improvements; **do not apply**.

Excluded by design: `link-checker` (overlaps our link-audit and can write) and
`component-audit` (React Code Components, not site content).

## Preflight (run before fanning out)
1. **Plugin installed?** Are `webflow-skills:*` skills and
   `mcp__plugin_webflow-skills_webflow__*` tools present? If **not**, skip the
   Webflow-native fan-out and tell the user how to add it (don't fail the run):

   > The Webflow-native checks need Webflow's own skills plugin. Install it:
   > ```
   > /plugin marketplace add webflow/webflow-skills
   > /plugin install webflow-skills@webflow-skills
   > ```
   > then authenticate the Webflow MCP (run `/mcp` and complete the Webflow OAuth,
   > or call the `mcp__plugin_webflow-skills_webflow__authenticate` tool), and
   > re-run. See https://github.com/webflow/webflow-skills.

2. **MCP authenticated?** If only the `...__authenticate` tool is present (not the
   data tools), the MCP isn't authenticated. **Authenticate in the main session
   first** — the OAuth prompt is interactive and a fan-out sub-agent running
   foreground can pass it through, but pre-authenticating avoids a mid-run prompt
   and is required for any headless/cron run. If it can't be authenticated, skip
   the Webflow-native fan-out and note it as a coverage caveat.

## Run
Spawn the `webflow-native-auditor` sub-agent **once per selected skill, in the
same parallel fan-out as the four core auditors** (foreground — background
sub-agents auto-deny the OAuth prompt). Pass each the skill name and the base
URL. Each returns `{skill, ran, reason?, summary, score, findings[], raw}`.

## Merge
Add a distinct **"Webflow-native (Data API / Designer)"** section to the report
(see `report-and-fixes.md`), separate from the rendered-HTML findings, and:
- Surface each skill's `score`/`summary` and fold its `findings` into the
  prioritized table tagged with concern = `webflow-native`.
- **Highlight configured-vs-rendered gaps** — e.g. Webflow `site-audit` says the
  SEO title field is set but our crawl shows the rendered `<title>` missing/dup →
  flag as an unpublished change or template override. This cross-check is the
  highest-value output of running both.
- For any skill that returned `ran:false`, list it under coverage caveats with
  its reason (not authenticated / Designer not connected / not installed).
- Keep everything **report-only**: asset-audit improvements are proposals, not
  applied changes.
