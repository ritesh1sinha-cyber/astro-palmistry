#!/usr/bin/env python3
"""Small, dependency-free guards for the customer-facing palm HTML."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "engines", "astro"))
sys.path.insert(0, os.path.join(ROOT, "engines"))

from core import palm_cards as PC  # noqa: E402
from palm_api import confluence as CF  # noqa: E402
from palm_api import conclusive as CC  # noqa: E402
from palm_api import palm_voice as PV  # noqa: E402
from palm_api.life_aspects import build_life_aspects  # noqa: E402
import astro_voice as AV  # noqa: E402

# The hardcoded fallbacks `_make_verdict`/`confluence.py` return when their
# internal `import palm_voice as PV` fails. Only `engines/` is on sys.path
# here (never `engines/palm_api/`) so this file mirrors the container's
# PYTHONPATH exactly (see deploy/Dockerfile.local) — a regression to a bare,
# unqualified `import palm_voice` will resurface these fallbacks and fail
# the checks below instead of silently shipping boilerplate.
GENERIC_FALLBACKS = (
    "your hands show a clear pattern here",
    "reads differently between hands.",
    "is consistent across both hands.",
)


def check(label: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"ok  {label}")


def raw() -> dict:
    features = {
        "quality": {},
        "morphology": {"hand_type": "earth"},
        "lines": {
            "life": {"detected": True, "depth": "deep", "quality": "clear"},
            "head": {"detected": True, "depth": "deep", "quality": "clear"},
            "heart": {"detected": True, "depth": "deep", "quality": "clear"},
            "fate": {"detected": True, "depth": "medium", "quality": "clear"},
        },
        "mounts": {"venus": "prominent"},
    }
    aspect = {
        "key": "health",
        "title": "Health & Vitality",
        "strength": "moderate",
        "summary": "Your energy has a steady base when you protect your rest.",
        "points": [{"text": "Your energy has a steady base when you protect your rest."}],
    }
    hand = {"features": features, "numbered_checklist": [], "overlay_path": "missing.jpg"}
    return {
        "left": hand,
        "right": hand,
        "confluence": {"dominant_hand": "right", "life_aspects": [aspect],
                       "lines": [], "mounts": [], "marks": []},
    }


def main() -> int:
    photos = PC._photos(raw(), "right")
    check("both hand placeholders remain visible", photos.count("palm-img-missing") == 2)
    check("both hand captions remain visible", "Left hand" in photos and "Right hand" in photos)

    free = PC.render(raw(), name="Ritz", age=30, paid=False)
    paid = PC.render(raw(), name="Ritz", age=30, paid=True)
    check("free keeps the two-hand gallery", free.count("<figure>") == 2)
    check("free locks supporting evidence", "evidence locked-inline" in free)
    check("paid unlocks supporting evidence", 'class="evidence-row"' in paid)
    check("paid removes the unlock CTA", 'data-unlock="1"' not in paid)

    # Free-view redesign: every paid section keeps its real title but the body
    # is a blurred placeholder, and the report carries exactly one unlock CTA.
    check("free shows six titled-but-locked sections",
          free.count('class="locked-section"') == 6)
    check("free blurs the placeholder bodies", "lock-blur" in free)
    check("free names the section as locked", "in the full reading" in free)
    check("free has exactly one unlock CTA", free.count('data-unlock="1"') == 1)
    check("free buy block names the upgrade",
          "See the pattern beneath the first reading" in free)
    check("free never carries the line-by-line workings",
          '<details class="workings' not in free)
    check("free never carries the forward timeline",
          '<ol class="timeline">' not in free)
    check("paid has no lock sections", 'class="locked-section"' not in paid)
    check("paid has no placeholder blur", '<div class="lock-blur">' not in paid)

    blocks = {"right": raw()["right"], "left": raw()["left"]}
    aspects = build_life_aspects(
        blocks, "right",
        saraswati_signals={"character": [{
            "text": "Your Capricorn ascendant and Jupiter triplicity lead your career.",
            "method": "Saraswati palmistry",
        }]},
    )
    customer_text = " ".join(
        point.get("text", "") for aspect in aspects for point in aspect.get("points", []))
    check("astro-palm jargon is excluded", "Capricorn" not in customer_text)
    check("each aspect is concise", all(len(a.get("points", [])) <= 2 for a in aspects))

    # `palm_voice` must resolve via `from palm_api import palm_voice`, not a
    # bare `import palm_voice`, or every verdict silently drops to boilerplate.
    mount_verdict = CC._make_verdict(
        "mount", "jupiter", {"level": "prominent"}, None,
        ["You carry natural confidence and a desire to lead."], "")
    check("mount verdict is a real prediction, not the fallback",
          "clear pattern here" not in mount_verdict.lower())
    check("mount verdict carries a Why line", "Why:" in mount_verdict)

    line_verdict = CC._make_verdict("line", "life", {"depth": "deep"}, 34, [], "")
    check("line verdict is a real prediction, not the fallback",
          "clear pattern here" not in line_verdict.lower())

    dom_venus = {"detected": True, "depth": "deep", "quality": "clear"}
    non_venus = {"detected": True, "depth": "thin", "quality": "faint"}
    line_conf = CF._line_confluence("life", dom_venus, non_venus, "right", "left")
    check("confluence line statement is generated", bool(line_conf and line_conf.get("statement")))
    check("confluence line statement is not the bare fallback",
          not any(fb in (line_conf.get("statement") or "").lower() for fb in GENERIC_FALLBACKS))

    mount_conf = CF._mount_confluence(
        {"mars": "prominent"}, {"mars": "flat"}, "right", "left")
    check("confluence mount statement is generated", bool(mount_conf))
    check("confluence mount statement is not the bare fallback",
          not any(fb in (mount_conf[0].get("statement") or "").lower() for fb in GENERIC_FALLBACKS))
    check("confluence mount statement names the trait, not the planet",
          "mars" not in mount_conf[0]["statement"].lower())

    # `polish_html` finalizes every palm report. It must strip jargon without
    # mangling structural headings — a blanket " mount" -> " area" replace
    # once turned the "Mount by mount" section heading into "Mount by area".
    heading = '<h3 class="sec">Mount by mount</h3>'
    check("polish_html leaves structural headings intact",
          PV.polish_html(heading) == heading)

    # `astro_voice.tidy()` runs over every palm sentence too. It must only
    # delete a *dangling* connector word left by a stripped citation/name, not
    # a connector that is legitimately the last word of a real sentence.
    sentence = "It shows more on your hand than you were born with."
    check("tidy() keeps a sentence that legitimately ends on a connector word",
          "born with." in AV.tidy(sentence))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
