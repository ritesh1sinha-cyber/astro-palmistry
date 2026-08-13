"""The palmist voice: named features, book readings, and an answer for each problem."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT, ROOT / "engines", ROOT / "engines" / "astro"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from palm_api import palmist_voice as PV  # noqa: E402


def _features(**over):
    feats = {
        "morphology": {
            "hand_type": "air",
            "index_vs_ring": "ring_longer",
            "thumb": {"length": "short", "will_vs_logic": "will_dominant",
                      "opening": "wide"},
        },
        "lines": {
            "life": {"detected": True, "depth": "deep", "sweep": "wide",
                     "quality": "clear", "shape": "curved"},
            "head": {"detected": True, "depth": "deep", "length": "short",
                     "direction": "straight", "start_relation": "merged",
                     "quality": "clear", "shape": "straight"},
            "heart": {"detected": True, "depth": "deep", "start_zone": "saturn",
                      "length": "short", "quality": "clear"},
            "fate": {"detected": True, "depth": "deep", "start_zone": "mid_palm",
                     "quality": "clear", "shape": "wavy"},
        },
        "minor_lines": {
            "sun": {"detected": True, "strength": "strong"},
            "girdle_of_venus": {"detected": False},
        },
        "mounts": {"jupiter": "moderate", "mars": "prominent", "venus": "flat"},
        "special_marks": [{
            "type": "trident", "title": "Trident (Trishul) sign", "zone": "jupiter",
            "meaning": "On your Jupiter mount you have a trident.",
        }],
        "quality": {"grade": "good", "special_marks_allowed": True},
    }
    feats.update(over)
    return feats


def test_every_reading_names_the_feature_and_says_what_it_means():
    reading = PV.read_hand({"features": _features()}, hand="right")
    assert reading.lines, "the major lines must produce readings"
    for item in reading.all():
        assert item.feature.strip(), f"{item.key} has no feature name"
        assert item.sign.strip(), f"{item.key} does not say what was seen"
        assert item.means.strip(), f"{item.key} does not say what it means"


def test_a_problem_sign_always_carries_an_answer():
    """Naming a difficulty without a step is the thing the reader resents."""
    reading = PV.read_hand({"features": _features()}, hand="right")
    problems = reading.problems()
    assert problems, "this hand carries difficult signs"
    missing = [p.key for p in problems if not p.remedy.strip()]
    assert not missing, f"problem signs with no remedy: {missing}"


def test_the_mounts_keep_their_own_names():
    reading = PV.read_hand({"features": _features()}, hand="right")
    named = " ".join(r.feature for r in reading.mounts)
    assert "Mount of Mars" in named
    assert "Mount of Venus" in named
    # …and still say where the mount is, for a reader who has never heard of it.
    where = " ".join(r.sign for r in reading.mounts)
    assert "ball of your thumb" in where


def test_a_line_does_not_state_the_same_verdict_twice():
    """Short and straight both read as a practical mind; only one should show."""
    reading = PV.read_hand({"features": _features()}, hand="right")
    head = [r.key for r in reading.lines if r.key.startswith("head_")]
    assert "head_direction_straight" in head
    assert "head_length_short" not in head
    assert len(head) <= PV._MAX_PER_LINE


def test_marks_are_gated_by_this_hand_not_the_other_one():
    good = {"features": _features()}
    blurred = {"features": _features(
        quality={"grade": "fair", "special_marks_allowed": False})}
    assert PV.read_hand(good, hand="left").marks, "a clear photo may report marks"
    assert not PV.read_hand(blurred, hand="right").marks, \
        "a fair photo must not report fine marks"


def test_an_absent_fate_line_is_read_rather_than_skipped():
    feats = _features()
    feats["lines"]["fate"] = {"detected": False}
    reading = PV.read_hand({"features": feats}, hand="right")
    absent = [r for r in reading.lines if r.key == "fate_absent"]
    assert absent, "a missing fate line is itself a reading"
    assert absent[0].remedy, "and it comes with something to do about it"
    # An absent line is a common finding and reads as alarming unless the
    # reading says outright that it is not a verdict against them.
    assert "not read an absent fate line as failure" in absent[0].means


def test_dated_events_come_back_in_age_order():
    hand = {"numbered_checklist": [
        {"kind": "line", "key": "fate", "title": "Your fate line",
         "timing": {"estimated_age": 44, "age_range": [40, 48]},
         "conclusive": {"conclusion": "The work changes shape."}},
        {"kind": "line", "key": "life", "title": "Your life line",
         "timing": {"estimated_age": 31, "age_range": [27, 36]},
         "conclusive": {"conclusion": "Vitality turns a corner."}},
        {"kind": "mount", "key": "jupiter", "title": "Jupiter"},
    ]}
    dated = PV.dated_events(hand, hand="right")
    assert [d.age for d in dated] == [31, 44]
    assert dated[0].age_range == (27, 36)


def test_the_palm_scrubber_leaves_the_book_vocabulary_alone():
    from palm_api import palm_voice as V

    text = ("A trident on the Mount of Jupiter, with a Girdle of Venus above "
            "the heart line.")
    assert V.polish_html(f"<p>{text}</p>") == f"<p>{text}</p>"
    # The astrology lane still has no business in a palm reading.
    assert "ascendant" not in V.polish_prose("your ascendant is strong").lower()
