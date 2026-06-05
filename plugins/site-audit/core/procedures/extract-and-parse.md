# Procedure: extract a JSON inventory per page

Run the deterministic extractor on every in-scope URL and save one JSON file per
page. The agents reason over these JSON files — **not** raw HTML.

## Run the extractor
The shared tools live in the plugin's `core/tools/` (Claude Code:
`$CLAUDE_PLUGIN_ROOT/core/tools/`; running from a repo clone: the
`plugins/site-audit/core/tools/` path).
```sh
TOOL="$CLAUDE_PLUGIN_ROOT/core/tools/site_extract.py"
SCRATCH="$(mktemp -d)/site"; mkdir -p "$SCRATCH"
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

One fetch per page produces a single inventory that **all three audit concerns
read** (SEO, security headers, link/mixed-content). Two sibling tools add what a
single HTML fetch can't see:
- `core/tools/tls_check.py <host>` → TLS protocol/cipher, cert expiry, whether
  deprecated TLS 1.0/1.1 are still accepted. Run once per host.
- `core/tools/link_check.py` (URLs on stdin or `--file`) → status + redirect
  hops + final URL for the union of links discovered across pages. Run once over
  the deduped link set.

## Inventory fields (what to read)
See the header of `core/tools/site_extract.py` for the authoritative list. Key fields:

| Field | Used by |
|---|---|
| `http_status`, `redirect_chain`, `fetched_url`, `tls_verified` | technical SEO / links |
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
| `response_headers` (lowercased, only those present), `set_cookie`, `server`, `x_powered_by` | **security headers** |
| `links` (`{href, text, internal, scheme}`), `link_counts` | **link health** |
| `mixed_content` (`{tag, url}`), `mixed_content_count` | **security (mixed content)** |
| `notes` | parser caveats (e.g. unverified TLS) |

For the deep TLS and link-reachability facts, read the JSON emitted by
`tls_check.py` and `link_check.py` respectively.

## Traceability rule
Every finding in the report must cite a field/value from one of these JSON files
(e.g. "home `title_length` = 71, exceeds ~60"). Do not assert anything the
inventory doesn't contain. If a needed signal isn't captured (e.g. Core Web
Vitals), say it's out of scope — don't invent it.

## Cross-page checks
Some criteria compare across pages (duplicate titles/descriptions, single
canonical host, sitemap-vs-crawled set). Load all inventory JSONs together for
those — a quick `jq`/python pass over `$SCRATCH/*.json` works well.
