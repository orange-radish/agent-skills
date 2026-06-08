#!/usr/bin/env python3
"""link_check.py - check the reachability of a list of URLs.

Companion to site_extract.py for the `site-audit` suite's link-health check.
Reads URLs (one per line) from stdin or from a --file, de-duplicates them, and
reports each one's final HTTP status, redirect hop count, and final URL — so the
link-health auditor can flag 404s, redirect chains, and http->https issues.
Standard library only (urllib, concurrent.futures).

Usage:
    cat urls.txt | python3 link_check.py
    python3 link_check.py --file urls.txt
    python3 link_check.py --file urls.txt --timeout 12 --workers 10

Output: one JSON object {"results": [ {url, status, ok, final_url, redirects,
error}, ... ], "checked": N}. Uses HEAD, falling back to GET when a server
rejects HEAD (405/501) or returns no useful status. Only http(s) URLs are
checked; others are skipped and reported with status null + scheme note.
"""
import sys
import json
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
from urllib.parse import urlparse
from urllib.error import URLError, HTTPError
import ssl

UA = ("Mozilla/5.0 (compatible; site-audit-linkcheck/1.0; "
      "+https://github.com/orange-radish/agent-skills)")


class _CountingRedirect(HTTPRedirectHandler):
    def __init__(self):
        self.count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.count += 1
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(url, method, timeout, ctx):
    rh = _CountingRedirect()
    opener = build_opener(HTTPSHandler(context=ctx), rh)
    req = Request(url, method=method, headers={"User-Agent": UA, "Accept": "*/*"})
    resp = opener.open(req, timeout=timeout)
    return resp.getcode(), resp.geturl(), rh.count


def check_one(url, timeout):
    scheme = urlparse(url).scheme.lower()
    if scheme not in ("http", "https"):
        return {"url": url, "status": None, "ok": None,
                "final_url": url, "redirects": 0, "scheme": scheme or "none"}
    ctx = ssl.create_default_context()
    tried_unverified = False
    methods = ["HEAD", "GET"]
    mi = 0
    while mi < len(methods):
        method = methods[mi]
        try:
            status, final, hops = _open(url, method, timeout, ctx)
            r = {"url": url, "status": status, "ok": status < 400,
                 "final_url": final, "redirects": hops}
            if tried_unverified:
                r["tls_unverified"] = True  # local trust-store fallback, not a finding
            return r
        except HTTPError as e:
            if method == "HEAD" and e.code in (400, 403, 405, 501):
                mi += 1; continue  # some servers reject HEAD - retry with GET
            return {"url": url, "status": e.code, "ok": e.code < 400,
                    "final_url": getattr(e, "url", url), "redirects": 0}
        except (URLError, OSError) as e:
            # urllib wraps SSL cert-verify failures in URLError.reason - on a
            # local trust-store problem, retry the SAME method unverified once.
            reason = getattr(e, "reason", e)
            if isinstance(reason, ssl.SSLCertVerificationError) and not tried_unverified:
                ctx = ssl._create_unverified_context(); tried_unverified = True
                continue
            if method == "HEAD":
                mi += 1; continue  # HEAD may be blocked; try GET
            return {"url": url, "status": None, "ok": False,
                    "final_url": url, "redirects": 0, "error": str(reason)}
        except Exception as e:  # noqa: BLE001
            return {"url": url, "status": None, "ok": False,
                    "final_url": url, "redirects": 0, "error": f"{type(e).__name__}: {e}"}
    return {"url": url, "status": None, "ok": False, "final_url": url,
            "redirects": 0, "error": "HEAD and GET both failed"}


def main(argv):
    args = argv[1:]
    file_path = None
    timeout = 12.0
    workers = 10
    i = 0
    while i < len(args):
        if args[i] == "--file":
            file_path = args[i + 1]; i += 2
        elif args[i] == "--timeout":
            timeout = float(args[i + 1]); i += 2
        elif args[i] == "--workers":
            workers = int(args[i + 1]); i += 2
        else:
            sys.stderr.write(f"unknown flag: {args[i]}\n"); return 2
    text = open(file_path).read() if file_path else sys.stdin.read()
    urls = []
    seen = set()
    for line in text.splitlines():
        u = line.strip()
        if u and u not in seen:
            seen.add(u); urls.append(u)
    if not urls:
        sys.stderr.write("no URLs provided\n"); return 2
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        results = list(pool.map(lambda u: check_one(u, timeout), urls))
    print(json.dumps({"checked": len(results), "results": results},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
