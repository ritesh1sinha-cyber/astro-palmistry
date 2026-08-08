#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bridge to the existing Vedic-chart engine in D:\\projct\\astro-code.

Given birth details (date / time / place), this geocodes the place and runs
PyJHora + Swiss Ephemeris to produce a full natal "precompute" (pc) dict that
the chart-driven report lanes (client_report_html, anchor engine) consume.

Returns None (never raises) if astro-code or its ephemeris is unavailable, so
the palm-only report keeps working as a fallback.
"""
from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

# Location of the astro-code chart engine. Defaults to this file's own folder
# (the bridge now lives inside astro-code), overridable via env for other layouts.
ASTRO_CODE_DIR = Path(os.environ.get("ASTRO_CODE_DIR", "") or Path(__file__).resolve().parent)


def _ensure_on_path() -> bool:
    if not ASTRO_CODE_DIR.is_dir():
        return False
    p = str(ASTRO_CODE_DIR)
    if p not in sys.path:
        sys.path.insert(0, p)
    pyjhora_src = ASTRO_CODE_DIR / "pyjhora" / "src"
    if pyjhora_src.is_dir() and str(pyjhora_src) not in sys.path:
        sys.path.insert(0, str(pyjhora_src))
        os.environ.setdefault("PYJHORA_SRC", str(pyjhora_src))
    return True


@lru_cache(maxsize=16)
def compute_chart(
    client_name: str,
    dob: str,
    birth_time: str,
    place: str = "",
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    timezone: Optional[float] = None,
) -> Optional[dict[str, Any]]:
    """
    Compute a natal precompute dict for the given birth details.

    dob: "YYYY-MM-DD", birth_time: "HH:MM" or "HH:MM:SS".
    Provide either a resolvable `place` (e.g. "New Delhi, India") or explicit
    lat/lon/timezone. Returns the pc dict, or None on any failure.
    """
    if not _ensure_on_path():
        return None
    try:
        from birth_place_resolve import (
            resolve_birth_place,
            normalize_birth_time,
            normalize_dob,
        )
        from astro_precompute import resolve_precompute
    except Exception as exc:  # noqa: BLE001
        print(f"[astro_chart_bridge] import failed: {exc}")
        return None

    try:
        if latitude is None or longitude is None or timezone is None:
            geo = resolve_birth_place(place)
            latitude = geo["latitude"]
            longitude = geo["longitude"]
            timezone = geo["timezone"]
            place = geo.get("place", place)

        pc = resolve_precompute(
            client_name=client_name,
            dob=normalize_dob(dob),
            birth_time=normalize_birth_time(birth_time),
            latitude=float(latitude),
            longitude=float(longitude),
            timezone=float(timezone),
            place_name=place,
        )
        return pc
    except Exception as exc:  # noqa: BLE001
        print(f"[astro_chart_bridge] chart computation failed: {exc}")
        return None


# Generic sample birth details for CLI smoke tests.
SAMPLE_BIRTH = {
    "client_name": "Sample",
    "dob": "1990-01-15",
    "birth_time": "12:00",
    "place": "New Delhi, India",
}


if __name__ == "__main__":
    pc = compute_chart(**SAMPLE_BIRTH)
    if not pc:
        print("FAILED to compute chart (astro-code or ephemeris unavailable)")
        raise SystemExit(1)
    meta = pc.get("meta", {})
    print(f"Lagna: {meta.get('lagna_sign')} (lord {meta.get('lagna_lord')})")
    pl = pc.get("planets", {})
    for name in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"):
        d = pl.get(name) or pl.get(name[:4]) or {}
        print(f"  {name:8s} {d.get('sign','?'):12s} house {d.get('house','?')!s:>3} {d.get('dignity','?')}")
    vim = pc.get("vimshottari", {})
    cmd = vim.get("current_md", {})
    print(f"Current MD: {cmd.get('md_lord')} ({cmd.get('start')} -> {cmd.get('end')})")
    print(f"Pillar lagna-lord dignity: {pc.get('pillar', {}).get('lagna_lord_dignity')}")
