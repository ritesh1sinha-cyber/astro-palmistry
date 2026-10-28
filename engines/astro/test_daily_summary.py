"""The crisp daily card: confluence votes -> score, tiles, short Do/Don't lines."""
from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import daily_summary as DS  # noqa: E402


def _reading(**over):
    r = {
        "client": "Asha", "tone": "mixed-positive",
        "opening": ("Asha, Tuesday opens with a quietly promising feel. The Moon in Aries "
                    "stirs creativity, romance, and children. Overall: workable."),
        "tarabala": {"name": "Parama Mitra", "tone": "auspicious"},
        "chandrabal": {"name": "Sampat Rasi", "tone": "auspicious",
                       "do_note": "Voice financial boundaries kindly.",
                       "note": "Avoid impulse spending to soothe mood."},
        "gochar": {"moon": {"auspicious": False, "inauspicious": True},
                   "sun": {"auspicious": True, "inauspicious": False},
                   "mercury": {"auspicious": True, "inauspicious": False}},
        "ashtakavarga": {"moon": {"sav": 30, "bav": 4}, "sun": {"sav": 33, "bav": 6}},
        "moon_transit": {"sign": "Aries", "house_from_moon": 5, "house_from_lagna": 10},
        "moonology": {"sign_summary": "You may notice that emotions run hot and fast; you want movement."},
        "vedic_confluence": {
            "verdict_plain": "Overall: a workable day for steady progress - move with your timing, not against it.",
            "work_hint": "Mars moves in fits and starts - one focused block beats multitasking. More text.",
            "personal_hint": ("Relationships: Sun needs patience - do not force outcomes. "
                              "Creativity and children: Mercury helps."),
        },
        "dos": [
            {"text": "Asha, lean into red today - Tuesday answers to Mars.", "source": "rules40/41 weekday Mars"},
            {"text": "Parama Mitra is a bright window - schedule the pitch you've postponed.",
             "source": "Tarabala/Parama Mitra"},
            {"text": "Pratyantar Jupiter opens a mentor door - thank a teacher.", "source": "Pratyantar"},
        ],
        "donts": [{"text": "Don't soothe mood with impulse shopping.", "source": "Chandrabal"}],
        "muhurat": {"windows": {
            "good_choghadiya": [
                {"label": "Chara", "start": "09:19:08", "end": "10:42:00", "plain": "Travel - good."},
                {"label": "Amrit", "start": "12:04:53", "end": "13:27:45", "plain": "Best window."}],
            "tri_kaal": [{"label": "Rahu Kaal", "start": "14:50:37", "end": "16:13:30", "plain": "x"}],
            "durmuhurta": [{"start": "08:45:59", "end": "09:30:11"}]}},
    }
    r.update(over)
    return r


def test_votes_give_score_checks_and_tiles():
    S = DS.build(_reading(), "Asha")
    assert 1 <= S["score"] <= 10
    assert S["checks"]["total"] == 8 and S["checks"]["lean"] == "good"
    keys = {t["key"]: t for t in S["tiles"]}
    assert set(keys) == {"work", "money", "people", "mind"}
    assert keys["mind"]["tone"] == "down"          # Moon's path is inauspicious
    assert keys["work"]["tone"] == "up"
    assert keys["work"]["text"].endswith("multitasking.")  # first sentence only
    assert S["headline"] == "A workable day for steady progress."
    assert "Move with your timing" in S["summary"]
    assert "The Moon in Aries" in S["summary"]
    assert S["focus"].startswith("children")


def test_hard_day_scores_low_and_leans_careful():
    bad = _reading(
        tarabala={"name": "Vipat", "tone": "caution"},
        chandrabal={"name": "x", "tone": "caution", "note": "Go slow."},
        gochar={"moon": {"inauspicious": True}, "sun": {"inauspicious": True},
                "mercury": {"inauspicious": True}},
        ashtakavarga={"moon": {"sav": 22, "bav": 2}, "sun": {"bav": 1}},
        tone="caution")
    S = DS.build(bad, "Asha")
    assert S["score"] <= 3 and S["tone"] == "down"
    assert S["checks"]["lean"] == "careful"
    assert "low today" in S["summary"]


def test_do_dont_lines_are_short_plain_and_skip_colour_repeats():
    S = DS.build(_reading(), "Asha")
    assert all("rules40" not in x and "red" not in x for x in S["dos"])
    assert S["dos"][0] == "Your star is a bright window — schedule the pitch you've postponed."
    assert S["dos"][1].startswith("The Jupiter sub-period")
    long = "x " * 20 + "- " + "Take twenty quiet minutes with a notebook before you decide anything"
    assert len(DS._short(long, 80)) <= 80


def test_timing_is_chronological_and_trimmed_to_minutes():
    t = DS.timing(_reading())
    assert [x["label"] for x in t["best"]] == ["Chara", "Amrit"]
    assert t["best"][0]["when"] == "09:19–10:42"
    assert t["avoid"][0]["label"] == "Rahu Kaal"
    assert t["avoid"][1]["when"] == "08:45–09:30"


def test_empty_reading_does_not_crash():
    S = DS.build({}, "")
    assert S["tiles"] == [] and S["score"] == 5


def test_free_card_is_one_screen_with_one_unlock_card_and_paid_folds_the_working():
    import daily_card as DC
    r = _reading()
    r["dasha"] = {"md": "Rahu", "ad": "Sun", "pd": "Jupiter"}
    free = DC.render(r, name="Asha", day=date(2026, 10, 27), paid=False)
    paid = DC.render(r, name="Asha", day=date(2026, 10, 27), paid=True)
    assert free.count('class="dy-unlock"') == 1
    assert 'class="blurred"' not in free and 'class="lock-wrap"' not in free
    assert 'class="qa-window' not in free
    assert "Best and avoid times" not in free        # timing is the paid half
    assert free.count('class="dy-tile ') == 4
    assert "Rahu – Sun – Jupiter" in free             # the locked card names the reader's clock
    assert "Best and avoid times" in paid and "Why today reads this way" in paid
    assert paid.count('class="dy-fold"') == 1
    assert "dy-unlock" not in paid.split("</style>", 2)[-1]

def test_money_tile_comes_from_money_signals_not_the_mood_note():
    bad_note = {"name": "Vipat Rasi", "tone": "caution",
                "do_note": "Confirm commute and gadget backups.", "note": "Avoid sarcastic replies."}
    r = _reading(chandrabal=bad_note,
                 moon_transit={"sign": "Taurus", "house_from_moon": 6, "house_from_lagna": 11})
    money = {t["key"]: t for t in DS.build(r, "Asha")["tiles"]}["money"]
    assert "commute" not in money["text"] and "sarcastic" not in money["text"]
    assert "11th house" in money["text"]
    r12 = _reading(chandrabal=bad_note,
                   moon_transit={"sign": "Pisces", "house_from_moon": 6, "house_from_lagna": 12})
    money12 = {t["key"]: t for t in DS.build(r12, "Asha")["tiles"]}["money"]
    assert "12th house" in money12["text"] and money12["text"] != money["text"]
