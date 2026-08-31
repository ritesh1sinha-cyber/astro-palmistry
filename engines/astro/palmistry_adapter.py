"""Adapter from the palm pipeline contract to consultation facts."""
from __future__ import annotations

from typing import Any


def build_palm_consultation_data(
    raw: dict[str, Any], *, name: str = "Native", gender: str = "unknown",
    lang: str = "en",
) -> dict[str, Any]:
    """Build one quality-gated consultation payload from pipeline output."""
    try:
        # Package-stable imports — works both when engines/astro is on PYTHONPATH
        # and when run as `python -m engines.astro...`
        try:
            from engines.astro.palmistry_consultation_reading import generate_palm_consultation_sections
            from engines.astro.reading_palms_analysis import analyze_palm
        except ImportError:
            from palmistry_consultation_reading import generate_palm_consultation_sections
            from reading_palms_analysis import analyze_palm

        conf = raw.get("confluence") or {}
        dominant = str(conf.get("dominant_hand") or raw.get("active_hand") or "right")
        dom = raw.get(dominant) if isinstance(raw.get(dominant), dict) else {}
        features = dom.get("features") if isinstance(dom, dict) else {}
        features = features if isinstance(features, dict) else {}
        left = raw.get("left") if isinstance(raw.get("left"), dict) else {}
        left_features = left.get("features") if isinstance(left, dict) else {}
        analysis = analyze_palm(features, name=name, gender=gender, hand=dominant)
        analysis["cv_raw_features"] = features
        analysis["cv_raw_features_left"] = (
            left_features if isinstance(left_features, dict) else {}
        )
        analysis.setdefault("meta", {}).update({
            "client_name": name,
            "gender": gender,
        })
        return generate_palm_consultation_sections(
            analysis, client_name=name, lang=lang)
    except Exception as exc:  # noqa: BLE001
        print(f"[palmistry_adapter] consultation unavailable: {exc}", flush=True)
        return {}
