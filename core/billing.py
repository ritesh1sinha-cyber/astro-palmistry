"""
Money and access.

Two ideas keep this honest at scale:

  1. `orders` says what was PAID. `entitlements` says what may be SEEN. They are
     separate tables, so a refund revokes access without erasing payment history,
     and a promo or support grant uses the same access path as a purchase.

  2. An order is marked paid only against a valid Razorpay HMAC signature. That
     signature reaches us two ways — the webhook, and the checkout callback the
     browser relays — and both are verified with the same key material here.
     Nothing unsigned is trusted, from either direction.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import text

from .config import S
from .db import engine, jdump, jrow, new_id, now, tx

FREE_ITEMS = {"chart_summary", "numerology", "daily_free"}

# What "everything" means. `bundle_all` is a price, not a permission — nothing
# downstream reads an entitlement called `bundle_all`, so granting it verbatim
# would take Rs 2,100 and unlock nothing. It expands here, once, and both the
# purchase path and the promo path go through `expand()` so they cannot drift.
BUNDLE_ITEMS = ("full_report", "classical_report", "btr", "kundali_match",
                "palm_full", "future_event", "horary", "user_question",
                "muhurat", "daily", "numerology_full")


def expand(item: str) -> tuple[str, ...]:
    """The entitlements an item actually confers."""
    return BUNDLE_ITEMS if item == "bundle_all" else (item,)


#: Items that are legitimately account-wide (no single report behind them).
ACCOUNT_WIDE_ITEMS = ("subscription", "bundle_all")

_ITEM_REPORT_KIND = {"palm_full": "palm", "numerology_full": "numerology"}


def report_kind_for_item(item: str) -> str:
    """The stored report kind a purchasable item unlocks."""
    return _ITEM_REPORT_KIND.get(item, item)


def latest_report_id(user_id: str, item: str) -> Optional[str]:
    """The customer's most recent report of the kind `item` unlocks."""
    with engine().connect() as c:
        row = c.execute(text("SELECT id FROM reports WHERE user_id = :u AND kind = :k"
                             " ORDER BY created_at DESC LIMIT 1"),
                        {"u": user_id, "k": report_kind_for_item(item)}).fetchone()
    return str(row[0]) if row else None


def already_unlocked(user_id: str, item: str, ref_id: Optional[str]) -> bool:
    """True when a real grant already covers this item and report. Unlike
    entitled(), admin/promo access does not count, so staff can still test
    checkout; and a subscription never counts, so renewals still work."""
    if item in ACCOUNT_WIDE_ITEMS or item in FREE_ITEMS:
        return False
    with engine().connect() as c:
        if ref_id:
            row = c.execute(text(
                "SELECT 1 FROM entitlements WHERE user_id=:u AND item=:i"
                " AND (ref_id = :r OR ref_id IS NULL) AND revoked_at IS NULL"
                " AND (expires_at IS NULL OR expires_at > :now) LIMIT 1"),
                {"u": user_id, "i": item, "r": ref_id, "now": now()}).fetchone()
        else:
            row = c.execute(text(
                "SELECT 1 FROM entitlements WHERE user_id=:u AND item=:i"
                " AND ref_id IS NULL AND revoked_at IS NULL"
                " AND (expires_at IS NULL OR expires_at > :now) LIMIT 1"),
                {"u": user_id, "i": item, "now": now()}).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# entitlements
# ---------------------------------------------------------------------------
def grant(user_id: str, item: str, *, ref_id: Optional[str] = None,
          source: str = "order", order_id: Optional[str] = None,
          days: Optional[int] = None) -> None:
    expires = (now() + timedelta(days=days)) if days else None
    from sqlalchemy.exc import IntegrityError
    try:
        _grant_once(user_id, item, ref_id, source, order_id, expires)
    except IntegrityError:
        # Two payers of the same grant raced past the existence check; the
        # unique index let exactly one through, which is all we wanted.
        pass


