# Criteria: on-page SEO

Judge each page's extractor inventory against these. Each item lists the
inventory field(s) it reads, the standard, and the severity if it fails. Cite
the field value in every finding — no eyeballing.

## Title (`title`, `title_length`)
- **Present** — every page has a non-empty `<title>`. Missing → **P0**.
- **Length** — roughly 30–60 characters. Google truncates ~580px (~60 chars).
  Too long (>65) or too short (<25) → **P2**.
- **Unique across pages** — compare `title` across all inventories. Duplicate
  titles on distinct pages → **P1**.
- **Descriptive** — leads with the page's actual topic, not just the brand. Brand
  is best as a suffix (`Page topic — Brand`). Weak/boilerplate → **P2**.

## Meta description (`meta_description`, `meta_description_length`)
- **Present** — missing description → **P1** (Google may auto-generate, but you
  lose control of the snippet).
- **Length** — roughly 120–160 characters. >170 risks truncation; <80 wastes the
  snippet → **P2**.
- **Unique across pages** — duplicates → **P2**.

## Headings (`headings`, `h1_count`)
- **Exactly one H1** — `h1_count` must be 1. Zero → **P1**; more than one → **P2**.
- **Logical outline** — heading levels in `headings` should not skip (e.g. H2 → H4
  with no H3). Skips → **P2**.
- **H1 reflects the page topic** — and is not identical to the site name on every
  page → **P2**.

## Canonical (`canonical`)
- **Present and absolute** — a self-referential absolute `https://` canonical is
  expected on indexable pages. Missing → **P1**; relative or http:// → **P2**.
- **Consistent with `fetched_url`** — a canonical pointing at a different URL than
  the page (and its redirect target) may de-index the page; confirm it's
  intentional → **P1** if it looks accidental.

## Indexability (`meta_robots`, `x_robots_tag`)
- **Not accidentally noindex** — if `meta_robots` or `x_robots_tag` contains
  `noindex` on a page that should rank, that is a **P0**. (Staging/utility pages
  legitimately noindex — confirm intent.)

## Images (`img_total`, `img_missing_alt`)
- **Alt coverage** — `img_missing_alt` should be 0 (decorative images use an
  empty `alt=""`, which the extractor does not count as missing). A high ratio of
  missing alt → **P2** (accessibility + image SEO).

## Social cards (`og`, `twitter`)
- **Open Graph core** — `og.title`, `og.description`, `og.image`, `og.url`,
  `og.type` present. Missing `og.image` or `og.title` → **P2**.
- **Twitter card** — `twitter.card` (usually `summary_large_image`) present;
  falls back to OG otherwise. Missing with no OG fallback → **P2**.

## Language (`html_lang`)
- **`<html lang>` set** — missing or empty → **P2**.

## Severity definitions
- **P0** — blocks indexing/ranking or breaks the page for crawlers (missing
  title, accidental noindex).
- **P1** — materially weakens SEO (missing description/canonical, duplicate
  titles, no H1).
- **P2** — best-practice gap; fix opportunistically.
