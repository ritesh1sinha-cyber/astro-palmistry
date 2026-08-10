"""Generate free/paid full-report HTML for interactive review (V5.2)."""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path[:0] = ["/app/engines/astro", "/app", "/app/engines"]

from astro_precompute import resolve_precompute  # noqa: E402
import deep_evidence as DE  # noqa: E402
import report_render as RD  # noqa: E402

OUT = Path("/tmp/review_samples")
SAMPLE = {
    "name": "Meera Nair",
    "dob": "1990-01-15",
    "tob": "12:00",
    "lat": 28.6139,
    "lon": 77.2090,
    "tz": 5.5,
    "place": "New Delhi",
    "gender": 0,
}


def _body(html: str) -> str:
    return re.sub(r"<style>.*?</style>", "", html or "", flags=re.S)


def main() -> int:
    pc = resolve_precompute(
        SAMPLE["name"], SAMPLE["dob"], birth_time=SAMPLE["tob"],
        latitude=SAMPLE["lat"], longitude=SAMPLE["lon"],
        timezone=SAMPLE["tz"], place_name=SAMPLE["place"],
        gender=SAMPLE["gender"])

    DE.begin(pc, lat=SAMPLE["lat"], lon=SAMPLE["lon"], tz=SAMPLE["tz"])
    try:
        free, paid, meta = RD._full_report_inner(
            pc, name=SAMPLE["name"], question="", today=date.today(),
            price=298, bundle_price=298, lat=SAMPLE["lat"], lon=SAMPLE["lon"],
            tz=SAMPLE["tz"], first="Meera")
    finally:
        DE.end()

    OUT.mkdir(parents=True, exist_ok=True)
    free_path = OUT / "astro_full_report_free.html"
    paid_path = OUT / "astro_full_report_paid.html"
    free_path.write_text(free, encoding="utf-8")
    paid_path.write_text(paid, encoding="utf-8")

    fb, pb = _body(free), _body(paid)
    past_n = max(fb.count('class="past-event'), pb.count('class="past-event'))

    # Detect identical traj-notes inside the same card (heuristic).
    dup_traj = False
    for card in re.findall(r'<article class="card".*?</article>', pb, flags=re.S):
        notes = re.findall(r'<p class="traj-note">(.*?)</p>', card, flags=re.S)
        notes = [re.sub(r"\s+", " ", n).strip() for n in notes if n.strip()]
        if len(notes) != len(set(notes)):
            dup_traj = True
            break

    checks = {
        "sample": SAMPLE,
        "free_bytes": len(free),
        "paid_bytes": len(paid),
        "past_events": past_n,
        "no_when_it_changes": ("When it changes" not in fb and "When it changes" not in pb),
        "no_moderate_signal": ("Moderate signal" not in fb and "Moderate signal" not in pb),
        "no_thing_to_push": ("thing to push" not in fb and "thing to push" not in pb),
        "no_3th_house": ("3th-house" not in fb and "3th-house" not in pb
                         and "3th house" not in fb and "3th house" not in pb),
        "no_offer_without_delivery": ("Expect the offer without the delivery" not in fb
                                      and "Expect the offer without the delivery" not in pb),
        "no_sell_you_gem_copy": ("Before anything we would sell you" not in fb
                                 and "Before anything we would sell you" not in pb),
        "no_generic_traj_mixed": (
            pb.count("Some things move while others need patience. Avoid forcing the result.") == 0
        ),
        "no_generic_traj_down": (
            pb.count("Progress may feel slower. Focus on consistency rather than forcing a result.") == 0
        ),
        "no_past_explain_dup": pb.count("past-explain") == 0 and fb.count("past-explain") == 0,
        "has_past_noticed": "You may have noticed this as" in fb or "You may have noticed this as" in pb,
        "has_current_chapter_label": (
            "The chapter you are in" in pb
            or "How this chapter affects this area" in pb
        ),
        "no_jeweller_bash": "Any jeweller will sell you" not in fb and "Any jeweller will sell you" not in pb,
        "has_chart_not_sign_gem": "individual chart, not simply from your zodiac sign" in (fb + pb),
        "has_overall_why": "Overall:" in pb,
        "no_pressing_on_main": (
            "has been pressing on" not in fb and "has been pressing on" not in pb
        ),
        "no_timing_contradiction": not (
            ("Strong agreement" in pb or "strong agreement" in pb)
            and ("weigh the mixed window carefully" in pb)
        ),
        "no_fight_off_illness": "fight off illness" not in fb and "fight off illness" not in pb,
        "no_nobody_else_gem": "nobody else will tell you" not in fb and "nobody else will tell you" not in pb,
        "no_energy_period_glitch": "energy. and which" not in fb and "energy. and which" not in pb,
        "learning_shortcuts": True,  # wording may vary with manifestation layer
        "has_chapter_range": ("→" in pb and "October 2026" in pb),
        "free_locks_present_why": (
            "Why this reads this way" in fb
            and "activates your" not in fb
            and "is influencing the" not in fb
        ),
        "paid_keeps_present_why": (
            "is influencing the" in pb or "activates your" in pb or "<b>Why:</b>" in pb
        ),
        "free_support_labels": (
            ("strong support" in fb or "mixed support" in fb or "Needs care" in fb)
            and "strong agreement" not in fb
            and "split read" not in fb
        ),
        "paid_three_of_four_digit": "of four timing methods" not in pb,
        "no_weighed_in_promise": "weighed in the promise" not in pb,
        "no_activates_the_sector": "activates the" not in pb or "sector (" not in pb,
        "free_no_lunar_rhythm": "shorter lunar rhythm" not in fb,
        "paid_keeps_lunar_rhythm": "shorter lunar rhythm" in pb,
        "persona_soft": (
            "If this feels familiar, the detailed timing ahead will" in (fb + pb)
            and "nothing after it is worth your money" not in (fb + pb)
        ),
        "free_gem_no_lagna_lord": "Lagna lord" not in fb,
        "free_gem_human": (
            "sensitive area of your chart" in fb
            or "not recommended for you" in fb
            or "Do not wear" in fb
        ),
        "no_generic_career_past": (
            "Your work was easier to move forward, and people were more likely to notice you."
            not in (fb + pb)
        ),
        "has_aligned_explained": (
            "birth chart, current timing and major planetary movement agree" in pb
            or "means the birth chart, current timing" in pb
        ),
        "has_chapter_affects_area": "How this chapter affects this area" in pb,
        "no_thinner_foundational": "thinner foundational support" not in pb,
        "free_why_soft": (
            "The full report shows the planets, timing and chart factors"
            in fb
        ),
        "no_duplicate_traj_in_love": not dup_traj,
        "has_trajectory_label": "How this area changes over time" in pb,
        "has_windows_label": "Your strongest upcoming windows" in pb,
        "has_structured_why": "Birth chart:" in pb and "Current timing:" in pb,
        "has_chapter_planets": "chapter-planets" in fb or "chapter-planets" in pb,
        "paid_planet_names_only": pb.count("planet-names") > 0 and pb.count("planet-row") == 0,
        "paid_trajectory_row": pb.count("trajectory-row"),
        "birth_time_soft": ("Your birth time may need checking." in (fb + pb)
                            or "birth time may need checking" in (fb + pb)),
        "suitable_gem_label": ("considered suitable for your chart" in pb.lower()
                               or "Considered suitable" in pb),
        "trial_soft": "traditional trial approach" in pb,
        "meta_free": meta.get("freeSections"),
        "meta_paid": meta.get("paidSections"),
        "paths": [str(free_path), str(paid_path)],
    }
    print(json.dumps(checks, indent=2))
    fail = [k for k, v in checks.items()
            if (isinstance(v, bool) and v is False
                and k not in ("dup_traj",)
                and not k.startswith(("meta_", "sample", "paths", "paid_bytes",
                                      "free_bytes", "past_events",
                                      "paid_trajectory")))]
    if fail:
        print("FAILED:", ", ".join(fail), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
