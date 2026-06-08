# Adapter detection

Run this first, against the homepage's raw HTML (the body the extractor already
fetched — re-read it with `curl -sL <homepage>` if needed). Pick exactly one
adapter. A `--platform=` command argument overrides everything here.

## Signatures

**Webflow** → use `adapters/webflow.md` if any of:
- `<meta name="generator" content="Webflow">` (case-insensitive)
- `html` or `body` carries `data-wf-page="..."` or `data-wf-site="..."`
- assets served from `assets.website-files.com` / `assets-global.website-files.com`
- `<!-- Last Published ... by Webflow -->` comment near the top

**Squarespace** → use `adapters/squarespace.md` if any of:
- `<meta name="generator" content="Squarespace">` (case-insensitive)
- inline `Static.SQUARESPACE_CONTEXT = {...}` script
- assets served from `static1.squarespace.com` / `images.squarespace-cdn.com`
- `<body ... class="... squarespace-...">`

**WordPress** → use `adapters/wordpress.md` if any of:
- `<meta name="generator" content="WordPress ...">` (case-insensitive)
- asset paths under `/wp-content/` or `/wp-includes/`
- `<link rel="https://api.w.org/" href=".../wp-json/">` (REST API discovery link)
- SEO-plugin comments (`Yoast SEO`, `Rank Math`, `All in One SEO`) in `<head>`

**Wix** → use `adapters/wix.md` if any of:
- `<meta name="generator" content="Wix.com Website Builder">` (case-insensitive)
- `X-Wix-*` response headers (e.g. `x-wix-request-id`) in `response_headers`/`server`
- assets served from `static.wixstatic.com` / `static.parastorage.com`
- inline `wix-warmup-data` / `window.wixBiSession` script

**Neither / unknown** → use `adapters/generic.md`.

## How to check
```sh
curl -sL --max-time 15 -A "site-audit/1.0" "<homepage-url>" \
  | grep -ioE 'generator" content="(webflow|squarespace|wordpress|wix)|data-wf-(page|site)|SQUARESPACE_CONTEXT|website-files\.com|squarespace-cdn\.com|/wp-(content|includes)/|api\.w\.org|wixstatic\.com|parastorage\.com|wix-warmup-data' \
  | head
```
(Also check the response headers — a `Server: Squarespace` or any `X-Wix-*`
header is a strong signal.) Map the first strong hit to its adapter. If hits are
ambiguous (e.g. a WordPress site embedding a Wix widget), prefer the `generator`
meta tag; if still unclear, ask the user or fall back to `generic.md`.

Record the detected platform in the report header so the reader knows which
paste instructions apply.
