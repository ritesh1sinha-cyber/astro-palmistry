"""
Cloudflare Turnstile — bot check for expensive / public endpoints.

When TURNSTILE_SECRET is unset (local laptop), verification is skipped so
dev and e2e keep working. When the secret is set (production), every call
to `require_human` must carry a fresh token from the browser widget.
"""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from fastapi import HTTPException, Request

from .config import S


def enabled() -> bool:
    return bool((S.turnstile_secret or "").strip())


def verify(token: str, remote_ip: str = "") -> bool:
    secret = (S.turnstile_secret or "").strip()
    if not secret:
        return True
    tok = (token or "").strip()
    if not tok:
        return False
    data = urllib.parse.urlencode({
        "secret": secret,
        "response": tok,
        **({"remoteip": remote_ip} if remote_ip else {}),
    }).encode()
    req = urllib.request.Request(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            import json
            body = json.loads(resp.read().decode("utf-8", errors="replace"))
        return bool(body.get("success"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return False


def token_from(request: Optional[Request], body_token: str = "") -> str:
    if (body_token or "").strip():
        return body_token.strip()
    if request is None:
        return ""
    return (request.headers.get("x-turnstile-token") or "").strip()


def require_human(request: Optional[Request] = None, *,
                  token: str = "") -> None:
    """Raise 403 if Turnstile is configured and the token is missing/invalid."""
    if not enabled():
        return
    ip = ""
    if request is not None:
        ip = (request.client.host if request.client else "") or ""
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            ip = fwd.split(",")[0].strip() or ip
    tok = token_from(request, token)
    if not verify(tok, ip):
        raise HTTPException(
            403,
            "Please complete the “I’m not a robot” check and try again.",
        )
