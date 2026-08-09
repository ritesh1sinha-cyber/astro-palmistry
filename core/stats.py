"""Global report-generation counters and site analytics — admin only.

Increments once each time a free (or paid) report is successfully stored,
i.e. when the user clicked Generate and the job finished. Not tied to
individual users — this is site-wide popularity by section.

Also tracks paid orders (money that cleared) and coarse page views for
capacity planning.
"""
from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import text

from .db import now, tx

# Job kinds that map to a customer-facing tab / section.
TRACKED_KINDS: frozenset[str] = frozenset({
    "palm",
    "full_report",
    "horary",
    "user_question",
    "numerology",
    "daily",
    "kundali_match",
    "muhurat",
    "btr",
})

KIND_LABELS: dict[str, str] = {
    "palm": "Palm reading",
    "full_report": "Full report",
    "horary": "Horary",
    "user_question": "Ask your chart",
    "numerology": "Numerology",
    "daily": "Daily reading",
    "kundali_match": "Kundali matching",
    "muhurat": "Muhurat",
    "btr": "Birth time rectification",
}

# Order.item values → admin display (paid unlocks / subscriptions).
PAID_ITEM_LABELS: dict[str, str] = {
    "palm_full": "Palm reading",
    "full_report": "Full report",
    "horary": "Horary",
    "user_question": "Ask your chart",
    "numerology_full": "Numerology",
    "kundali_match": "Kundali matching",
    "muhurat": "Muhurat",
    "btr": "Birth time rectification",
    "subscription": "Daily subscription",
    "bundle_all": "Bundle (all)",
    "future_event": "Future / timing",
}

# SPA routes we accept for page-view counters (reject junk paths).
TRACKED_PATHS: frozenset[str] = frozenset({
    "home", "read", "astro", "soon", "contact", "reports", "analysis",
    "astro:report", "astro:horary", "astro:question", "astro:daily",
    "astro:numero", "astro:match", "astro:muhurat", "astro:btr",
})

PATH_LABELS: dict[str, str] = {
    "home": "Home",
    "read": "Palm reading",
    "astro": "Astrology (hub)",
    "soon": "Roadmap",
    "contact": "Contact",
    "reports": "My reports",
    "analysis": "Admin analysis",
    "astro:report": "Astro · Full report",
    "astro:horary": "Astro · Horary",
    "astro:question": "Astro · Ask your chart",
    "astro:daily": "Astro · Daily",
    "astro:numero": "Astro · Numerology",
    "astro:match": "Astro · Kundali match",
    "astro:muhurat": "Astro · Muhurat",
    "astro:btr": "Astro · BTR",
}


def increment_report_generation(kind: str) -> None:
    """Bump the global counter for this report kind (no-op if unknown)."""
    k = (kind or "").strip()
    if k not in TRACKED_KINDS:
        return
    t = now()
    with tx() as c:
        row = c.execute(
            text("SELECT count FROM report_generation_stats WHERE kind = :k"),
            {"k": k},
        ).fetchone()
        if row:
            c.execute(
                text("UPDATE report_generation_stats SET count = count + 1, "
                     "updated_at = :t WHERE kind = :k"),
                {"k": k, "t": t},
            )
        else:
            c.execute(
                text("INSERT INTO report_generation_stats (kind, count, updated_at) "
                     "VALUES (:k, 1, :t)"),
                {"k": k, "t": t},
            )


def get_report_generation_counts() -> Dict[str, int]:
    """Return {kind: count} for every tracked section (missing → 0)."""
    out = {k: 0 for k in TRACKED_KINDS}
    with tx() as c:
        rows = c.execute(text("SELECT kind, count FROM report_generation_stats")).fetchall()
    for row in rows:
        k = row[0] if not hasattr(row, "_mapping") else row._mapping.get("kind")
        n = row[1] if not hasattr(row, "_mapping") else row._mapping.get("count")
        if k in out:
            out[k] = int(n or 0)
    return out


