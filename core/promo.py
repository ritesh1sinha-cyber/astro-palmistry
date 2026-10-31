"""Promo codes — a public offer we can actually honour.

We are about to tell the world "the first 500 users get everything free." That
is a promise with a hard number in it, made by a product whose entire pitch is
accountability. Handing out the 501st free account, or letting one person
redeem twice, would undo the positioning faster than any bad prediction.

So the cap is enforced in the database, not in application logic that races.
Two mechanisms do the work:

  1. `UPDATE ... WHERE redeemed_count < max_redemptions` — the guard lives in
     the WHERE clause, so two concurrent redemptions of the 500th slot cannot
     both succeed. The loser sees rowcount 0 and is refused. Checking the count
     first and then incrementing is the classic wrong answer; under load it
     over-issues.

  2. A unique index on (code_id, user_id) — one redemption per account, decided
     by the database rather than by a SELECT that can be overtaken.

Both run inside one transaction, so a refusal at either step rolls the other
back and the counter never drifts from the redemption rows. `redeemed_count` is
a cache; the rows are the truth, and `reconcile()` proves it.

Redemption grants entitlements through the same `billing.grant()` path a
purchase uses, with `source='promo'`. Nothing downstream needs to know how
access was acquired, which is why a refund and a promo revocation behave
identically.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text

from . import billing
from .db import engine, jrow, new_id, now, tx
from .errors import UserError

# The code a human types. Deliberately narrow: uppercase and digits only, so
# "first500" and " FIRST500 " both normalise to the same thing and O/0
# confusion is the only remaining hazard.
CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{2,31}$")


def normalise(code: str) -> str:
    return re.sub(r"\s+", "", str(code or "")).upper()


# ---------------------------------------------------------------------------
# creation (admin / seed)
# ---------------------------------------------------------------------------
def create_code(code: str, *, item: str = "bundle_all",
                max_redemptions: int = 500, expires_at: Optional[datetime] = None,
                note: str = "") -> dict:
    """Idempotent by code. Re-creating an existing code returns it untouched."""
    code = normalise(code)
    if not CODE_RE.match(code):
        raise ValueError(f"bad code format: {code!r}")
    if item not in billing.BUNDLE_ITEMS and item not in ("bundle_all",):
        # Any single purchasable item is fine too, as long as it is real.
        from .config import S
        if item not in S.prices:
            raise ValueError(f"unknown item {item!r}")
    if max_redemptions < 1:
        raise ValueError("max_redemptions must be >= 1")

    with tx() as c:
        row = c.execute(text("SELECT * FROM promo_codes WHERE code = :c"),
                        {"c": code}).fetchone()
        if row:
            return jrow(row)
        c.execute(text(
            "INSERT INTO promo_codes (id,code,item,max_redemptions,redeemed_count,"
            "active,expires_at,note,created_at)"
            " VALUES (:i,:c,:it,:m,0,1,:e,:n,:t)"),
            {"i": new_id(), "c": code, "it": item, "m": max_redemptions,
             "e": expires_at, "n": note, "t": now()})
        return jrow(c.execute(text("SELECT * FROM promo_codes WHERE code = :c"),
                             {"c": code}).fetchone())


def deactivate(code: str) -> None:
    with tx() as c:
        c.execute(text("UPDATE promo_codes SET active = 0 WHERE code = :c"),
                  {"c": normalise(code)})


# ---------------------------------------------------------------------------
# public read — what the landing page shows
# ---------------------------------------------------------------------------
def status(code: str) -> dict:
    """Safe to expose. Never reveals who redeemed, only how many slots remain."""
    code = normalise(code)
    with engine().connect() as c:
        row = c.execute(text("SELECT * FROM promo_codes WHERE code = :c"),
                        {"c": code}).fetchone()
    if not row:
        return {"code": code, "valid": False, "reason": "not_found"}
    p = jrow(row)
    left = max(0, int(p["max_redemptions"]) - int(p["redeemed_count"]))
    reason = None
    if not _truthy(p.get("active")):
        reason = "withdrawn"
    elif _expired(p.get("expires_at")):
        reason = "expired"
    elif left == 0:
        reason = "exhausted"
    return {"code": code, "valid": reason is None, "reason": reason,
            "item": p["item"], "claimed": int(p["redeemed_count"]),
            "total": int(p["max_redemptions"]), "remaining": left}


def _truthy(v: Any) -> bool:
    return v in (1, True, "1", "true", "t", "TRUE")


def _expired(v: Any) -> bool:
    if not v:
        return False
    if isinstance(v, str):
        try:
            v = datetime.fromisoformat(v)
        except ValueError:
            return False
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v <= now()


# ---------------------------------------------------------------------------
# redemption — the only path that consumes a slot
# ---------------------------------------------------------------------------
REFUSALS = {
    "not_found": "That code isn't one of ours. Check the spelling — they are "
                 "all letters and numbers, no spaces.",
    "withdrawn": "That code has been withdrawn.",
    "expired": "That code has expired.",
    "exhausted": "All the free places on this code have been claimed. We said "
                 "we would not quietly extend it, so we haven't.",
    "already": "You have already used this code — it is one per person, and "
               "your access is already on your account.",
    "wrong_item": "This code is for a different reading.",
}


def redeem(user_id: str, code: str, *, item: Optional[str] = None,
           ref_id: Optional[str] = None) -> dict:
    """Consume one slot and grant access. Raises UserError on any refusal.

    The order of operations matters: claim the per-user row first, then the
    counter. Both are guarded by the database, and both live in one
    transaction, so a failure at either step leaves nothing behind.
    """
    if bool(item) != bool(ref_id):
        raise ValueError("report-scoped redemption needs both item and ref_id")
    code = normalise(code)
    with tx() as c:
        row = c.execute(text("SELECT * FROM promo_codes WHERE code = :c"),
                        {"c": code}).fetchone()
        if not row:
            raise UserError(REFUSALS["not_found"])
        p = jrow(row)
        if not _truthy(p.get("active")):
            raise UserError(REFUSALS["withdrawn"])
        if _expired(p.get("expires_at")):
            raise UserError(REFUSALS["expired"])
        if item and p["item"] not in ("bundle_all", item):
            raise UserError(REFUSALS["wrong_item"])

        # One per person. The unique index is the real check; this SELECT only
        # exists to produce a friendly message instead of an integrity error.
        seen = c.execute(text("SELECT 1 FROM promo_redemptions"
                              " WHERE code_id = :ci AND user_id = :u"),
                         {"ci": p["id"], "u": user_id}).fetchone()
        if seen:
            raise UserError(REFUSALS["already"])

        c.execute(text("INSERT INTO promo_redemptions (id,code_id,user_id,"
                       "item,redeemed_at) VALUES (:i,:ci,:u,:it,:t)"),
                  {"i": new_id(), "ci": p["id"], "u": user_id,
                   "it": p["item"], "t": now()})

        # The cap. The guard is in the WHERE clause on purpose — see module
        # docstring. rowcount 0 means somebody else took the last slot between
        # our read and our write.
        res = c.execute(text(
            "UPDATE promo_codes SET redeemed_count = redeemed_count + 1"
            " WHERE id = :i AND redeemed_count < max_redemptions"),
            {"i": p["id"]})
        if res.rowcount != 1:
            raise UserError(REFUSALS["exhausted"])   # rolls back the insert

        claimed = int(p["redeemed_count"]) + 1

    # Grants happen after the counter is safely taken. If a grant were to fail
    # the slot is still consumed, which is the conservative direction: we would
    # rather owe one person a support fix than hand out an extra free account.
    items = (item,) if item else billing.expand(p["item"])
    for it in items:
        billing.grant(user_id, it, ref_id=ref_id, source="promo")

    return {"ok": True, "code": code, "item": item or p["item"], "granted": items,
            "claimed": claimed, "total": int(p["max_redemptions"]),
            "remaining": max(0, int(p["max_redemptions"]) - claimed)}


# ---------------------------------------------------------------------------
# reconciliation — the counter is a cache, the rows are the truth
# ---------------------------------------------------------------------------
def reconcile(code: Optional[str] = None) -> list[dict]:
    """Report (and repair) any drift between redeemed_count and actual rows."""
    out = []
    with tx() as c:
        q = "SELECT id, code, redeemed_count FROM promo_codes"
        params: dict = {}
        if code:
            q += " WHERE code = :c"
            params["c"] = normalise(code)
        for row in c.execute(text(q), params).fetchall():
            p = jrow(row)
            real = c.execute(text("SELECT COUNT(*) FROM promo_redemptions"
                                  " WHERE code_id = :i"), {"i": p["id"]}).scalar()
            if int(real) != int(p["redeemed_count"]):
                c.execute(text("UPDATE promo_codes SET redeemed_count = :r"
                               " WHERE id = :i"), {"r": real, "i": p["id"]})
                out.append({"code": p["code"], "was": int(p["redeemed_count"]),
                            "now": int(real)})
    return out