def _grant_once(user_id, item, ref_id, source, order_id, expires) -> None:
    with tx() as c:
        # Postgres cannot infer the type of a bare NULL bind param; ref_id is UUID.
        if ref_id is None:
            existing = c.execute(text(
                "SELECT id FROM entitlements WHERE user_id=:u AND item=:i"
                " AND ref_id IS NULL AND revoked_at IS NULL"),
                {"u": user_id, "i": item}).fetchone()
        else:
            existing = c.execute(text(
                "SELECT id FROM entitlements WHERE user_id=:u AND item=:i"
                " AND ref_id = :r AND revoked_at IS NULL"),
                {"u": user_id, "i": item, "r": ref_id}).fetchone()
        if existing:
            if expires:
                c.execute(text("UPDATE entitlements SET expires_at = :e WHERE id = :id"),
                          {"e": expires, "id": existing._mapping["id"]})
            return
        c.execute(text("INSERT INTO entitlements (id,user_id,item,ref_id,source,"
                       "order_id,granted_at,expires_at)"
                       " VALUES (:i,:u,:it,:r,:s,:o,:t,:e)"),
                  {"i": new_id(), "u": user_id, "it": item, "r": ref_id,
                   "s": source, "o": order_id, "t": now(), "e": expires})


def revoke(user_id: str, item: str, ref_id: Optional[str] = None) -> None:
    with tx() as c:
        if ref_id is None:
            c.execute(text("UPDATE entitlements SET revoked_at = :t"
                           " WHERE user_id=:u AND item=:i"
                           " AND ref_id IS NULL AND revoked_at IS NULL"),
                      {"t": now(), "u": user_id, "i": item})
        else:
            c.execute(text("UPDATE entitlements SET revoked_at = :t"
                           " WHERE user_id=:u AND item=:i"
                           " AND ref_id = :r AND revoked_at IS NULL"),
                      {"t": now(), "u": user_id, "i": item, "r": ref_id})


def entitled(user_id: str, item: str, ref_id: Optional[str] = None) -> bool:
    """Item-specific grant, or an account-wide grant, or an active subscription."""
    from .auth import has_full_access_id
    if has_full_access_id(user_id):
        return True
    if item in FREE_ITEMS:
        return True
    with engine().connect() as c:
        if ref_id is None:
            row = c.execute(text(
                "SELECT 1 FROM entitlements WHERE user_id=:u AND item=:i"
                "   AND ref_id IS NULL"
                "   AND revoked_at IS NULL"
                "   AND (expires_at IS NULL OR expires_at > :now) LIMIT 1"),
                {"u": user_id, "i": item, "now": now()}).fetchone()
        else:
            row = c.execute(text(
                "SELECT 1 FROM entitlements WHERE user_id=:u AND item=:i"
                "   AND (ref_id = :r OR ref_id IS NULL)"
                "   AND revoked_at IS NULL"
                "   AND (expires_at IS NULL OR expires_at > :now) LIMIT 1"),
                {"u": user_id, "i": item, "r": ref_id, "now": now()}).fetchone()
        if row:
            return True
        if item in ("daily", "muhurat", "horary"):
            return is_subscribed(user_id, conn=c)
    return False


def is_subscribed(user_id: str, conn=None) -> bool:
    q = text("SELECT 1 FROM subscriptions WHERE user_id=:u AND status='active'"
             " AND current_period_end > :now LIMIT 1")
    if conn is not None:
        return conn.execute(q, {"u": user_id, "now": now()}).fetchone() is not None
    with engine().connect() as c:
        return c.execute(q, {"u": user_id, "now": now()}).fetchone() is not None


def pin_subscribed_daily_reports(user_id: str) -> int:
    """Permanently unlock daily reports generated during a subscription period.

    Without this, reports saved with paid=false before we pinned them would
    re-lock when the subscription entitlement expires even though the reader
    generated them while subscribed.
    """
    with tx() as c:
        if S.is_postgres:
            r = c.execute(text(
                "UPDATE reports r SET paid = true "
                "FROM subscriptions s "
                "WHERE r.user_id = :u AND r.kind = 'daily' AND r.paid = false "
                "  AND r.user_id = s.user_id "
                "  AND r.created_at >= s.created_at "
                "  AND r.created_at <= s.current_period_end"
            ), {"u": user_id})
        else:
            r = c.execute(text(
                "UPDATE reports SET paid = 1 "
                "WHERE user_id = :u AND kind = 'daily' AND paid = 0 "
                "  AND EXISTS ("
                "    SELECT 1 FROM subscriptions s "
                "    WHERE s.user_id = reports.user_id "
                "      AND reports.created_at >= s.created_at "
                "      AND reports.created_at <= s.current_period_end"
                "  )"
            ), {"u": user_id})
        return int(r.rowcount or 0)


