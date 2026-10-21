"""No untrusted content is executable. Network targets are explicit allowlists."""

import hashlib
import ipaddress
import json
import re
import socket
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def canonical_url(url: str) -> str:
    p = urlsplit(url)
    if p.scheme not in {"http", "https"} or not p.hostname or p.username or p.password:
        raise ValueError("URL must be public HTTP(S), without credentials")
    tracking = {"fbclid", "gclid", "igshid", "si"}
    if any(
        k.lower() in {"access_token", "api_key", "token", "key", "signature"}
        for k, _ in parse_qsl(p.query)
    ):
        raise ValueError("URL credential parameters are forbidden in evidence")
    query = [
        (k, v) for k, v in parse_qsl(p.query) if not k.startswith("utm_") and k not in tracking
    ]
    return urlunsplit(
        (p.scheme.lower(), p.netloc.lower(), p.path or "/", urlencode(sorted(query)), "")
    )


def validate_target(url: str, allowed: set[str], resolve=True) -> str:
    url = canonical_url(url)
    p = urlsplit(url)
    host = p.hostname
    if host not in allowed or p.port not in {None, 80, 443} or host == "localhost":
        raise ValueError("TARGET_NOT_ALLOWLISTED")
    if resolve:
        addresses = {
            a[4][0] for a in socket.getaddrinfo(host, p.port or 443, type=socket.SOCK_STREAM)
        }
        if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
            raise ValueError("PRIVATE_NETWORK_BLOCKED")
    else:
        try:
            if not ipaddress.ip_address(host).is_global:
                raise ValueError("PRIVATE_NETWORK_BLOCKED")
        except ValueError as exc:
            if str(exc) == "PRIVATE_NETWORK_BLOCKED":
                raise
    return url


def redact(text: str, secrets=()) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[SECRET]")
    text = re.sub(r"(?i)(bearer\s+)[\w.\-]+", r"\1[SECRET]", text)
    text = re.sub(r"(?i)([?&](?:key|token|access_token|api_key)=)[^&\s]+", r"\1[SECRET]", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", text)
    text = re.sub(r"(?<!\w)(?:\+?62|0)\d[\d ()-]{7,15}\d(?!\w)", "[PHONE]", text)
    return re.sub(r"(?<!\d)\d{16}(?!\d)", "[NIK]", text)


def safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    temporary.replace(path)
