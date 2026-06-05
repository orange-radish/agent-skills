---
name: security-audit
description: Audit a live website's HTTP security headers and TLS configuration and propose fixes — CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, cookie Secure/HttpOnly/SameSite flags, mixed content, TLS protocol/cipher/cert and deprecated-protocol acceptance. Part of the site-audit suite; reuses the shared crawl. Use when reviewing a site's security posture / response headers. Do not use for application-level pentesting, auth/session logic, or code vulnerabilities — this judges headers + TLS only, and never writes to the site.
user-invocable: false
allowed-tools:
  - Read
  - Bash
  - Grep
  - Glob
---

# security-audit

Judge a site's HTTP response headers and TLS setup against
`criteria/security-headers.md`, then propose fixes — **with the platform's real
header-control limits made explicit**. Audit + propose only; never writes.

## Ground truth
- **Response headers, cookies, mixed content** come from the shared extractor's
  inventory: `response_headers`, `set_cookie`, `server`, `x_powered_by`,
  `mixed_content` (see `../../core/procedures/extract-and-parse.md`). One fetch
  per page; the extractor reports exactly the headers that page returned.
- **TLS facts** (protocol, cipher, cert expiry, deprecated-protocol acceptance)
  come from `../../core/tools/tls_check.py <host>` — run once per host.
- Every finding cites a field/value. An absent security header is *visibly
  absent* in `response_headers` (only present headers are emitted) — that's the
  signal, not a guess.

## Platform caveat (the most important framing)
Hosted builders limit header control: Squarespace exposes almost none, Webflow
allows some via custom code / hosting, only self-hosted / reverse-proxied sites
control everything. A finding can be correct yet not fixable on the platform —
pair each with the real capability per the active `../../core/adapters/<platform>.md`.
Don't prescribe a header the platform can't set; say so instead.

## Workflow
1. Read `criteria/security-headers.md`.
2. Read every page inventory's header/cookie/mixed-content fields + the
   `tls_check.py` output for the host(s).
3. Judge each criterion; assign P0/P1/P2 with the cited field.
4. Propose fixes mapped to the platform adapter (what you *can* set, and where).

When run via `/site-audit:audit-site`, this is the `security-auditor` sub-agent.

## Do not
- Do not write to the site, CMS, or MCP.
- Do not claim header absence without checking `response_headers`.
- Do not prescribe platform-impossible fixes — state the limitation.
- Not a substitute for application pentesting (auth, injection, business logic).