def pin_all_subscribed_daily_reports() -> int:
    """One-time / startup backfill across every account with subscription history."""
    with engine().connect() as c:
        rows = c.execute(text("SELECT DISTINCT user_id FROM subscriptions")).fetchall()
    total = 0
    for row in rows:
        uid = row[0] if not hasattr(row, "_mapping") else row._mapping["user_id"]
        total += pin_subscribed_daily_reports(uid)
    return total


def subscription_of(user_id: str) -> Optional[dict]:
    with engine().connect() as c:
        row = c.execute(text("SELECT * FROM subscriptions WHERE user_id=:u"
                             " ORDER BY current_period_end DESC LIMIT 1"),
                        {"u": user_id}).fetchone()
    return jrow(row) if row else None


# ---------------------------------------------------------------------------
# usage metering (free tiers)
# ---------------------------------------------------------------------------
def use_quota(user_id: str, kind: str, limit: int, period: str) -> tuple[bool, int]:
    """Consume one unit. Returns (allowed, remaining_after)."""
    with tx() as c:
        row = c.execute(text("SELECT used FROM usage_counters"
                             " WHERE user_id=:u AND kind=:k AND period=:p"),
                        {"u": user_id, "k": kind, "p": period}).fetchone()
        used = row._mapping["used"] if row else 0
        if used >= limit:
            return False, 0
        if row:
            c.execute(text("UPDATE usage_counters SET used = used + 1, updated_at = :t"
                           " WHERE user_id=:u AND kind=:k AND period=:p"),
                      {"t": now(), "u": user_id, "k": kind, "p": period})
        else:
            c.execute(text("INSERT INTO usage_counters (user_id,kind,period,used,updated_at)"
                           " VALUES (:u,:k,:p,1,:t)"),
                      {"u": user_id, "k": kind, "p": period, "t": now()})
        return True, limit - used - 1


def quota_left(user_id: str, kind: str, limit: int, period: str) -> int:
    with engine().connect() as c:
        row = c.execute(text("SELECT used FROM usage_counters"
                             " WHERE user_id=:u AND kind=:k AND period=:p"),
                        {"u": user_id, "k": kind, "p": period}).fetchone()
    return max(0, limit - (row._mapping["used"] if row else 0))


def month_period() -> str:
    return now().strftime("%Y-%m")


# ---------------------------------------------------------------------------
# IST daily report-generation cap (protects workers + LLM from abuse)
# ---------------------------------------------------------------------------
REPORT_GEN_COUNTER = "report_gen_ist"

# Job kinds that run the full engine stack — counted against the daily cap.
GENERATION_LIMIT_KINDS: frozenset[str] = frozenset({
    "palm", "full_report", "classical_report", "horary", "user_question",
    "numerology", "daily", "kundali_match", "muhurat", "btr", "future_event",
})


def _ist_tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Asia/Kolkata")
    except Exception:  # noqa: BLE001
        return timezone(timedelta(hours=5, minutes=30))


def ist_day_period() -> str:
    """IST calendar date string — resets at 12:00 AM IST."""
    return datetime.now(_ist_tz()).date().isoformat()


def ist_day_utc_range() -> tuple[datetime, datetime]:
    """UTC bounds [start, end) for the current IST calendar day."""
    tz = _ist_tz()
    now_ist = datetime.now(tz)
    start_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    end_ist = start_ist + timedelta(days=1)
    return start_ist.astimezone(timezone.utc), end_ist.astimezone(timezone.utc)


def paid_report_bonus_today(user_id: str) -> int:
    """Extra generation slots from single-report purchases today (IST)."""
    start, end = ist_day_utc_range()
    with engine().connect() as c:
        row = c.execute(text(
            "SELECT COUNT(*) AS n FROM orders WHERE user_id=:u AND status='paid'"
            " AND item NOT IN ('subscription')"
            " AND paid_at >= :s AND paid_at < :e"),
                        {"u": user_id, "s": start, "e": end}).fetchone()
    return int((row._mapping["n"] if row else 0) or 0)


