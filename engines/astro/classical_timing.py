#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Horizon buckets for the Classical Vedic Report.

The rest of the engine scans a flat five years and ranks windows by score. A
traditional report answers a different question: what happens in the next six
months, the next year, and the next two to three years. This module reprojects
the running dasha sequence and the confluence windows onto those three
horizons so each one can be written up on its own.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

__all__ = ["HORIZONS", "horizon_buckets", "period_rows", "ruling_lords"]

#: (key, customer heading, days from today the bucket opens, days it closes)
HORIZONS: tuple[tuple[str, str, int, int], ...] = (
    ("next_6_months", "Next 6 Months", 0, 183),
    ("next_12_months", "Next 12 Months", 183, 365),
    ("next_2_3_years", "Next 2-3 Years", 365, 1095),
)

_PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")


def _as_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "")[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _overlaps(row_start: date | None, row_end: date | None,
              win_start: date, win_end: date) -> bool:
    if row_start is None:
        return False
    end = row_end or row_start
    return row_start < win_end and end >= win_start


def period_rows(pc: dict, start: date, end: date) -> list[dict]:
    """Dasha periods touching [start, end), finest granularity available.

    Antardashas are used inside the running mahadasha because the precompute
    only expands the current one. Beyond it, the mahadasha itself is the finest
    period the chart data supports, and is labelled as such.
    """
    vim = (pc or {}).get("vimshottari") or {}
    current_md = vim.get("current_md") or {}
    md_lord = str(current_md.get("md_lord") or "")
    rows: list[dict] = []

    for ad in vim.get("current_md_antardashas") or []:
        ad_start, ad_end = _as_date(ad.get("start")), _as_date(ad.get("end"))
        if not _overlaps(ad_start, ad_end, start, end):
            continue
        ad_lord = str(ad.get("ad_lord") or "")
        rows.append({
            "kind": "antardasha",
            "label": f"{md_lord}-{ad_lord}",
            "md_lord": md_lord,
            "lord": ad_lord,
            "start": ad_start,
            "end": ad_end,
        })

    current_start = _as_date(current_md.get("start"))
    for md in vim.get("sequence") or []:
        md_start, md_end = _as_date(md.get("start")), _as_date(md.get("end"))
        if md_start is not None and md_start == current_start:
            continue
        if not _overlaps(md_start, md_end, start, end):
            continue
        lord = str(md.get("md_lord") or "")
        rows.append({
            "kind": "mahadasha",
            "label": f"{lord} mahadasha",
            "md_lord": lord,
            "lord": lord,
            "start": md_start,
            "end": md_end,
        })

    rows.sort(key=lambda r: r["start"] or date.max)
    return rows


def _window_rows(pc: dict, *, today: date, years: int) -> list[dict]:
    """Every area's windows over the horizon, scanned once.

    `report_timing.best_windows` is deliberately not used here: it narrows to a
    handful of headline windows across the whole chart, which leaves a
    three-year horizon with one or two entries. A traditional report needs
    coverage per life area, so each area is scanned directly over one shared
    transit pass.
    """
    try:
        import report_cards as RC
        import report_timing as RT
    except Exception:  # noqa: BLE001
        return []

    out: list[dict] = []
    try:
        segments = RT.transit_segments(pc, start=today, years=years)
        for area in RC.AREAS:
            rows = RT.windows_for_area(pc, area.key, area.house, start=today,
                                       years=years, segments=segments)
            for row in rows:
                if not (row.get("aligned") or row.get("opportunity")):
                    continue
                start = _as_date(row.get("start"))
                if start is None:
                    continue
                out.append({
                    "area": area.key,
                    "label": area.label,
                    "start": start,
                    "end": _as_date(row.get("end")),
                    "planet": row.get("planet", ""),
                    "score": float(row.get("score") or 0.0),
                    "aligned": bool(row.get("aligned")),
                })
    except Exception as exc:  # noqa: BLE001
        print(f"[classical_timing] windows failed: {exc}", flush=True)
        return out
    return out


def horizon_buckets(pc: dict, *, today: date | None = None,
                    windows_per_bucket: int = 5) -> list[dict]:
    """Return one entry per horizon, each with its periods and its windows."""
    today = today or date.today()
    windows = _window_rows(pc, today=today, years=3)

    buckets: list[dict] = []
    for key, label, day_from, day_to in HORIZONS:
        start = today + timedelta(days=day_from)
        end = today + timedelta(days=day_to)
        in_range = [w for w in windows if start <= w["start"] < end]
        in_range.sort(key=lambda w: (-w["score"], w["start"]))

        # One window per life area keeps the bucket readable and stops a single
        # busy area from filling the whole horizon.
        picked: list[dict] = []
        seen: set[str] = set()
        for window in in_range:
            if window["area"] in seen:
                continue
            picked.append(window)
            seen.add(window["area"])
            if len(picked) >= windows_per_bucket:
                break
        picked.sort(key=lambda w: w["start"])

        buckets.append({
            "key": key,
            "label": label,
            "start": start,
            "end": end,
            "periods": period_rows(pc, start, end),
            "windows": picked,
        })
    return buckets


def ruling_lords(bucket: dict) -> list[str]:
    """Planets that actually rule time inside a bucket, strongest first."""
    seen: list[str] = []
    for row in bucket.get("periods") or []:
        for lord in (row.get("lord"), row.get("md_lord")):
            if lord in _PLANETS and lord not in seen:
                seen.append(lord)
    return seen
