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

**Neither / unknown** → use `adapters/generic.md`.

## How to check
```sh
curl -sL --max-time 15 -A "site-seo-audit/1.0" "<homepage-url>" \
  | grep -ioE 'generator" content="(webflow|squarespace)"|data-wf-(page|site)|SQUARESPACE_CONTEXT|website-files\.com|squarespace-cdn\.com' \
  | head
```
Map the first strong hit to its adapter. If hits are ambiguous (both appear,
e.g. an embedded widget), prefer the `generator` meta tag; if still unclear, ask
the user or fall back to `generic.md`.

Record the detected platform in the report header so the reader knows which
paste instructions apply.
