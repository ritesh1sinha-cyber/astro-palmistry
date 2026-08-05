"""Authentication — Google Sign-In, verified server-side, with revocable sessions."""

from __future__ import annotations

import hashlib
import os
import secrets
from typing import Optional

from fastapi import Cookie, Header, HTTPException, Request

from .config import S
from .db import create_session, revoke_session, upsert_user, user_for_token

COOKIE = "ap_session"


def admin_emails() -> set[str]:
    raw = os.getenv("ADMIN_EMAILS", "") or S.admin_email
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def is_admin(user: Optional[dict]) -> bool:
    if not user:
        return False
    return (user.get("email") or "").strip().lower() in admin_emails()


def is_admin_id(user_id: str) -> bool:
    from sqlalchemy import text

    from .db import engine, jrow
    with engine().connect() as c:
        row = c.execute(text("SELECT email FROM users WHERE id = :u"),
                        {"u": user_id}).fetchone()
    return is_admin(jrow(row)) if row else False


def verify_google(id_token: str) -> dict:
    """
    Verify the ID token with Google. We never decode-and-trust: an unverified
    JWT is attacker-controlled, and the old app trusted whatever the client sent.
    """
    if not S.google_client_id:
        raise HTTPException(503, "GOOGLE_CLIENT_ID is not configured")
    try:
        from google.auth.transport import requests as g_requests
        from google.oauth2 import id_token as g_id_token
    except ImportError as exc:                                       # pragma: no cover
        raise HTTPException(503, "google-auth is not installed") from exc
    try:
        info = g_id_token.verify_oauth2_token(
            id_token, g_requests.Request(), S.google_client_id)
    except ValueError as exc:
        raise HTTPException(401, f"invalid Google token: {exc}") from exc
    if info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise HTTPException(401, "bad token issuer")
    if not info.get("email_verified", True):
        raise HTTPException(401, "email not verified with Google")
    return info


def login_with_google(id_token: str, *, ip: str = "", ua: str = "") -> tuple[dict, str]:
    info = verify_google(id_token)
    user = upsert_user(email=info["email"], name=info.get("name", ""),
                       picture=info.get("picture", ""), google_sub=info["sub"])
    return user, create_session(user["id"], ip=ip, ua=ua)


def login_dev(email: str, name: str, *, ip: str = "", ua: str = "") -> tuple[dict, str]:
    """Local development only. Guarded by DEV_LOGIN; never enable in production."""
    if not S.dev_login:
        raise HTTPException(404, "not enabled")
    user = upsert_user(email=email, name=name)
    return user, create_session(user["id"], ip=ip, ua=ua)


def login_admin(email: str, password: str, *, ip: str = "", ua: str = "") -> tuple[dict, str]:
    """Dev/staging only. Full access without payment — never enable in production."""
    if not S.dev_login:
        raise HTTPException(404, "not enabled")
    em = (email or "").strip().lower()
    if em not in admin_emails():
        raise HTTPException(401, "invalid admin credentials")
    if not secrets.compare_digest(password or "", S.admin_password):
        raise HTTPException(401, "invalid admin credentials")
    user = upsert_user(email=em, name="Admin Tester")
    return user, create_session(user["id"], ip=ip, ua=ua)


def logout(token: str) -> None:
    if token:
        revoke_session(token)


def _token_from(request: Request, authorization: Optional[str],
                cookie: Optional[str]) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    if cookie:
        return cookie
    return request.cookies.get(COOKIE, "")


async def current_user(request: Request,
                       authorization: Optional[str] = Header(default=None),
                       ap_session: Optional[str] = Cookie(default=None)) -> dict:
    token = _token_from(request, authorization, ap_session)
    if not token:
        raise HTTPException(401, "sign in required")
    user = user_for_token(token)
    if not user:
        raise HTTPException(401, "session expired — please sign in again")
    return user


async def optional_user(request: Request,
                        authorization: Optional[str] = Header(default=None),
                        ap_session: Optional[str] = Cookie(default=None)) -> Optional[dict]:
    token = _token_from(request, authorization, ap_session)
    return user_for_token(token) if token else None