def report_gen_allowance(user_id: str) -> int:
    """Today's generation budget: base cap + one per paid report bought today."""
    from .auth import has_full_access_id
    if has_full_access_id(user_id):
        return 999_999
    return max(0, int(S.sub_daily_gen_limit or 0)) + paid_report_bonus_today(user_id)


def report_gen_used(user_id: str) -> int:
    period = ist_day_period()
    with engine().connect() as c:
        row = c.execute(text("SELECT used FROM usage_counters"
                             " WHERE user_id=:u AND kind=:k AND period=:p"),
                        {"u": user_id, "k": REPORT_GEN_COUNTER,
                         "p": period}).fetchone()
    return int((row._mapping["used"] if row else 0) or 0)


def report_gen_remaining(user_id: str) -> int:
    from .auth import has_full_access_id
    if has_full_access_id(user_id):
        return 999_999
    return max(0, report_gen_allowance(user_id) - report_gen_used(user_id))


def consume_report_generation(user_id: str) -> tuple[bool, int]:
    """Consume one IST-day generation slot. Returns (allowed, remaining_after)."""
    from .auth import has_full_access_id
    if has_full_access_id(user_id):
        return True, 999_999
    allowance = report_gen_allowance(user_id)
    period = ist_day_period()
    with tx() as c:
        row = c.execute(text("SELECT used FROM usage_counters"
                             " WHERE user_id=:u AND kind=:k AND period=:p"),
                        {"u": user_id, "k": REPORT_GEN_COUNTER,
                         "p": period}).fetchone()
        used = int((row._mapping["used"] if row else 0) or 0)
        if used >= allowance:
            return False, 0
        if row:
            c.execute(text("UPDATE usage_counters SET used = used + 1, updated_at = :t"
                           " WHERE user_id=:u AND kind=:k AND period=:p"),
                      {"t": now(), "u": user_id, "k": REPORT_GEN_COUNTER,
                       "p": period})
        else:
            c.execute(text("INSERT INTO usage_counters (user_id,kind,period,used,updated_at)"
                           " VALUES (:u,:k,:p,1,:t)"),
                      {"u": user_id, "k": REPORT_GEN_COUNTER, "p": period,
                       "t": now()})
        return True, max(0, allowance - used - 1)


def refund_report_generation(user_id: str, kind: str) -> None:
    """Give back today's slot when a job fails without producing a report
    (unreadable photo, engine error): the customer got nothing, so it must not
    count against the daily cap. Best effort."""
    from .auth import has_full_access_id
    if kind not in GENERATION_LIMIT_KINDS or has_full_access_id(user_id):
        return
    try:
        with tx() as c:
            c.execute(text("UPDATE usage_counters SET used = used - 1, updated_at = :t"
                           " WHERE user_id=:u AND kind=:k AND period=:p AND used > 0"),
                      {"t": now(), "u": user_id, "k": REPORT_GEN_COUNTER,
                       "p": ist_day_period()})
    except Exception as exc:  # noqa: BLE001
        print(f"[billing] generation refund skipped: {exc}", flush=True)


def check_report_generation(user_id: str, kind: str) -> tuple[bool, int, int]:
    """Returns (allowed, remaining_after_if_consumed, allowance_today)."""
    from .auth import has_full_access_id
    # Everyone is capped (free and subscribed alike); only full-access/admin
    # accounts are exempt. One login must not be able to flood the queue.
    if has_full_access_id(user_id) or kind not in GENERATION_LIMIT_KINDS:
        return True, 999_999, 999_999
    allowance = report_gen_allowance(user_id)
    used = report_gen_used(user_id)
    remaining = max(0, allowance - used)
    return used < allowance, remaining, allowance


def daily_trial_used_count(user_id: str) -> int:
    """Count of unlocked full daily reports generated for this account."""
    paid_clause = "paid = true" if S.is_postgres else "paid = 1"
    with engine().connect() as c:
        row = c.execute(text(
            f"SELECT COUNT(*) FROM reports "
            f"WHERE user_id = :u AND kind = 'daily' AND {paid_clause}"
        ), {"u": user_id}).fetchone()
        return int(row[0] if row else 0)


