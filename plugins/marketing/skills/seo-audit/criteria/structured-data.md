# Criteria: structured data (JSON-LD / schema.org)

Reads `jsonld` and `jsonld_types` from each inventory. Structured data is the
single highest-leverage lever for AI-agent discoverability and rich results —
it turns prose into machine-readable facts. Prefer **JSON-LD** (Google's
recommended format) over microdata/RDFa.

## Presence & validity
- **At least some JSON-LD on the site** — a marketing site with zero JSON-LD
  (`jsonld_types` empty everywhere) → **P1**.
- **Valid JSON** — every block in `jsonld` must have `"valid": true`. A block with
  `"valid": false` (the extractor records the parse error) → **P1**; invalid
  JSON-LD is ignored by crawlers entirely.

## Expected types by page role
Map each page to the types it should carry. Missing an expected type → **P1**;
present-but-incomplete (missing required props) → **P2**.

- **Home / all pages** — `Organization` (or `LocalBusiness` for a
  physical-location business) and `WebSite`. `Organization` should include
  `name`, `url`, `logo`, and `sameAs` (social profiles). `WebSite` should include
  `name`, `url`, and a `potentialAction` → `SearchAction` if the site has search.
- **Any page with a nav path** — `BreadcrumbList` reflecting the URL hierarchy.
- **Product / service / pricing pages** — `Product` or `Service` (+ `Offer` with
  `price`/`priceCurrency` where applicable).
- **Pages with a Q&A block** — `FAQPage` with `mainEntity` → `Question`/`Answer`.
- **Blog / news / article pages** — `Article` or `BlogPosting` with `headline`,
  `datePublished`, `author`, `image`.
- **Contact / location** — `LocalBusiness` with `address`, `telephone`,
  `openingHours` if relevant.

## Correctness
- **Matches visible content** — JSON-LD must describe what's actually on the page
  (no fabricated reviews, prices, or FAQs). Mismatch is a guidelines violation →
  **P1**.
- **One coherent graph** — multiple blocks are fine, but entities should
  cross-reference by `@id` rather than contradict each other → **P2** if
  inconsistent.
- **Absolute URLs** in `url`, `logo`, `image`, `sameAs` → **P2** if relative.

## Proposing fixes
For each missing/incomplete type, generate a filled block from
`templates/jsonld/` (Organization, WebSite, BreadcrumbList, Product, FAQPage,
Article, LocalBusiness). Fill known business facts; mark unknowns as `TODO`.
Validate the proposed JSON parses before emitting. Delivery location is
adapter-specific (see the active `adapters/*.md`).

## Severity
- **P1** — no structured data at all, invalid JSON-LD, missing a core expected
  type (Organization/WebSite), or markup that misrepresents the page.
- **P2** — incomplete props, relative URLs, inconsistent graph, missing
  page-role-specific types (BreadcrumbList, FAQPage, Product).
