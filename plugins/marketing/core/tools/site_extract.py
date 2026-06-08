#!/usr/bin/env python3
"""site_extract.py - emit a JSON inventory for one web page.

Ground-truth extractor for the `site-audit` suite (SEO, security, link-health).
Fetches the *rendered, published HTML* of a URL (or reads a saved .html file)
and emits a single JSON object describing every fact a crawler, AI agent, or
security/link auditor would see. The audit sub-agents judge this JSON against
their skill's criteria/ files - they do NOT re-parse HTML by hand, and every
finding must be traceable to a field here.

Standard library only (urllib, html.parser, json, gzip) - no pip install.
TLS protocol/cert facts come from the sibling tls_check.py; link reachability
from link_check.py. This tool fetches each page once and reports what that one
response contained, including its HTTP response headers.

Usage:
    python3 site_extract.py <url>                 # fetch and analyze a live URL
    python3 site_extract.py --file page.html      # analyze a saved file
    python3 site_extract.py <url> --file page.html  # use file body, label as url
    python3 site_extract.py <url> --timeout 20    # custom fetch timeout (s)

Output: a JSON object on stdout (see KEYS below). On a fetch error the object
contains {"url", "ok": false, "error": "..."} so callers can record the failure
without crashing the run.

Top-level KEYS:
  SEO/content: url, fetched_url, ok, http_status, redirect_chain, content_type,
    x_robots_tag, html_lang, charset, viewport, title, title_length,
    meta_description, meta_description_length, meta_robots, canonical, og, twitter,
    hreflang, headings, h1_count, img_total, img_missing_alt, word_count, jsonld,
    jsonld_types, tls_verified, notes
  security: response_headers (dict of the security-relevant headers actually
    present, lowercased), set_cookie (list of raw Set-Cookie strings), server,
    x_powered_by
  links/mixed-content: links (list of {href, text, internal, scheme}),
    link_counts ({internal, external, http, total}), mixed_content (list of
    {tag, url} subresources loaded over http:// on this page), mixed_content_count
"""
import sys
import json
import gzip
import io
import ssl
from html.parser import HTMLParser
from urllib.request import (Request, build_opener, HTTPSHandler,
                            HTTPRedirectHandler)
from urllib.parse import urlparse, urljoin
from urllib.error import URLError, HTTPError

UA = ("Mozilla/5.0 (compatible; site-audit/1.0; "
      "+https://github.com/orange-radish/agent-skills)")

# Set by fetch() when it has to fall back to an unverified TLS context (a local
# trust-store problem, e.g. macOS system Python). Surfaced in the inventory so
# the audit can disclose it - we never send credentials, only read public HTML.
TLS_UNVERIFIED = False


class _RecordingRedirect(HTTPRedirectHandler):
    """Follows redirects (like the default) but records each hop, so the audit
    can flag redirect chains and final landing status."""
    def __init__(self):
        self.chain = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.chain.append({"from": req.full_url, "status": code, "to": newurl})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, timeout, insecure=False):
    """Fetch url, recording the redirect chain via a custom opener.

    Tries a verified TLS context first. On a certificate *verification* failure
    (not a real protocol error) it retries once with verification disabled and
    sets the module-level TLS_UNVERIFIED flag. Returns
    (final_url, status, headers, body_text, redirect_chain, error)."""
    global TLS_UNVERIFIED
    ctx = ssl._create_unverified_context() if insecure else ssl.create_default_context()
    if insecure:
        TLS_UNVERIFIED = True
    redirect_handler = _RecordingRedirect()
    opener = build_opener(HTTPSHandler(context=ctx), redirect_handler)
    req = Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, identity",
    })
    try:
        resp = opener.open(req, timeout=timeout)
    except HTTPError as e:
        # HTTPError is also a response: capture its status/body/headers.
        return (e.url, e.code, (e.headers or {}), _read_body(e),
                redirect_handler.chain, None)
    except URLError as e:
        reason = e.reason
        if isinstance(reason, ssl.SSLCertVerificationError) and not insecure:
            # Local trust store can't verify - retry the whole fetch unverified.
            return fetch(url, timeout, insecure=True)
        return url, None, {}, "", redirect_handler.chain, f"URLError: {reason}"
    except Exception as e:  # noqa: BLE001 - report any fetch failure as data
        return url, None, {}, "", redirect_handler.chain, f"{type(e).__name__}: {e}"

    # Return the raw header object (email.message.Message) so build_inventory can
    # preserve duplicate Set-Cookie headers and read every security header.
    return (resp.geturl(), resp.getcode(), resp.headers,
            _read_body(resp), redirect_handler.chain, None)


