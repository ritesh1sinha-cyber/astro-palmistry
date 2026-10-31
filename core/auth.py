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


def promo_login_emails() -> set[str]:
    """Passcode / “Login via promocode” accounts — full readings, not admin."""
    raw = os.getenv("PROMO_LOGIN_EMAILS", "") or "guest@graharekha.co.in"
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def is_admin(user: Optional[dict]) -> bool:
    if not user:
        return False
    return (user.get("email") or "").strip().lower() in admin_emails()


def is_promo_login(user: Optional[dict]) -> bool:
    if not user:
        return False
    return (user.get("email") or "").strip().lower() in promo_login_emails()


def is_dev_user(user: Optional[dict]) -> bool:
    if not user or user.get("google_sub"):
        return False
    return ((user.get("email") or "").strip().lower()
            == (S.dev_email or "").strip().lower())


def has_full_access(user: Optional[dict]) -> bool:
    """Unlock paid halves without payment. Admin or promocode login."""
    return is_admin(user) or is_promo_login(user)


def has_report_access(user: Optional[dict], item: str = "") -> bool:
    if item == "classical_report":
        return is_admin(user)
    return has_full_access(user) or is_dev_user(user)


def is_admin_id(user_id: str) -> bool:
    from sqlalchemy import text

    from .db import engine, jrow
    with engine().connect() as c:
        row = c.execute(text("SELECT email FROM users WHERE id = :u"),
                        {"u": user_id}).fetchone()
    return is_admin(jrow(row)) if row else False


def has_full_access_id(user_id: str) -> bool:
    from sqlalchemy import text

    from .db import engine, jrow
    with engine().connect() as c:
        row = c.execute(text("SELECT email FROM users WHERE id = :u"),
                        {"u": user_id}).fetchone()
    return has_full_access(jrow(row)) if row else False


def has_report_access_id(user_id: str, item: str = "") -> bool:
    from sqlalchemy import text

    from .db import engine, jrow
    with engine().connect() as c:
        row = c.execute(text("SELECT * FROM users WHERE id = :u"),
                        {"u": user_id}).fetchone()
    return has_report_access(jrow(row), item) if row else False


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


def login_dev(email: str, name: str, *, passcode: str = "",
              ip: str = "", ua: str = "") -> tuple[dict, str]:
    """Promocode / passcode login. Guarded by DEV_LOGIN; never enable in production."""
    if not S.dev_login:
        raise HTTPException(404, "not enabled")
    expected = S.guest_passcode or ""
    if not expected or not secrets.compare_digest(passcode or "", expected):
        raise HTTPException(401, "invalid guest passcode")
    em = (email or "").strip().lower()
    if em == (S.dev_email or "").strip().lower():
        raise HTTPException(403, "use dev sign-in for this account")
    if em and em not in admin_emails():
        target_em = em
    else:
        target_em = next(iter(sorted(promo_login_emails())), "guest@graharekha.co.in")
    user = upsert_user(email=target_em, name=name or ("Promocode guest" if target_em.startswith("guest") else "Test User"))
    return user, create_session(user["id"], ip=ip, ua=ua)


def login_report_dev(username: str, password: str, *,
                     ip: str = "", ua: str = "") -> tuple[dict, str]:
    """Report-only dev login; never an admin or a Google identity."""
    if not S.dev_login:
        raise HTTPException(404, "not enabled")
    user_ok = secrets.compare_digest((username or "").strip(), S.dev_username or "")
    pass_ok = secrets.compare_digest(password or "", S.dev_password or "")
    if not (user_ok and pass_ok):
        raise HTTPException(401, "invalid dev credentials")
    user = upsert_user(email=(S.dev_email or "").strip().lower(), name="GrahaRekha Dev")
    return user, create_session(user["id"], ip=ip, ua=ua)


def login_admin(username: str = "", password: str = "", *,
                email: str = "", ip: str = "", ua: str = "") -> tuple[dict, str]:
    """Admin login with full unlock. Guarded by DEV_LOGIN."""
    if not S.dev_login:
        raise HTTPException(404, "not enabled")
    u = (username or "").strip()
    em = (email or "").strip().lower()
    # Accept username from `.config`, or the admin email (legacy clients).
    user_ok = bool(u) and secrets.compare_digest(u, S.admin_username or "")
    email_ok = bool(em) and em in admin_emails()
    if not (user_ok or email_ok):
        raise HTTPException(401, "invalid admin credentials")
    if not secrets.compare_digest(password or "", S.admin_password or ""):
        raise HTTPException(401, "invalid admin credentials")
    admin_em = (S.admin_email or "graharekha@graharekha.local").strip().lower()
    user = upsert_user(email=admin_em, name="GrahaRekha Admin")
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
