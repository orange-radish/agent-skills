#!/usr/bin/env python3
"""tls_check.py - probe a host's TLS configuration and certificate.

Companion to site_extract.py for the `site-audit` suite's security checks.
Connects to <host>:443, reports the negotiated protocol + cipher, certificate
expiry/subject/issuer, and whether deprecated protocols (TLS 1.0 / 1.1) are
still accepted. Standard library only (ssl, socket).

Usage:
    python3 tls_check.py <host-or-url>          # e.g. example.com or https://example.com/x
    python3 tls_check.py <host> --port 8443
    python3 tls_check.py <host> --timeout 10

Output: one JSON object on stdout. On connection failure: {"host","ok":false,"error"}.

Notes / honesty:
- Certificate fields require a trusted handshake. If this Python's trust store
  can't verify the chain (e.g. macOS system Python), we still report the
  negotiated protocol + cipher from an unverified handshake and set
  `cert_verified: false` with `cert: null` rather than guessing.
- The deprecated-protocol probe depends on the local OpenSSL still supporting
  TLS 1.0/1.1 to *offer* them; if the client can't, the result is "unknown".
"""
import sys
import ssl
import json
import socket
import warnings
from datetime import datetime, timezone
from urllib.parse import urlparse


def _host_port(arg, default_port):
    if "://" in arg or arg.startswith("//"):
        u = urlparse(arg if "://" in arg else "https:" + arg)
        return u.hostname, (u.port or default_port)
    if "/" in arg:
        arg = arg.split("/", 1)[0]
    if ":" in arg:
        h, p = arg.rsplit(":", 1)
        if p.isdigit():
            return h, int(p)
    return arg, default_port


def _negotiate(host, port, timeout):
    """Verified handshake first; fall back to unverified to still read the
    protocol/cipher. Returns (version, cipher_name, cert_dict_or_None, verified)."""
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                return ss.version(), (ss.cipher() or [None])[0], ss.getpeercert(), True
    except ssl.SSLCertVerificationError:
        pass  # local trust problem - retry unverified just to read protocol/cipher
    ctx2 = ssl._create_unverified_context()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with ctx2.wrap_socket(sock, server_hostname=host) as ss:
            return ss.version(), (ss.cipher() or [None])[0], None, False


def _accepts_protocol(host, port, timeout, tls_version):
    """Force a single protocol version and report whether the server accepts it.
    Returns True / False / None(unknown - client can't offer it)."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # pinning TLS1.0/1.1 warns; intentional
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            ctx.minimum_version = tls_version
            ctx.maximum_version = tls_version
    except (ValueError, AttributeError):
        return None  # this OpenSSL build won't let us pin that version
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host):
                return True
    except (ssl.SSLError, OSError):
        return False


def _cert_summary(cert):
    if not cert:
        return None
    not_after = cert.get("notAfter")
    days = None
    if not_after:
        try:
            exp = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            days = (exp - datetime.now(timezone.utc)).days
        except ValueError:
            pass
    subject = dict(x[0] for x in cert.get("subject", []))
    issuer = dict(x[0] for x in cert.get("issuer", []))
    sans = [v for k, v in cert.get("subjectAltName", []) if k == "DNS"]
    return {
        "subject_cn": subject.get("commonName"),
        "issuer_org": issuer.get("organizationName") or issuer.get("commonName"),
        "not_before": cert.get("notBefore"),
        "not_after": not_after,
        "days_until_expiry": days,
        "san_dns": sans,
    }


def check(host, port, timeout):
    try:
        version, cipher, cert, verified = _negotiate(host, port, timeout)
    except Exception as e:  # noqa: BLE001 - report any failure as data
        return {"host": host, "port": port, "ok": False,
                "error": f"{type(e).__name__}: {e}"}

    deprecated = {}
    for label, ver in (("tls1_0", getattr(ssl.TLSVersion, "TLSv1", None)),
                       ("tls1_1", getattr(ssl.TLSVersion, "TLSv1_1", None))):
        deprecated[label] = (None if ver is None
                             else _accepts_protocol(host, port, timeout, ver))

    return {
        "host": host,
        "port": port,
        "ok": True,
        "negotiated_protocol": version,
        "cipher": cipher,
        "cert_verified": verified,
        "cert": _cert_summary(cert),
        "accepts_deprecated": deprecated,  # True = server still allows it (a finding)
        "notes": ([] if verified else
                  ["Certificate chain not verified by this host's trust store; "
                   "protocol/cipher are still accurate, cert fields omitted."]),
    }


def main(argv):
    args = argv[1:]
    host_arg = None
    port = 443
    timeout = 10.0
    i = 0
    while i < len(args):
        if args[i] == "--port":
            port = int(args[i + 1]); i += 2
        elif args[i] == "--timeout":
            timeout = float(args[i + 1]); i += 2
        elif args[i].startswith("-"):
            sys.stderr.write(f"unknown flag: {args[i]}\n"); return 2
        else:
            host_arg = args[i]; i += 1
    if not host_arg:
        sys.stderr.write(__doc__); return 2
    host, port = _host_port(host_arg, port)
    print(json.dumps(check(host, port, timeout), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