def daily_trial_remaining(user_id: str) -> int:
    """Number of free full daily report generations left (out of FREE_DAILY, default 3)."""
    from .auth import has_full_access_id
    if has_full_access_id(user_id) or is_subscribed(user_id):
        return 0
    used = daily_trial_used_count(user_id)
    return max(0, S.free_daily - used)


def daily_trial_grants_full(user_id: str) -> bool:
    return daily_trial_remaining(user_id) > 0


# ---------------------------------------------------------------------------
# credits (append-only ledger; users.credits is a cache of it)
# ---------------------------------------------------------------------------
def credit(user_id: str, delta: int, reason: str, ref_id: Optional[str] = None) -> int:
    with tx() as c:
        row = c.execute(text("SELECT credits FROM users WHERE id = :u"),
                        {"u": user_id}).fetchone()
        bal = (row._mapping["credits"] if row else 0) + delta
        if bal < 0:
            raise ValueError("insufficient credits")
        c.execute(text("UPDATE users SET credits = :b WHERE id = :u"),
                  {"b": bal, "u": user_id})
        c.execute(text("INSERT INTO credit_ledger (user_id,delta,reason,ref_id,"
                       "balance_after,created_at) VALUES (:u,:d,:r,:ref,:b,:t)"),
                  {"u": user_id, "d": delta, "r": reason, "ref": ref_id,
                   "b": bal, "t": now()})
        return bal


# ---------------------------------------------------------------------------
# orders
# ---------------------------------------------------------------------------
def create_order(user_id: str, item: str, *, ref_id: Optional[str] = None,
                 idempotency_key: Optional[str] = None) -> dict:
    amount = S.price(item)
    if idempotency_key:
        with engine().connect() as c:
            row = c.execute(text("SELECT * FROM orders WHERE idempotency_key = :k"),
                            {"k": idempotency_key}).fetchone()
            if row:
                return _order_public(jrow(row))

    # A double tap, a retry or a bot must not mint a fresh order (and a fresh
    # gateway order) each time. Reuse this user's still-open order for the same
    # item and report; the customer then sees one checkout, not four.
    with engine().connect() as c:
        ref_sql = "ref_id = :r" if ref_id else "ref_id IS NULL"
        params = {"u": user_id, "it": item,
                  "since": now() - timedelta(minutes=30)}
        if ref_id:
            params["r"] = ref_id
        row = c.execute(
            text("SELECT * FROM orders WHERE user_id = :u AND item = :it AND "
                 + ref_sql + " AND status = 'created' AND created_at > :since"
                 " ORDER BY created_at DESC LIMIT 1"), params).fetchone()
    if row:
        return _order_public(jrow(row))

    oid, public = new_id(), "OD-" + uuid.uuid4().hex[:8].upper()
    gw_order_id = None
    if S.gateway == "razorpay" and S.razorpay_key_id:
        gw_order_id = _razorpay_create_order(public, amount)

    with tx() as c:
        c.execute(text("INSERT INTO orders (id,public_id,user_id,item,ref_id,"
                       "amount_paise,status,gateway,gateway_order_id,"
                       "idempotency_key,created_at)"
                       " VALUES (:i,:p,:u,:it,:r,:a,'created',:g,:go,:k,:t)"),
                  {"i": oid, "p": public, "u": user_id, "it": item, "r": ref_id,
                   "a": amount, "g": S.gateway, "go": gw_order_id,
                   "k": idempotency_key, "t": now()})
        row = c.execute(text("SELECT * FROM orders WHERE id = :i"), {"i": oid}).fetchone()
    return _order_public(jrow(row))


def _order_public(o: dict) -> dict:
    out = {"orderId": o["public_id"], "item": o["item"],
           "amount": o["amount_paise"] // 100,
           "amountPaise": o["amount_paise"], "status": o["status"],
           "gateway": o.get("gateway")}
    if o.get("gateway_order_id"):
        out["gatewayOrderId"] = o["gateway_order_id"]
        out["keyId"] = S.razorpay_key_id
    elif S.upi_id:
        # fallback for pre-gateway testing only — a bare intent cannot be verified
        out["upiIntentUrl"] = (
            f"upi://pay?pa={S.upi_id}&pn={S.payee_name.replace(' ', '%20')}"
            f"&am={o['amount_paise'] // 100}&cu=INR&tr={o['public_id']}")
    return out