def _read_body(resp):
    raw = resp.read()
    enc = (resp.headers.get("Content-Encoding") or "").lower()
    if "gzip" in enc:
        try:
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        except OSError:
            pass
    # Decode permissively; meta charset is reported separately for the agent.
    return raw.decode("utf-8", errors="replace")


# Tags whose URL attribute is a subresource the browser loads (so an http://
# value on an https page is mixed content), mapped to the attr that carries it.
_SUBRESOURCE_ATTRS = {
    "img": "src", "script": "src", "iframe": "src", "source": "src",
    "audio": "src", "video": "src", "embed": "src", "track": "src",
    "object": "data",
}
# <link rel> values that load a subresource (vs. canonical/alternate, which don't)
_SUBRESOURCE_LINK_RELS = {"stylesheet", "preload", "prefetch", "icon",
                          "apple-touch-icon", "mask-icon", "preconnect"}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = None
        self._in_title = False
        self.metas = []          # list of attr-dicts for <meta>
        self.links = []          # list of attr-dicts for <link>
        self.headings = []       # ordered [{level, text}]
        self._heading_level = None
        self._heading_buf = []
        self.img_total = 0
        self.img_missing_alt = 0
        self.html_lang = None
        self.jsonld = []         # list of {types, valid, raw}
        self._in_jsonld = False
        self._jsonld_buf = []
        self._text_parts = []
        self._skip_text_depth = 0   # inside script/style/noscript/template
        self.anchors = []        # [{href, text, rel, target}] from <a href>
        self._anchor = None      # current open anchor dict
        self._anchor_buf = []
        self.mixed_content = []  # [{tag, url}] http:// subresources (capped)
        self.notes = []

    def _note_subresource(self, tag, url):
        if url.lower().startswith("http://") and len(self.mixed_content) < 100:
            self.mixed_content.append({"tag": tag, "url": url})

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html" and "lang" in a:
            self.html_lang = a["lang"]
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.links.append(a)
            rels = a.get("rel", "").lower().split()
            if any(r in _SUBRESOURCE_LINK_RELS for r in rels):
                self._note_subresource("link", a.get("href", ""))
        elif tag == "a" and "href" in a:
            self._anchor = {"href": a["href"], "rel": a.get("rel", ""),
                            "target": a.get("target", "")}
            self._anchor_buf = []
        elif tag == "img":
            self.img_total += 1
            if not a.get("alt", "").strip() and "alt" not in a:
                self.img_missing_alt += 1
            elif "alt" in a and not a.get("alt", "").strip():
                # present-but-empty alt is intentional (decorative); not counted
                pass
            self._note_subresource("img", a.get("src", ""))
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._heading_level = int(tag[1])
            self._heading_buf = []
        elif tag == "script":
            if a.get("type", "").lower() == "application/ld+json":
                self._in_jsonld = True
                self._jsonld_buf = []
            self._note_subresource("script", a.get("src", ""))
            self._skip_text_depth += 1
        elif tag in ("style", "noscript", "template"):
            self._skip_text_depth += 1
        if tag in _SUBRESOURCE_ATTRS and tag not in ("img", "script"):
            self._note_subresource(tag, a.get(_SUBRESOURCE_ATTRS[tag], ""))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "a" and self._anchor is not None:
            self._anchor["text"] = " ".join("".join(self._anchor_buf).split())[:200]
            self.anchors.append(self._anchor)
            self._anchor = None
            self._anchor_buf = []
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self._heading_level:
            text = " ".join("".join(self._heading_buf).split())
            self.headings.append({"level": self._heading_level, "text": text})
            self._heading_level = None
            self._heading_buf = []
        elif tag == "script":
            if self._in_jsonld:
                self._record_jsonld("".join(self._jsonld_buf))
                self._in_jsonld = False
                self._jsonld_buf = []
            self._skip_text_depth = max(0, self._skip_text_depth - 1)
        elif tag in ("style", "noscript", "template"):
            self._skip_text_depth = max(0, self._skip_text_depth - 1)

    def handle_data(self, data):
        if self._in_title:
            self.title = (self.title or "") + data
        if self._in_jsonld:
            self._jsonld_buf.append(data)
        if self._heading_level:
            self._heading_buf.append(data)
        if self._anchor is not None:
            self._anchor_buf.append(data)
        if self._skip_text_depth == 0 and data.strip():
            self._text_parts.append(data)

    def _record_jsonld(self, raw):
        raw = raw.strip()
        if not raw:
            return
        entry = {"raw": raw[:4000], "valid": False, "types": []}
        try:
            data = json.loads(raw)
            entry["valid"] = True
            entry["types"] = _collect_types(data)
        except json.JSONDecodeError as e:
            entry["error"] = f"invalid JSON: {e}"
        self.jsonld.append(entry)

    def word_count(self):
        return len(" ".join(self._text_parts).split())


