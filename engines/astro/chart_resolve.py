"""
chart_resolve.py - single entry for natal chart facts.

Priority:
  1. --precomputed JSON (PyJHora or session)
  2. birth time + coordinates via workspace PyJHora (pyjhora/src)
  3. AstroSage VedicReport extract

All report lanes should call resolve_precompute() rather than precompute(extract) directly.
"""
from __future__ import annotations

import argparse
from typing import Optional

from astro_precompute import load_precomputed, resolve_precompute

__all__ = ["load_precomputed", "resolve_precompute", "add_chart_source_args"]


def add_chart_source_args(
    ap: argparse.ArgumentParser,
    *,
    precomputed_default: Optional[str] = None,
) -> None:
    """Register --precomputed and PyJHora birth flags on an ArgumentParser."""
    ap.add_argument(
        "--precomputed",
        default=precomputed_default,
        help="Precomputed JSON (PyJHora or session); skips extract parse",
    )
    ap.add_argument(
        "--time",
        default=None,
        help="Birth time HH:MM or HH:MM:SS - compute chart via PyJHora",
    )
    ap.add_argument("--lat", type=float, default=None, help="Birth latitude (decimal degrees)")
    ap.add_argument("--lon", type=float, default=None, help="Birth longitude (decimal degrees)")
    ap.add_argument("--tz", type=float, default=None, help="Timezone offset hours e.g. 5.5")
    ap.add_argument("--place", default="", help="Birth place label (metadata only)")
    ap.add_argument("--ayanamsa", default="LAHIRI", help="PyJHora ayanamsa (default LAHIRI)")
    ap.add_argument("--gender", type=int, choices=[0, 1], default=None, help="0=male 1=female for Chara dasha")


def chart_kwargs_from_args(args) -> dict:
    """Build resolve_precompute keyword args from argparse namespace."""
    return {
        "precomputed_path": getattr(args, "precomputed", None),
        "birth_time": getattr(args, "time", None),
        "latitude": getattr(args, "lat", None),
        "longitude": getattr(args, "lon", None),
        "timezone": getattr(args, "tz", None),
        "place_name": getattr(args, "place", "") or "",
        "ayanamsa": getattr(args, "ayanamsa", "LAHIRI") or "LAHIRI",
        "gender": getattr(args, "gender", None),
    }