def get_paid_order_counts() -> Dict[str, Any]:
    """Successful paid orders grouped by item, plus revenue totals."""
    counts: Dict[str, int] = {k: 0 for k in PAID_ITEM_LABELS}
    revenue_paise: Dict[str, int] = {k: 0 for k in PAID_ITEM_LABELS}
    with tx() as c:
        rows = c.execute(text(
            "SELECT item, COUNT(*) AS n, COALESCE(SUM(amount_paise), 0) AS paise "
            "FROM orders WHERE status = 'paid' GROUP BY item"
        )).fetchall()
    for row in rows:
        m = row._mapping if hasattr(row, "_mapping") else None
        item = (m.get("item") if m else row[0]) or ""
        n = int((m.get("n") if m else row[1]) or 0)
        paise = int((m.get("paise") if m else row[2]) or 0)
        if item in counts:
            counts[item] = n
            revenue_paise[item] = paise
        else:
            counts[item] = counts.get(item, 0) + n
            revenue_paise[item] = revenue_paise.get(item, 0) + paise
    total_orders = sum(counts.values())
    total_paise = sum(revenue_paise.values())
    return {
        "counts": counts,
        "revenuePaise": revenue_paise,
        "totalOrders": total_orders,
        "totalPaise": total_paise,
    }


def increment_page_view(path: str) -> bool:
    """Bump a coarse page-view counter. Returns False if path is not tracked."""
    p = (path or "").strip().lower()
    if p not in TRACKED_PATHS:
        return False
    t = now()
    with tx() as c:
        row = c.execute(
            text("SELECT count FROM page_view_stats WHERE path = :p"),
            {"p": p},
        ).fetchone()
        if row:
            c.execute(
                text("UPDATE page_view_stats SET count = count + 1, "
                     "updated_at = :t WHERE path = :p"),
                {"p": p, "t": t},
            )
        else:
            c.execute(
                text("INSERT INTO page_view_stats (path, count, updated_at) "
                     "VALUES (:p, 1, :t)"),
                {"p": p, "t": t},
            )
    return True


def get_page_view_counts() -> Dict[str, Any]:
    """Return per-path counts and a grand total."""
    counts = {p: 0 for p in TRACKED_PATHS}
    with tx() as c:
        rows = c.execute(
            text("SELECT path, count FROM page_view_stats")
        ).fetchall()
    for row in rows:
        p = row[0] if not hasattr(row, "_mapping") else row._mapping.get("path")
        n = row[1] if not hasattr(row, "_mapping") else row._mapping.get("count")
        if p in counts:
            counts[p] = int(n or 0)
    return {"counts": counts, "total": sum(counts.values())}


def admin_analysis_summary() -> Dict[str, Any]:
    """Single payload for the admin Analysis page."""
    free = get_report_generation_counts()
    paid = get_paid_order_counts()
    views = get_page_view_counts()

    free_rows: List[dict] = []
    for kind in TRACKED_KINDS:
        free_rows.append({
            "key": kind,
            "label": KIND_LABELS.get(kind, kind),
            "count": free.get(kind, 0),
        })
    free_rows.sort(key=lambda r: (-r["count"], r["label"]))

    paid_rows: List[dict] = []
    for item, n in (paid.get("counts") or {}).items():
        paid_rows.append({
            "key": item,
            "label": PAID_ITEM_LABELS.get(item, item.replace("_", " ").title()),
            "count": n,
            "revenuePaise": (paid.get("revenuePaise") or {}).get(item, 0),
        })
    paid_rows.sort(key=lambda r: (-r["count"], r["label"]))

    view_rows: List[dict] = []
    for path, n in (views.get("counts") or {}).items():
        view_rows.append({
            "key": path,
            "label": PATH_LABELS.get(path, path),
            "count": n,
        })
    view_rows.sort(key=lambda r: (-r["count"], r["label"]))

    return {
        "freeReports": {
            "total": sum(free.values()),
            "bySection": free_rows,
        },
        "paidOrders": {
            "totalOrders": paid.get("totalOrders", 0),
            "totalPaise": paid.get("totalPaise", 0),
            "bySection": paid_rows,
        },
        "pageViews": {
            "total": views.get("total", 0),
            "byPath": view_rows,
        },
    }
