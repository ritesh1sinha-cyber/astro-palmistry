"""Contact-form enquiries — list and status updates for admin."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from core.db import tx

VALID_STATUSES = frozenset({"new", "replied", "closed"})


def list_enquiries(*, status: str = "", limit: int = 50) -> dict[str, Any]:
    lim = max(1, min(int(limit or 50), 200))
    st = (status or "").strip().lower()
    where = ""
    params: dict[str, Any] = {"lim": lim}
    if st:
        if st not in VALID_STATUSES:
            raise ValueError(f"unknown status {st!r}")
        where = " WHERE status = :st"
        params["st"] = st

    with tx() as c:
        rows = c.execute(
            text(
                "SELECT id, name, phone, email, message, status, created_at"
                f" FROM enquiries{where}"
                " ORDER BY created_at DESC LIMIT :lim"
            ),
            params,
        ).mappings().all()
        counts = {
            r[0]: int(r[1])
            for r in c.execute(
                text("SELECT status, COUNT(*) FROM enquiries GROUP BY status")
            ).all()
        }

    return {
        "enquiries": [
            {
                "id": str(r["id"]),
                "name": r["name"] or "",
                "phone": r["phone"] or "",
                "email": r["email"] or "",
                "message": r["message"] or "",
                "status": r["status"] or "new",
                "createdAt": str(r["created_at"] or ""),
            }
            for r in rows
        ],
        "counts": {k: counts.get(k, 0) for k in sorted(VALID_STATUSES)},
    }


def set_enquiry_status(enquiry_id: str, status: str) -> dict[str, Any]:
    st = (status or "").strip().lower()
    if st not in VALID_STATUSES:
        raise ValueError(f"unknown status {st!r}")
    with tx() as c:
        n = c.execute(
            text("UPDATE enquiries SET status = :st WHERE id = :id"),
            {"id": enquiry_id, "st": st},
        ).rowcount
        if not n:
            raise LookupError("no such enquiry")
        row = c.execute(
            text(
                "SELECT id, name, phone, email, message, status, created_at"
                " FROM enquiries WHERE id = :id"
            ),
            {"id": enquiry_id},
        ).mappings().first()
    return {
        "id": str(row["id"]),
        "name": row["name"] or "",
        "phone": row["phone"] or "",
        "email": row["email"] or "",
        "message": row["message"] or "",
        "status": row["status"] or "new",
        "createdAt": str(row["created_at"] or ""),
    }
