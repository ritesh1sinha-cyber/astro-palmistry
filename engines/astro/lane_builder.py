"""Generate the twelve specialist reports the confluence engine reads.

The confluence report scores its own confidence partly on how many specialist
sub-reports it can find on disk (`LANE_FILES` in vedic_confluence_report). The
product never generated them, so every flagship report ran with **0 of 12**,
had its cross-method confidence capped at MODERATE, and opened with a red
banner telling the customer so:

    Partial pass: 0/12 specialist sub-reports were on disk when this
    confluence ran. Cross-method confidence is capped at MODERATE until the
    full lane set is generated for Sample_8f6a07

Three problems in one sentence: the customer is shown internal status, an
internal slug, and — worst — it is true. The most expensive product in the
catalogue was running at reduced strength on every single order.

This builds the lane set first. Each lane is independent: one that raises is
logged and skipped rather than taking the report down with it, because a
confluence over eleven lanes is worth far more than an error page.
"""

from __future__ import annotations

import inspect
import time
import traceback
from datetime import date, datetime
from pathlib import Path
from typing import Callable

#: (lane name, module, function, output filename prefix)
LANES: list[tuple[str, str, str, str]] = [
    ("Pillar",       "vedic_pillar_report",       "generate_pillar_html",       "Vedic_Pillar"),
    ("Vimshottari",  "vedic_vimshottari_report",  "generate_vimshottari_html",  "Vedic_Vimshottari"),
    ("BNN",          "vedic_bnn_report",          "generate_bnn_html",          "Vedic_BNN"),
    ("KP",           "vedic_kp_report",           "generate_kp_html",           "Vedic_KP"),
    ("Jaimini",      "vedic_jaimini_report",      "generate_jaimini_html",      "Vedic_Jaimini"),
    ("Yogini",       "vedic_yogini_report",       "generate_yogini_html",       "Vedic_Yogini"),
    ("Ashtakavarga", "vedic_ashtakavarga_report", "generate_ashtakavarga_html", "Vedic_Ashtakavarga"),
    ("RTVD",         "vedic_rtvd_report",         "generate_rtvd_html",         "Vedic_RTVD"),
    ("Longevity",    "vedic_longevity_report",    "generate_longevity_html",    "Vedic_Longevity"),
    ("BlindChart",   "vedic_blindchart_report",   "generate_blindchart_html",   "Vedic_BlindChart"),
    ("Bhardwaj",     "vedic_bhardwaj_report",     "generate_bhardwaj_html",     "Vedic_Bhardwaj"),
]


def _write(out_dir: Path, prefix: str, slug: str, html: str) -> Path:
    """Filename must match LANE_FILES' glob: Vedic_KP_{slug}_*.html"""
    path = out_dir / f"{prefix}_{slug}_{date.today():%Y%m%d}.html"
    path.write_text(html or "", encoding="utf-8")
    return path


def build_lanes(out_dir: str | Path, *, slug: str, client_name: str, dob: str,
                birth_time: str, latitude: float, longitude: float,
                timezone: float, place_name: str, gender: int = 0,
                precomputed_path: str = "", budget_seconds: float = 240.0,
                log: Callable[[str], None] = print) -> dict:
    """Write every lane it can inside the time budget. Never raises."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Bhardwaj clusters its book corpus with embeddings; without the stand-in
    # it is the one lane that dies on the default image.
    try:
        import semantic_fallback
        semantic_fallback.install()
    except Exception:
        pass

    # The lanes do not share one signature — Ashtakavarga has no `tob`/`place`,
    # some predate `gender`. Rather than maintain a per-lane argument table
    # that rots the next time a lane changes, ask each function what it takes.
    common = dict(tob=birth_time, place=place_name, birth_time=birth_time,
                  place_name=place_name,
                  latitude=latitude, longitude=longitude, timezone=timezone,
                  precomputed_path=precomputed_path or None, gender=gender)

    built, failed, skipped = [], {}, []
    started = time.time()

    for name, module_name, func_name, prefix in LANES:
        if time.time() - started > budget_seconds:
            # A slow lane must not blow the customer's total wait. Better a
            # confluence over the lanes that finished than a timeout.
            skipped.append(name)
            continue
        t0 = time.time()
        try:
            module = __import__(module_name)
            func = getattr(module, func_name)
            try:
                accepted = set(inspect.signature(func).parameters)
                kwargs = {k: v for k, v in common.items() if k in accepted}
            except (TypeError, ValueError):
                kwargs = dict(common)
            html = func(client_name, dob, **kwargs)
            if isinstance(html, tuple):
                html = html[0]
            if isinstance(html, (str, Path)) and str(html).endswith(".html") \
                    and Path(str(html)).is_file():
                html = Path(str(html)).read_text(encoding="utf-8", errors="ignore")
            if not html or len(str(html)) < 400:
                raise ValueError(f"empty output ({len(str(html or ''))} bytes)")
            _write(out, prefix, slug, str(html))
            built.append(name)
            log(f"[lanes] {name} ok ({time.time() - t0:.1f}s)")
        except Exception as exc:
            failed[name] = f"{type(exc).__name__}: {exc}"
            log(f"[lanes] {name} FAILED after {time.time() - t0:.1f}s — "
                f"{type(exc).__name__}: {exc}")
            log(traceback.format_exc(limit=3))

    # numerology has its own signature
    if time.time() - started <= budget_seconds:
        try:
            from numerology_report import generate_numerology_html
            d = dob if isinstance(dob, date) else datetime.strptime(
                str(dob)[:10], "%Y-%m-%d").date()
            html = generate_numerology_html(
                client_name, d, sex="Male" if not gender else "Female")
            if isinstance(html, tuple):
                html = html[0]
            _write(out, "Numerology", slug, str(html))
            built.append("Numerology")
            log("[lanes] Numerology ok")
        except Exception as exc:
            failed["Numerology"] = f"{type(exc).__name__}: {exc}"
            log(f"[lanes] Numerology FAILED — {type(exc).__name__}: {exc}")

    log(f"[lanes] {len(built)}/{len(LANES) + 1} built in "
        f"{time.time() - started:.1f}s"
        + (f", failed: {sorted(failed)}" if failed else "")
        + (f", skipped for time: {skipped}" if skipped else ""))
    return {"built": built, "failed": failed, "skipped": skipped,
            "seconds": round(time.time() - started, 1), "dir": str(out)}