def _collect_types(node):
    """Recursively gather every @type value from a JSON-LD object/@graph."""
    found = []
    if isinstance(node, dict):
        t = node.get("@type")
        if isinstance(t, str):
            found.append(t)
        elif isinstance(t, list):
            found.extend(x for x in t if isinstance(x, str))
        for key in ("@graph", "mainEntity", "itemListElement"):
            if key in node:
                found.extend(_collect_types(node[key]))
    elif isinstance(node, list):
        for item in node:
            found.extend(_collect_types(item))
    return found


def _first_meta(metas, name=None, prop=None):
    for m in metas:
        if name and m.get("name", "").lower() == name.lower():
            return m.get("content", "")
        if prop and m.get("property", "").lower() == prop.lower():
            return m.get("content", "")
    return None


# Response headers the security auditor judges (lowercased). Only those actually
# present are emitted, so an absent header is visibly absent in the inventory.
_SECURITY_HEADERS = [
    "content-security-policy", "content-security-policy-report-only",
    "strict-transport-security", "x-content-type-options", "x-frame-options",
    "referrer-policy", "permissions-policy", "cross-origin-opener-policy",
    "cross-origin-embedder-policy", "cross-origin-resource-policy",
    "x-xss-protection", "content-type",
]


def _header_facts(headers):
    """From an email.message.Message (or {}), return (security_headers dict,
    set_cookie list, server, x_powered_by). Lookups are case-insensitive;
    duplicate Set-Cookie headers are preserved."""
    get = getattr(headers, "get", lambda *a, **k: None)
    present = {}
    for h in _SECURITY_HEADERS:
        v = get(h)
        if v is not None:
            present[h] = v
    set_cookie = headers.get_all("Set-Cookie") if hasattr(headers, "get_all") else []
    return present, list(set_cookie or []), get("Server"), get("X-Powered-By")


def _classify_links(anchors, page_url):
    """Resolve each <a href> against the page URL and classify it. Returns
    (links list, counts dict). Non-navigational schemes (mailto/tel/js/#) are
    recorded with that scheme but excluded from internal/external/http counts."""
    page_host = urlparse(page_url).netloc.lower()
    links, internal, external, http = [], 0, 0, 0
    for an in anchors:
        raw = (an.get("href") or "").strip()
        scheme = (urlparse(raw).scheme or "").lower()
        if raw.startswith("#") or scheme in ("mailto", "tel", "javascript", "data"):
            links.append({"href": raw, "text": an.get("text", ""),
                          "internal": None, "scheme": scheme or "fragment"})
            continue
        resolved = urljoin(page_url, raw)
        rs = urlparse(resolved)
        is_internal = rs.netloc.lower() == page_host
        if rs.scheme == "http":
            http += 1
        if is_internal:
            internal += 1
        else:
            external += 1
        links.append({"href": resolved, "text": an.get("text", ""),
                      "internal": is_internal, "scheme": rs.scheme})
    if len(links) > 300:
        links = links[:300]
    counts = {"internal": internal, "external": external, "http": http,
              "total": internal + external}
    return links, counts


