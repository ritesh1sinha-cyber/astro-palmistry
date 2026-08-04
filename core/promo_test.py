#!/usr/bin/env python3
"""Proof that "first 500 free" is a promise we can keep.

Run:  python3 core/promo_test.py

The tests that matter are the last three: the 501st redemption, the concurrent
race for the final slot, and the check that a promo grants the same access a
purchase does. Everything before them is scaffolding for those.

This runs against a throwaway SQLite file so it needs no Postgres. SQLite
serialises writers, which means the concurrency test proves the *guard* is in
the right place (the WHERE clause) rather than proving Postgres' MVCC — but the
statement it exercises is the identical one production runs.
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading

_TMP = tempfile.mkdtemp(prefix="promotest-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/t.db"
os.environ.setdefault("SESSION_SECRET", "test-only")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text                                          # noqa: E402

from core import billing, promo                                      # noqa: E402
from core.db import init_schema, new_id, now, tx                     # noqa: E402
from core.errors import UserError                                    # noqa: E402

PASS, FAIL = [], []


def check(name: str, cond: bool, detail: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" + (f"  — {detail}" if detail and not cond else ""))


def mk_user(n: int) -> str:
    uid = new_id()
    with tx() as c:
        c.execute(text("INSERT INTO users (id,email,name,credits,created_at)"
                       " VALUES (:i,:e,:n,0,:t)"),
                  {"i": uid, "e": f"u{n}-{uid[:6]}@test.local",
                   "n": f"User {n}", "t": now()})
    return uid


# ---------------------------------------------------------------------------
init_schema()
print("\n— normalisation and validation —")

check("lowercase input normalises", promo.normalise(" first500 ") == "FIRST500")
try:
    promo.create_code("bad code!", max_redemptions=5)
    check("malformed code rejected", False, "no error raised")
except ValueError:
    check("malformed code rejected", True)
try:
    promo.create_code("ZEROCAP", max_redemptions=0)
    check("zero cap rejected", False, "no error raised")
except ValueError:
    check("zero cap rejected", True)
try:
    promo.create_code("NOSUCHITEM", item="unicorn_reading", max_redemptions=5)
    check("unknown item rejected", False, "no error raised")
except ValueError:
    check("unknown item rejected", True)

c1 = promo.create_code("FIRST500", max_redemptions=500, note="launch")
c2 = promo.create_code("first500", max_redemptions=999)
check("creation is idempotent by code", c1["id"] == c2["id"])
check("re-creation does not change the cap",
      int(c2["max_redemptions"]) == 500, f"cap={c2['max_redemptions']}")

# ---------------------------------------------------------------------------
print("\n— the bundle actually unlocks things —")

# Not a magic number: adding a bundle item should not fail this, but silently
# expanding to nothing (or to itself) must.
check("bundle_all expands to every bundle item",
      billing.expand("bundle_all") == billing.BUNDLE_ITEMS
      and len(billing.BUNDLE_ITEMS) >= 8,
      f"expanded to {billing.expand('bundle_all')}")
check("bundle_all does not expand to itself",
      "bundle_all" not in billing.expand("bundle_all"))
check("a normal item does not expand", billing.expand("palm_full") == ("palm_full",))
check("bundle covers the flagship report", "full_report" in billing.BUNDLE_ITEMS)
check("bundle covers rectification", "btr" in billing.BUNDLE_ITEMS)
check("every bundle item is a real priced item or a subscription perk",
      all(i in billing.S.prices or i in ("daily",) for i in billing.BUNDLE_ITEMS),
      str([i for i in billing.BUNDLE_ITEMS if i not in billing.S.prices
           and i != "daily"]))

# ---------------------------------------------------------------------------
print("\n— a promo grants exactly what a purchase grants —")

buyer, winner = mk_user(1), mk_user(2)
for it in billing.expand("bundle_all"):
    billing.grant(buyer, it, source="order")
promo.create_code("GRANTTEST", max_redemptions=1)
promo.redeem(winner, "GRANTTEST")

same = all(billing.entitled(buyer, i) == billing.entitled(winner, i)
           for i in billing.BUNDLE_ITEMS)
check("promo access == purchase access", same)
check("promo unlocks the paid report",
      billing.entitled(winner, "full_report"))
check("promo access works for any chart (account-wide)",
      billing.entitled(winner, "full_report", ref_id=new_id()))
check("promo does NOT unlock something outside the bundle",
      not billing.entitled(winner, "subscription"))

with tx() as c:
    src = c.execute(text("SELECT DISTINCT source FROM entitlements"
                         " WHERE user_id = :u"), {"u": winner}).fetchall()
check("entitlement is tagged source='promo'",
      [r[0] for r in src] == ["promo"], str(src))

# ---------------------------------------------------------------------------
print("\n— refusals —")

try:
    promo.redeem(mk_user(3), "NOSUCHCODE")
    check("unknown code refused", False, "no error raised")
except UserError as e:
    check("unknown code refused", "isn't one of ours" in str(e))

try:
    promo.redeem(winner, "GRANTTEST")
    check("same user cannot redeem twice", False, "second redemption allowed")
except UserError as e:
    check("same user cannot redeem twice", "already used" in str(e))

with tx() as c:
    n = c.execute(text("SELECT redeemed_count FROM promo_codes WHERE code='GRANTTEST'")
                  ).scalar()
check("a refused redemption does not consume a slot", int(n) == 1, f"count={n}")

promo.create_code("WITHDRAWN", max_redemptions=10)
promo.deactivate("WITHDRAWN")
try:
    promo.redeem(mk_user(4), "WITHDRAWN")
    check("deactivated code refused", False, "no error raised")
except UserError as e:
    check("deactivated code refused", "withdrawn" in str(e))

from datetime import timedelta                                       # noqa: E402
promo.create_code("EXPIRED", max_redemptions=10,
                  expires_at=now() - timedelta(days=1))
try:
    promo.redeem(mk_user(5), "EXPIRED")
    check("expired code refused", False, "no error raised")
except UserError as e:
    check("expired code refused", "expired" in str(e))

# ---------------------------------------------------------------------------
print("\n— THE CAP: the 501st user is refused —")

promo.create_code("CAP500", max_redemptions=500)
users = [mk_user(100 + i) for i in range(501)]
granted, refused = 0, 0
for u in users:
    try:
        promo.redeem(u, "CAP500")
        granted += 1
    except UserError:
        refused += 1

check("exactly 500 redemptions succeeded", granted == 500, f"granted={granted}")
check("the 501st was refused", refused == 1, f"refused={refused}")

st = promo.status("CAP500")
check("code reports itself exhausted", st["valid"] is False
      and st["reason"] == "exhausted", str(st))
check("remaining is zero, not negative", st["remaining"] == 0, str(st))
check("500 users hold real entitlements",
      sum(1 for u in users if billing.entitled(u, "full_report")) == 500)
check("the 501st user holds nothing",
      not billing.entitled(users[-1], "full_report"))

with tx() as c:
    rows = c.execute(text("SELECT COUNT(*) FROM promo_redemptions r"
                          " JOIN promo_codes p ON p.id = r.code_id"
                          " WHERE p.code = 'CAP500'")).scalar()
check("redemption rows match the counter", int(rows) == 500, f"rows={rows}")

# ---------------------------------------------------------------------------
print("\n— the race for the last slot —")

promo.create_code("RACE", max_redemptions=50)
racers = [mk_user(2000 + i) for i in range(80)]
wins, losses, errors = [], [], []


def run(uid: str) -> None:
    try:
        promo.redeem(uid, "RACE")
        wins.append(uid)
    except UserError:
        losses.append(uid)
    except Exception as e:                                           # noqa: BLE001
        errors.append(repr(e))


threads = [threading.Thread(target=run, args=(u,)) for u in racers]
for t in threads:
    t.start()
for t in threads:
    t.join()

check("no unexpected exceptions under concurrency", not errors,
      "; ".join(errors[:2]))
check("concurrency never over-issues", len(wins) <= 50, f"wins={len(wins)}")
check("all 50 slots were used", len(wins) == 50, f"wins={len(wins)}")
check("every loser got a readable refusal", len(wins) + len(losses) == 80,
      f"{len(wins)}+{len(losses)}")

with tx() as c:
    cnt = c.execute(text("SELECT redeemed_count FROM promo_codes WHERE code='RACE'")
                    ).scalar()
check("counter matches the winners exactly", int(cnt) == len(wins),
      f"counter={cnt} wins={len(wins)}")
check("no drift to reconcile", promo.reconcile("RACE") == [],
      str(promo.reconcile("RACE")))

# ---------------------------------------------------------------------------
print("\n— reconciliation catches drift —")

with tx() as c:
    c.execute(text("UPDATE promo_codes SET redeemed_count = 3 WHERE code='RACE'"))
fixed = promo.reconcile("RACE")
check("drift is detected and repaired",
      fixed and fixed[0]["was"] == 3 and fixed[0]["now"] == 50, str(fixed))

# ---------------------------------------------------------------------------
print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED: " + ", ".join(FAIL))
sys.exit(1 if FAIL else 0)