def order_by_public(public_id: str) -> Optional[dict]:
    with engine().connect() as c:
        row = c.execute(text("SELECT * FROM orders WHERE public_id = :p"),
                        {"p": public_id}).fetchone()
    return jrow(row) if row else None


def _razorpay_create_order(receipt: str, amount_paise: int) -> Optional[str]:
    """Create the gateway order that ties a payment back to `receipt`.

    Returning None is not harmless. Without a gateway order the checkout cannot
    carry our order id, the customer falls through to the shared payment button,
    and the resulting capture has nothing in it that identifies which order to
    credit. So a failure here is logged loudly rather than swallowed — it is the
    difference between a payment that reconciles itself and one that needs a
    human.
    """
    import base64
    import urllib.request
    auth = base64.b64encode(
        f"{S.razorpay_key_id}:{S.razorpay_key_secret}".encode()).decode()
    body = json.dumps({"amount": amount_paise, "currency": "INR",
                       "receipt": receipt, "payment_capture": 1}).encode()
    req = urllib.request.Request(
        "https://api.razorpay.com/v1/orders", data=body,
        headers={"Content-Type": "application/json", "Authorization": "Basic " + auth})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.load(resp).get("id")
    except Exception as exc:                                         # noqa: BLE001
        detail = ""
        body_text = getattr(exc, "read", None)
        if callable(body_text):
            try:
                detail = body_text().decode("utf-8", "replace")[:400]
            except Exception:                                        # noqa: BLE001
                detail = ""
        print(f"[billing] RAZORPAY ORDER CREATE FAILED for receipt={receipt} "
              f"amount={amount_paise}: {type(exc).__name__}: {exc} {detail}",
              flush=True)
        return None      # order still exists locally; retry or fall back to UPI


def verify_checkout_signature(*, gateway_order_id: str, payment_id: str,
                              signature: str) -> bool:
    """Verify the success payload Razorpay Checkout hands the browser.

    Razorpay signs ``order_id|payment_id`` with the API key secret. That is the
    same proof strength as the webhook signature, so honouring it is safe — and
    necessary, because the webhook is an asynchronous callback that can be
    delayed, misconfigured or blocked, and until now it was the only path to
    "paid". A charged customer staring at a locked report was the result.
    """
    if not (S.razorpay_key_secret and gateway_order_id and payment_id and signature):
        return False
    expected = hmac.new(S.razorpay_key_secret.encode(),
                        f"{gateway_order_id}|{payment_id}".encode(),
                        hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip())


def order_by_gateway_order_id(gateway_order_id: str) -> Optional[dict]:
    with engine().connect() as c:
        row = c.execute(text("SELECT * FROM orders WHERE gateway_order_id = :g"),
                        {"g": gateway_order_id}).fetchone()
    return jrow(row) if row else None


# ---------------------------------------------------------------------------
# webhooks — the only path that grants access
# ---------------------------------------------------------------------------
def verify_razorpay_signature(raw_body: bytes, signature: str) -> bool:
    if not S.razorpay_webhook_secret:
        return False
    expected = hmac.new(S.razorpay_webhook_secret.encode(), raw_body,
                        hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, (signature or "").strip())


def record_event(order_id: Optional[str], event_type: str, payload: dict,
                 signature_ok: bool) -> None:
    with tx() as c:
        c.execute(text("INSERT INTO payment_events (order_id,gateway,event_type,"
                       "signature_ok,payload,received_at)"
                       " VALUES (:o,:g,:e,:s,:p,:t)"),
                  {"o": order_id, "g": S.gateway, "e": event_type,
                   "s": signature_ok, "p": jdump(payload), "t": now()})


