#!/usr/bin/env python3
"""seo_extract.py - emit a JSON SEO inventory for one web page.

Ground-truth extractor for the `seo-audit` skill. Fetches the *rendered,
published HTML* of a URL (or reads a saved .html file) and emits a single JSON
object describing every SEO / structured-data fact a crawler or AI agent would
see. The agents judge this JSON against the skill's criteria/ files - they do
NOT re-parse HTML by hand, and every finding must be traceable to a field here.

Standard library only (urllib, html.parser, json, gzip) - no pip install.

Usage:
    python3 seo_extract.py <url>                 # fetch and analyze a live URL
    python3 seo_extract.py --file page.html      # analyze a saved file
    python3 seo_extract.py <url> --file page.html  # use file body, label as url
    python3 seo_extract.py <url> --timeout 20    # custom fetch timeout (s)

Output: a JSON object on stdout (see KEYS below). On a fetch error the object
contains {"url", "ok": false, "error": "..."} so callers can record the failure
without crashing the run.

Top-level KEYS:
  url, fetched_url, ok, http_status, redirect_chain, content_type, x_robots_tag,
  html_lang, charset, viewport, title, title_length, meta_description,
  meta_description_length, meta_robots, canonical, og (dict), twitter (dict),
  hreflang (list), headings (ordered list of {level,text}), h1_count,
  img_total, img_missing_alt, word_count, jsonld (list of {types, valid, raw}),
  jsonld_types (flat list), notes (list of parser-level observations).
"""
import sys
import json
import gzip
import io
import ssl
from html.parser import HTMLParser
from urllib.request import (Request, build_opener, HTTPSHandler,
                            HTTPRedirectHandler)
from urllib.error import URLError, HTTPError

UA = ("Mozilla/5.0 (compatible; site-seo-audit/1.0; "
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
        # HTTPError is also a response: capture its status/body.
        return (e.url, e.code, dict(e.headers or {}), _read_body(e),
                redirect_handler.chain, None)
    except URLError as e:
        reason = e.reason
        if isinstance(reason, ssl.SSLCertVerificationError) and not insecure:
            # Local trust store can't verify - retry the whole fetch unverified.
            return fetch(url, timeout, insecure=True)
        return url, None, {}, "", redirect_handler.chain, f"URLError: {reason}"
    except Exception as e:  # noqa: BLE001 - report any fetch failure as data
        return url, None, {}, "", redirect_handler.chain, f"{type(e).__name__}: {e}"

    return (resp.geturl(), resp.getcode(), dict(resp.headers),
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


class SEOParser(HTMLParser):
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
        self.notes = []

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
        elif tag == "img":
            self.img_total += 1
            if not a.get("alt", "").strip() and "alt" not in a:
                self.img_missing_alt += 1
            elif "alt" in a and not a.get("alt", "").strip():
                # present-but-empty alt is intentional (decorative); not counted
                pass
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._heading_level = int(tag[1])
            self._heading_buf = []
        elif tag == "script":
            if a.get("type", "").lower() == "application/ld+json":
                self._in_jsonld = True
                self._jsonld_buf = []
            self._skip_text_depth += 1
        elif tag in ("style", "noscript", "template"):
            self._skip_text_depth += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
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


def build_inventory(url, status, headers, body, chain):
    p = SEOParser()
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

    return {
        "url": url,
        "fetched_url": url,
        "ok": status is not None and status < 400,
        "http_status": status,
        "redirect_chain": chain,
        "content_type": headers.get("Content-Type"),
        "x_robots_tag": headers.get("X-Robots-Tag"),
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
