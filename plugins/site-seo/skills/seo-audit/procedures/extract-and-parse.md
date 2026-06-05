# Procedure: extract a JSON inventory per page

Run the deterministic extractor on every in-scope URL and save one JSON file per
page. The agents reason over these JSON files — **not** raw HTML.

## Run the extractor
```sh
TOOL="$CLAUDE_PLUGIN_ROOT/skills/seo-audit/tools/seo_extract.py"   # or the repo path
SCRATCH="$(mktemp -d)/seo"; mkdir -p "$SCRATCH"
i=0
for url in $URLS; do
  i=$((i+1))
  python3 "$TOOL" "$url" --timeout 20 > "$SCRATCH/page_$i.json"
done
echo "$SCRATCH"
```
- Requires `python3` (3.8+) only — standard library, no pip install.
- Each file is a complete inventory; a fetch failure is recorded as
  `{"ok": false, "error": "..."}` rather than crashing the loop.
- For a saved HTML file instead of a live fetch: `python3 "$TOOL" <url> --file page.html`.

## Inventory fields (what to read)
See the header of `tools/seo_extract.py` for the authoritative list. Key fields:

| Field | Used by |
|---|---|
| `http_status`, `redirect_chain`, `fetched_url`, `tls_verified` | technical SEO |
| `title`, `title_length` | on-page SEO |
| `meta_description`, `meta_description_length` | on-page SEO |
| `meta_robots`, `x_robots_tag` | indexability |
| `canonical`, `hreflang` | on-page + technical SEO |
| `og`, `twitter` | social cards |
| `headings`, `h1_count` | on-page SEO + AI structure |
| `img_total`, `img_missing_alt` | accessibility / image SEO |
| `word_count` | AI discoverability (content crawlability) |
| `jsonld` (with `valid`/`types`/`error`), `jsonld_types` | structured data |
| `html_lang`, `charset`, `viewport` | on-page SEO |
| `notes` | parser caveats (e.g. unverified TLS) |

## Traceability rule
Every finding in the report must cite a field/value from one of these JSON files
(e.g. "home `title_length` = 71, exceeds ~60"). Do not assert anything the
inventory doesn't contain. If a needed signal isn't captured (e.g. Core Web
Vitals), say it's out of scope — don't invent it.

## Cross-page checks
Some criteria compare across pages (duplicate titles/descriptions, single
canonical host, sitemap-vs-crawled set). Load all inventory JSONs together for
those — a quick `jq`/python pass over `$SCRATCH/*.json` works well.