def build_inventory(url, status, headers, body, chain):
    p = PageParser()
    try:
        p.feed(body)
    except Exception as e:  # noqa: BLE001 - malformed HTML shouldn't kill the run
        p.notes.append(f"parser stopped early: {type(e).__name__}: {e}")

    title = (p.title or "").strip() or None
    desc = _first_meta(p.metas, name="description")
    og = {m.get("property", "")[3:]: m.get("content", "")
          for m in p.metas
          if m.get("property", "").lower().startswith("og:")}
    twitter = {m.get("name", "")[8:]: m.get("content", "")
               for m in p.metas
               if m.get("name", "").lower().startswith("twitter:")}
    canonical = next((l.get("href") for l in p.links
                      if l.get("rel", "").lower() == "canonical"), None)
    hreflang = [{"lang": l.get("hreflang"), "href": l.get("href")}
                for l in p.links
                if l.get("rel", "").lower() == "alternate" and l.get("hreflang")]
    charset = next((m.get("charset") for m in p.metas if "charset" in m), None)
    viewport = _first_meta(p.metas, name="viewport")
    jsonld_types = sorted({t for e in p.jsonld for t in e["types"]})
    h1_count = sum(1 for h in p.headings if h["level"] == 1)
    sec_headers, set_cookie, server, x_powered_by = _header_facts(headers)
    links, link_counts = _classify_links(p.anchors, url)
    get_hdr = getattr(headers, "get", lambda *a, **k: None)

    return {
        "url": url,
        "fetched_url": url,
        "ok": status is not None and status < 400,
        "http_status": status,
        "redirect_chain": chain,
        "content_type": get_hdr("Content-Type"),
        "x_robots_tag": get_hdr("X-Robots-Tag"),
        "response_headers": sec_headers,
        "set_cookie": set_cookie,
        "server": server,
        "x_powered_by": x_powered_by,
        "links": links,
        "link_counts": link_counts,
        "mixed_content": p.mixed_content,
        "mixed_content_count": len(p.mixed_content),
        "html_lang": p.html_lang,
        "charset": charset,
        "viewport": viewport,
        "title": title,
        "title_length": len(title) if title else 0,
        "meta_description": desc,
        "meta_description_length": len(desc) if desc else 0,
        "meta_robots": _first_meta(p.metas, name="robots"),
        "canonical": canonical,
        "og": og,
        "twitter": twitter,
        "hreflang": hreflang,
        "headings": p.headings,
        "h1_count": h1_count,
        "img_total": p.img_total,
        "img_missing_alt": p.img_missing_alt,
        "word_count": p.word_count(),
        "jsonld": p.jsonld,
        "jsonld_types": jsonld_types,
        "notes": p.notes,
    }


def main(argv):
    args = argv[1:]
    url = None
    file_path = None
    timeout = 15
    i = 0
    while i < len(args):
        if args[i] == "--file":
            file_path = args[i + 1]
            i += 2
        elif args[i] == "--timeout":
            timeout = float(args[i + 1])
            i += 2
        elif args[i].startswith("-"):
            sys.stderr.write(f"unknown flag: {args[i]}\n")
            return 2
        else:
            url = args[i]
            i += 1

    if not url and not file_path:
        sys.stderr.write(__doc__)
        return 2

    if file_path:
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            body = fh.read()
        inv = build_inventory(url or file_path, 200, {}, body, [])
        print(json.dumps(inv, indent=2, ensure_ascii=False))
        return 0

    final_url, status, headers, body, chain, error = fetch(url, timeout)
    if error:
        print(json.dumps({"url": url, "fetched_url": final_url, "ok": False,
                          "http_status": status, "redirect_chain": chain,
                          "error": error}, indent=2, ensure_ascii=False))
        return 0
    inv = build_inventory(final_url, status, headers, body, chain)
    inv["url"] = url
    inv["tls_verified"] = not TLS_UNVERIFIED
    if TLS_UNVERIFIED:
        inv["notes"].append("TLS certificate not verified (local trust-store "
                            "issue); content fetched over an unverified "
                            "connection. Not an SEO finding.")
    print(json.dumps(inv, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