def mark_paid_from_gateway_payment(*, email: str = "", amount_paise: int = 0,
                                   gateway_payment_id: str = "",
                                   receipt: str = "") -> Optional[dict]:
    """Match a Razorpay payment-button capture to a pending local order.

    Payment buttons do not create our gateway orders, so the webhook often has
    no `receipt`. Prefer: explicit receipt → email+amount → recent same amount.
    """
    receipt = (receipt or "").strip()
    if receipt:
        o = order_by_public(receipt)
        if o and o.get("status") in ("created", "pending", "failed") and (
                not amount_paise or amount_paise >= o["amount_paise"]):
            return mark_paid(o["public_id"], gateway_payment_id=gateway_payment_id)

    em = (email or "").strip().lower()
    if "@" in em and amount_paise > 0:
        with engine().connect() as c:
            user = c.execute(text("SELECT id FROM users WHERE lower(email) = :e"),
                             {"e": em}).fetchone()
            if user:
                uid = jrow(user)["id"]
                row = c.execute(text(
                    "SELECT * FROM orders WHERE user_id = :u AND status = 'created'"
                    " AND amount_paise = :a ORDER BY created_at DESC LIMIT 1"),
                                {"u": uid, "a": amount_paise}).fetchone()
                if row:
                    return mark_paid(jrow(row)["public_id"],
                                     gateway_payment_id=gateway_payment_id)

    # No receipt and no email match. We used to guess here: "the only unpaid order
    # of this amount in the last two hours". That hands one customer's payment to
    # whichever stranger happened to have a same-priced order open, so a payer
    # could stay locked while someone else's report unlocked for free. The event
    # is already recorded in payment_events (unmatched); support unlocks the right
    # order from the admin lookup.
    print(f"[billing] UNMATCHED PAYMENT {gateway_payment_id} amount={amount_paise} "
          f"email={em!r} — needs a manual unlock", flush=True)
    return None


def mark_paid(public_id: str, *, gateway_payment_id: str = "") -> dict:
    """Idempotent. Grants the entitlement the order was for."""
    o = order_by_public(public_id)
    if not o:
        raise KeyError("order not found")
    if o["status"] == "refunded":
        # A late or replayed webhook must not resurrect a refunded purchase.
        return {"ok": False, "refunded": True, "item": o["item"]}
    if o["status"] == "paid":
        # Re-run the (idempotent) grants: a paid order whose grant failed
        # half-way, or a legacy order with no report id, heals on retry.
        # (Never for a subscription: that would extend it again on every retry.)
        if o["item"] not in ACCOUNT_WIDE_ITEMS:
            ref = o.get("ref_id") or latest_report_id(o["user_id"], o["item"])
            try:
                _apply_grants(o, o["item"], o["user_id"], ref)
            except Exception:                                         # noqa: BLE001
                pass
        return {"ok": True, "already": True, "item": o["item"]}

    item, uid, ref = o["item"], o["user_id"], o.get("ref_id")
    if not ref and item not in ACCOUNT_WIDE_ITEMS:
        # An order placed without a report id would grant every report of this
        # kind, forever. Bind it to the customer's latest report of that kind.
        ref = latest_report_id(uid, item)

    with tx() as c:
        # Conditional, so a webhook and the browser callback racing each other
        # grant exactly once.
        res = c.execute(text("UPDATE orders SET status='paid', paid_at=:t,"
                             " gateway_payment_id = COALESCE(NULLIF(:gp,''), gateway_payment_id),"
                             " ref_id = COALESCE(ref_id, :r)"
                             " WHERE id = :i AND status IN ('created','pending','failed')"),
                        {"t": now(), "gp": gateway_payment_id, "i": o["id"], "r": ref})
        if not res.rowcount:
            return {"ok": True, "already": True, "item": item}

    _apply_grants(o, item, uid, ref)
    return {"ok": True, "item": item, "userId": uid, "refId": ref}


def _apply_grants(o: dict, item: str, uid: str, ref: Optional[str]) -> None:
    """Write the entitlements a paid order confers. Idempotent."""
    if item == "subscription":
        _extend_subscription(uid)
        grant(uid, "daily", source="subscription", order_id=o["id"], days=30)
        grant(uid, "muhurat", source="subscription", order_id=o["id"], days=30)
        pin_subscribed_daily_reports(uid)
    elif item == "bundle_all":
        # Account-wide (ref_id stays NULL) — the bundle covers every chart the
        # buyer has, not just the one they happened to be looking at. entitled()
        # treats a NULL ref_id as matching any ref, so this is what "everything"
        # has to look like in the table.
        for it in expand(item):
            grant(uid, it, source="order", order_id=o["id"])
        if ref:
            from .db import report_mark_paid
            report_mark_paid(ref)
    else:
        grant(uid, item, ref_id=ref, source="order", order_id=o["id"])
        if ref:
            from .db import report_mark_paid
            report_mark_paid(ref)


