# Criteria: security headers + TLS

Judge each page's inventory `response_headers` / `set_cookie` / `server` /
`x_powered_by` / `mixed_content`, plus the host's `tls_check.py` output. Cite the
exact field/value in every finding. Mozilla-Observatory-style standard.

**Platform reality (bake this into every fix):** hosted builders limit header
control. Squarespace exposes almost no header settings; Webflow allows some via
custom code / hosting config; only self-hosted / reverse-proxied sites control
all of these. So a finding may be *correct* yet *not fixable on the platform* —
say which, per the active `core/adapters/<platform>.md`, rather than prescribing
an impossible change.

## HTTPS & mixed content (`mixed_content`, `fetched_url`, redirect to https)
- **No mixed content** — `mixed_content_count` must be 0. Any `http://`
  subresource (script/img/iframe/css) on an `https://` page → **P1**: it breaks
  the security guarantee and browsers may block it. List the offending `{tag,url}`.
- **HTTPS canonical** — `fetched_url` should be `https://`; an http:// final URL
  that doesn't redirect to https → **P1**.

## HSTS (`response_headers["strict-transport-security"]`)
- **Present** with a sane `max-age` (≥ 6 months / 15552000). Missing → **P2**
  (escalate to **P1** for sites with logins or that submit sensitive data, e.g. a
  law firm's contact/intake forms). `includeSubDomains` and `preload` are pluses.

## Content-Security-Policy (`content-security-policy`)
- **Present** → strong defense against XSS/injection. Absent → **P2** (CSP is
  genuinely hard to deploy on hosted platforms; flag as an opportunity, and note
  whether the platform even allows it). `unsafe-inline`/`unsafe-eval` in the
  policy weaken it → note as P2.

## Clickjacking (`x-frame-options` or CSP `frame-ancestors`)
- One of them present → framing controlled. Neither → **P2** (clickjacking risk).

## MIME sniffing (`x-content-type-options`)
- Should be `nosniff`. Missing → **P2**.

## Referrer & Permissions policy
- `referrer-policy` present (e.g. `strict-origin-when-cross-origin`) — missing → **P2**.
- `permissions-policy` present (locks down camera/mic/geo) — missing → **P2** (low).

## Cookies (`set_cookie`)
- Each cookie should carry `Secure` and `HttpOnly`, and an explicit `SameSite`.
  A cookie missing `Secure` or `HttpOnly` → **P2** (escalate to **P1** if it's a
  session/auth cookie). Cite the cookie name. (Many marketing sites set only
  analytics cookies — judge proportionately.)

## Information disclosure (`server`, `x_powered_by`)
- A `Server` or `X-Powered-By` header that leaks **specific software versions**
  (e.g. `Apache/2.4.29`, `PHP/7.2`) → **P2** (aids targeted attacks). A bare
  product name with no version (e.g. `Squarespace`, `cloudflare`) is fine.

## TLS (`tls_check.py` output)
- **No deprecated protocols** — `accepts_deprecated.tls1_0` / `tls1_1` must be
  `false`. Either `true` → **P1**. (`null` = client couldn't test; say so.)
- **Modern negotiated protocol** — `negotiated_protocol` should be TLS 1.2 or
  1.3. 1.1/1.0 → **P1**.
- **Certificate validity** — `cert.days_until_expiry` < 15 → **P1**; < 30 →
  **P2**. If `cert_verified` is false (local trust-store artifact), report
  protocol/cipher and note the cert wasn't readable — do **not** invent expiry.

## Severity
- **P0** — none typically from headers alone (reserve for an actively dangerous
  misconfig, e.g. a cookie exposing a session over http).
- **P1** — mixed content, deprecated TLS, near-expiry cert, missing HSTS on a
  sensitive site, insecure session cookie.
- **P2** — missing CSP / clickjacking / nosniff / referrer / permissions
  headers, version disclosure, non-session cookie flag gaps.

Always pair each finding with the platform's real fix capability.
