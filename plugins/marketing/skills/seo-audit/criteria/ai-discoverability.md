# Criteria: AI-agent discoverability (GEO / AEO)

How well an LLM-backed agent or answer engine can crawl, parse, and cite the
site. Distinct from classic SEO: the goal is machine *understanding* and
*citation*, not just ranking.

## AI-crawler access (fetched `robots.txt`)
Check `robots.txt` for `User-agent` rules naming AI crawlers:
`GPTBot`, `ChatGPT-User`, `OAI-SearchBot` (OpenAI); `ClaudeBot`, `anthropic-ai`,
`Claude-Web` (Anthropic); `PerplexityBot` (Perplexity); `Google-Extended`
(Google AI training); `CCBot` (Common Crawl); `Bytespider`, `Amazonbot`,
`Applebot-Extended`.

- **This is a policy decision, not a defect.** Report the current posture
  plainly: which AI crawlers are allowed vs disallowed. **Do not auto-flag a
  block as a failure** — many brands intentionally allow answer-engine crawlers
  (Perplexity, ChatGPT-User) for citations while disallowing training crawlers
  (Google-Extended, GPTBot, CCBot). Surface the trade-off and let the owner
  decide. Only flag as **P2** if the posture looks *accidental* (e.g. a blanket
  block that also stops answer engines the brand clearly wants visibility in).

## llms.txt (fetched separately at `/llms.txt`)
- **Emerging convention** — a `/llms.txt` (and optionally `/llms-full.txt`) gives
  agents a curated, plain-markdown map of the site's key pages and facts. Most
  sites lack it. Absent → **P2**, with a proposed draft from `templates/llms.txt`.

## Semantic HTML & content structure (`headings`, `word_count`, `jsonld_types`)
- **Real heading outline** — a clean H1→H2→H3 structure (see
  `criteria/seo-onpage.md`) is what lets an agent segment the page. Flat or
  heading-less pages are hard to extract → **P2**.
- **Substantive extractable text** — `word_count` near zero on a content page
  suggests the value is locked in images or rendered client-side (invisible to
  `curl` and most crawlers) → **P1** if a key page has almost no server-rendered
  text. (Webflow/Squarespace are mostly server-rendered; near-zero is a red flag.)
- **Answer-shaped content** — pages that answer concrete questions (what/how/
  pricing) are more citable. A site with no FAQ/Q&A structure and no `FAQPage`
  JSON-LD misses easy answer-engine surface area → **P2**.

## Identity & disambiguation
- **Consistent entity identity** — `Organization` JSON-LD with `sameAs` linking
  the brand's social/Wikipedia/Crunchbase profiles helps agents disambiguate the
  brand. Missing `sameAs` → **P2** (also covered in `criteria/structured-data.md`).

## Text-not-in-images
- **Key claims in text, not baked into hero images** — agents can't read text
  inside images reliably, and `img_missing_alt` won't recover it. Flag pages
  whose primary message appears to be image-only (low `word_count`, high
  `img_total`) → **P2**.

## Severity
- **P1** — key page has no server-rendered text (content not crawlable).
- **P2** — no llms.txt, weak semantic structure, no answer-shaped content,
  missing `sameAs`, accidental answer-engine block, image-only messaging.

Always present the AI-crawler posture as an explicit owner decision, never as a
unilateral "fix."