def refund(public_id: str) -> None:
    o = order_by_public(public_id)
    if not o:
        raise KeyError("order not found")
    with tx() as c:
        c.execute(text("UPDATE orders SET status='refunded', refunded_at=:t WHERE id=:i"),
                  {"t": now(), "i": o["id"]})
    revoke_order_access(o)


def bind_orphan_order_grants() -> int:
    """One-time/startup repair. Orders placed without a report id left an
    account-wide grant, so one purchase unlocked every report of that kind for
    ever. Bind each such grant to the customer's latest report of that kind.
    Idempotent; never touches bundles, subscriptions, promo or support grants."""
    from sqlalchemy.exc import IntegrityError
    with engine().connect() as c:
        rows = c.execute(text(
            "SELECT e.id AS eid, e.user_id, e.item, o.id AS oid"
            " FROM entitlements e JOIN orders o ON o.id = e.order_id"
            " WHERE e.source = 'order' AND e.ref_id IS NULL AND e.revoked_at IS NULL"
            " AND o.item NOT IN ('bundle_all', 'subscription')")).fetchall()
    fixed = 0
    for r in rows:
        m = r._mapping
        rid = latest_report_id(m["user_id"], m["item"])
        if not rid:
            continue
        try:
            with tx() as c:
                c.execute(text("UPDATE entitlements SET ref_id = :r WHERE id = :e"),
                          {"r": rid, "e": m["eid"]})
                c.execute(text("UPDATE orders SET ref_id = COALESCE(ref_id, :r)"
                               " WHERE id = :o"), {"r": rid, "o": m["oid"]})
            from .db import report_mark_paid
            report_mark_paid(rid)
            fixed += 1
        except IntegrityError:
            # That report already has its own live grant; this one is redundant.
            with tx() as c:
                c.execute(text("UPDATE entitlements SET revoked_at = :t WHERE id = :e"),
                          {"t": now(), "e": m["eid"]})
    return fixed


def revoke_order_access(o: dict) -> int:
    """Take back everything a paid order unlocked: its entitlements (every item
    a bundle expanded into, not the bundle's own name) and the report's paid
    flag, which would otherwise keep the report open on its own."""
    uid, ref = o["user_id"], o.get("ref_id")
    with engine().connect() as c:
        linked = c.execute(text("SELECT count(*) FROM entitlements WHERE order_id = :o"),
                           {"o": o["id"]}).fetchone()[0]
    n = 0
    with tx() as c:
        res = c.execute(text("UPDATE entitlements SET revoked_at = :t"
                             " WHERE order_id = :o AND revoked_at IS NULL"),
                        {"t": now(), "o": o["id"]})
        n += int(res.rowcount or 0)
    if not linked:
        # Older rows carry no order_id; fall back to matching by item and report.
        for it in expand(o["item"]):
            revoke(uid, it, None if o["item"] == "bundle_all" else ref)
    if n and ref and o["item"] not in ("subscription", "bundle_all"):
        # Only when something was actually revoked now, so re-running the same
        # revocation after a restart cannot lock a report that was bought again.
        with tx() as c:
            c.execute(text("UPDATE reports SET paid = :p WHERE id = :i"),
                      {"p": False, "i": ref})
    return n


def _extend_subscription(user_id: str) -> None:
    sub = subscription_of(user_id)
    base = now()
    if sub and sub.get("current_period_end"):
        end = sub["current_period_end"]
        if isinstance(end, str):
            end = datetime.fromisoformat(end)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        base = max(base, end)
    new_end = base + timedelta(days=30)
    with tx() as c:
        if sub:
            c.execute(text("UPDATE subscriptions SET status='active',"
                           " current_period_end=:e WHERE id=:i"),
                      {"e": new_end, "i": sub["id"]})
        else:
            c.execute(text("INSERT INTO subscriptions (id,user_id,plan,status,"
                           "current_period_end,created_at)"
                           " VALUES (:i,:u,'daily_monthly','active',:e,:t)"),
                      {"i": new_id(), "u": user_id, "e": new_end, "t": now()})
    # reset the monthly horary allowance
    with tx() as c:
        c.execute(text("DELETE FROM usage_counters WHERE user_id=:u AND kind='horary'"),
                  {"u": user_id})
