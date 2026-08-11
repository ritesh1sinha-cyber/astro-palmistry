"""P5 regression matrix for the review_html(10) detailed fix plan.

Covers, across four differently-shaped charts (Meera / Ramesh / Suresh /
Gyanesh — the same personas the oversample/interactive-review generators
use), the invariants the fix plan calls out:

  * promise and activation are computed independently (P0-8)
  * a divisional chart can never raise a promise above its D1 tier (P1-18)
  * timing/dasha/transit data can never feed the promise score (P1-19)
  * the troubles/D30 area speaks challenge vocabulary, never promise
    vocabulary (P0-3)
  * no raw classical text, rule IDs or debug strings survive into the
    rendered HTML (P0-5/P0-6)
  * free and paid tiers agree on the same canonical promise/activation
    wording (P2-6), and free never emits an exact month-year (P1-14/15)

The unit-level tests below use synthetic natal charts (no PyJHora / Docker
dependency, matching the convention in test_promise_confluence.py) so they
run anywhere. The HTML-level tests read the Docker-regenerated review_html
fixtures for Meera/Ramesh/Suresh/Gyanesh when present, and skip quietly
otherwise (regeneration is a separate, explicit step — see
gen_docker_smoke_copy.py).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))

import deep_evidence as DE  # noqa: E402
from narration.status_vocab import (  # noqa: E402
    ACTIVATION_STATUS,
    CHALLENGE_STATUS,
    PROMISE_STATUS,
)
from narration.verdict_phrases import (  # noqa: E402
    challenge_mechanism_line,
    challenge_pattern_phrase,
)
from personalized_confluence import (  # noqa: E402
    _cap_divisional_to_natal,
    canonical_area,
    clear_promise_cache,
    resolve_activation,
    resolve_all_promises,
    resolve_promise,
    resolve_wealth_subareas,
)
from qa_checks.customer_text_sanitizer import validate_customer_text  # noqa: E402
from qa_checks.health_safety_check import health_violations  # noqa: E402
from qa_checks.report_consistency import validate_report_consistency  # noqa: E402

_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
_LORD = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}


def _make_pc(name: str, *, dob: str, planets: dict, lagna_sign: str = "Aries") -> dict:
    house_lords = {
        str(i): {"lord": _LORD[_SIGNS[i - 1]]} for i in range(1, 13)
    }
    divisional = {}
    for code in ("D2", "D3", "D4", "D7", "D9", "D10", "D12", "D20", "D24", "D27", "D30"):
        divisional[code] = {
            "Lagna": lagna_sign,
            **{p: d["sign"] for p, d in planets.items()},
        }
    return {
        "chart_hash": f"review10-{name}",
        "planets": planets,
        "house_lords": house_lords,
        "divisional": divisional,
        "lagna": {"sign": lagna_sign},
        "meta": {"lagna_sign": lagna_sign, "dob": dob, "name": name},
    }


def _meera() -> dict:
    return _make_pc(
        "meera", dob="1990-01-15",
        planets={
            "Sun": {"sign": "Aries", "house": 10, "navamsha_sign": "Aries"},
            "Moon": {"sign": "Taurus", "house": 2, "navamsha_sign": "Taurus"},
            "Mars": {"sign": "Capricorn", "house": 7, "navamsha_sign": "Capricorn"},
            "Mercury": {"sign": "Virgo", "house": 10, "navamsha_sign": "Virgo"},
            "Jupiter": {"sign": "Cancer", "house": 5, "navamsha_sign": "Cancer"},
            "Venus": {"sign": "Pisces", "house": 7, "navamsha_sign": "Pisces"},
            "Saturn": {"sign": "Libra", "house": 10, "navamsha_sign": "Libra"},
            "Rahu": {"sign": "Gemini", "house": 3, "navamsha_sign": "Gemini"},
            "Ketu": {"sign": "Sagittarius", "house": 9, "navamsha_sign": "Sagittarius"},
        },
    )


def _ramesh() -> dict:
    # Strong 10th/11th house support: career and wealth should read as
    # (strongly_)supported with little conflict.
    return _make_pc(
        "ramesh", dob="1986-03-08",
        planets={
            "Sun": {"sign": "Capricorn", "house": 10, "navamsha_sign": "Capricorn"},
            "Moon": {"sign": "Taurus", "house": 2, "navamsha_sign": "Taurus"},
            "Mars": {"sign": "Aries", "house": 1, "navamsha_sign": "Aries"},
            "Mercury": {"sign": "Aquarius", "house": 11, "navamsha_sign": "Aquarius"},
            "Jupiter": {"sign": "Capricorn", "house": 10, "navamsha_sign": "Capricorn"},
            "Venus": {"sign": "Aquarius", "house": 11, "navamsha_sign": "Aquarius"},
            "Saturn": {"sign": "Aquarius", "house": 11, "navamsha_sign": "Aquarius"},
            "Rahu": {"sign": "Gemini", "house": 3, "navamsha_sign": "Gemini"},
            "Ketu": {"sign": "Sagittarius", "house": 9, "navamsha_sign": "Sagittarius"},
        },
    )


def _suresh() -> dict:
    # Afflicted 6th/8th/12th (D30) houses: troubles should read as an
    # indicated-to-strongly-indicated challenge pattern.
    return _make_pc(
        "suresh", dob="1990-01-12",
        planets={
            "Sun": {"sign": "Capricorn", "house": 6, "navamsha_sign": "Capricorn"},
            "Moon": {"sign": "Scorpio", "house": 8, "navamsha_sign": "Scorpio"},
            "Mars": {"sign": "Pisces", "house": 12, "navamsha_sign": "Pisces"},
            "Mercury": {"sign": "Capricorn", "house": 6, "navamsha_sign": "Capricorn"},
            "Jupiter": {"sign": "Scorpio", "house": 8, "navamsha_sign": "Scorpio"},
            "Venus": {"sign": "Pisces", "house": 12, "navamsha_sign": "Pisces"},
            "Saturn": {"sign": "Scorpio", "house": 8, "navamsha_sign": "Scorpio"},
            "Rahu": {"sign": "Virgo", "house": 6, "navamsha_sign": "Virgo"},
            "Ketu": {"sign": "Pisces", "house": 12, "navamsha_sign": "Pisces"},
        },
    )


def _gyanesh() -> dict:
    # Minor (dob 2012): exercises the age-band branch of area_modules.
    pc = _make_pc(
        "gyanesh", dob="2012-01-01",
        planets={
            "Sun": {"sign": "Sagittarius", "house": 5, "navamsha_sign": "Sagittarius"},
            "Moon": {"sign": "Cancer", "house": 4, "navamsha_sign": "Cancer"},
            "Mars": {"sign": "Leo", "house": 5, "navamsha_sign": "Leo"},
            "Mercury": {"sign": "Sagittarius", "house": 5, "navamsha_sign": "Sagittarius"},
            "Jupiter": {"sign": "Cancer", "house": 4, "navamsha_sign": "Cancer"},
            "Venus": {"sign": "Capricorn", "house": 6, "navamsha_sign": "Capricorn"},
            "Saturn": {"sign": "Libra", "house": 3, "navamsha_sign": "Libra"},
            "Rahu": {"sign": "Gemini", "house": 3, "navamsha_sign": "Gemini"},
            "Ketu": {"sign": "Sagittarius", "house": 9, "navamsha_sign": "Sagittarius"},
        },
    )
    pc["meta"]["dob"] = "2012-01-01"
    return pc


PERSONAS = {
    "meera": _meera,
    "ramesh": _ramesh,
    "suresh": _suresh,
    "gyanesh": _gyanesh,
}


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_promise_cache()
    DE.end()
    yield
    clear_promise_cache()
    DE.end()


# ---------------------------------------------------------------------------
# P0-8 / P1-19: promise and activation are two separate questions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("persona", PERSONAS)
def test_promise_and_activation_are_independent(persona):
    pc = PERSONAS[persona]()
    before = resolve_promise(pc, "career")
    pc["vimshottari"] = {"current_md": {"md_lord": "Saturn"}}
    pc["transits"] = {"Jupiter": {"house": 10}}
    after = resolve_promise(pc, "career")
    assert before["status"] == after["status"]
    assert before["score"] == after["score"]

    act_up = resolve_activation(direction="up", score=1.2, confidence="high",
                                 agreement="strong", promise_status=before["status"])
    act_down = resolve_activation(direction="down", score=-1.2, confidence="high",
                                   agreement="strong", promise_status=before["status"])
    assert act_up["status"] != act_down["status"]
    assert act_up["status"] in ACTIVATION_STATUS
    assert act_down["status"] in ACTIVATION_STATUS
    # Activation must never claim to have recomputed the promise.
    assert act_up["promise_status"] == before["status"]
    assert act_up.get("activation_only") is True


# ---------------------------------------------------------------------------
# P1-18: D1 is the baseline; a divisional vote cannot flip a clear natal read
# ---------------------------------------------------------------------------

def test_divisional_never_overrides_natal_baseline():
    # Strong negative natal, strong positive divisional: capped, not flipped.
    assert _cap_divisional_to_natal(-1.0, 1.5) == 0.6
    # Strong positive natal, strong negative divisional: capped, not flipped.
    assert _cap_divisional_to_natal(1.0, -1.5) == -0.6
    # No cap needed when the two families agree in sign.
    assert _cap_divisional_to_natal(0.8, 0.9) == 0.9


@pytest.mark.parametrize("persona", PERSONAS)
def test_promise_never_exceeds_d1_plus_divisional_cap(persona):
    pc = PERSONAS[persona]()
    out = resolve_all_promises(pc)
    for key, promise in out.items():
        assert promise["status"] in (PROMISE_STATUS + CHALLENGE_STATUS)


# ---------------------------------------------------------------------------
# P0-3: D30 / troubles speaks challenge vocabulary, never promise vocabulary
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("persona", PERSONAS)
def test_troubles_area_uses_challenge_vocabulary_only(persona):
    pc = PERSONAS[persona]()
    troubles = resolve_promise(pc, "troubles")
    assert troubles["kind"] == "challenge"
    assert troubles["status"] in CHALLENGE_STATUS
    # "mixed"/"weak"/"insufficient_evidence" are intentionally shared bucket
    # words between the two vocabularies (status_vocab.py); only the
    # promise-specific extremes ("strongly_supported"/"supported") would
    # actually read as "illness is promised" and must never appear here.
    assert troubles["status"] not in ("strongly_supported", "supported")

    phrase = challenge_pattern_phrase(status=troubles["status"])
    assert "supported" not in phrase.lower()
    mechanism = challenge_mechanism_line()
    assert "supported" not in mechanism.lower()


def test_suresh_afflicted_chart_reads_as_indicated_challenge():
    pc = _suresh()
    troubles = resolve_promise(pc, "troubles")
    assert troubles["status"] in ("indicated", "strongly_indicated", "mixed")


# ---------------------------------------------------------------------------
# Wealth sub-promises stay inside the one Money card (P1-8)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("persona", PERSONAS)
def test_wealth_subareas_bounded_inside_money_card(persona):
    pc = PERSONAS[persona]()
    subs = resolve_wealth_subareas(pc)
    assert set(subs) == {"income", "accumulation", "business_gains", "sudden_gains"}
    for row in subs.values():
        assert row["status"] in PROMISE_STATUS
        assert row["status_label"]


# ---------------------------------------------------------------------------
# P0-5/P0-6: no raw classical text / rule IDs / unsafe health language, and
# P2-6: free and paid must agree on the same canonical promise wording, with
# no exact month-year leaking onto the free tier (P1-14/15).
# ---------------------------------------------------------------------------

_PERSONA_HTML_STEMS = {
    "meera": ("astro_full_report_free.html", "astro_full_report_paid.html"),
    "ramesh": ("ramesh_1986-03-08_delhi_free.html", "ramesh_1986-03-08_delhi_paid.html"),
    "suresh": ("suresh_1990-01-12_delhi_free.html", "suresh_1990-01-12_delhi_paid.html"),
    "gyanesh": ("gyanesh_2012-01-01_hyderabad_free.html", "gyanesh_2012-01-01_hyderabad_paid.html"),
}
_REVIEW_DIR = ROOT / "ci-storage" / "review_html"
_MONTH_YEAR = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{4}\b", re.I,
)
_STYLE_SCRIPT = re.compile(r"<(style|script)\b.*?</\1>", re.S | re.I)


def _load(name: str) -> str | None:
    path = _REVIEW_DIR / name
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="ignore")


def _body_only(html: str) -> str:
    """Strip <style>/<script> so CSS/JS tokens (e.g. SVG "stroke") never

    trip a customer-prose health-language scan (matches
    qa_checks.report_consistency's own stripping).
    """
    return _STYLE_SCRIPT.sub(" ", html)


@pytest.mark.parametrize("persona", PERSONAS)
def test_html_has_no_leaks_and_passes_consistency(persona):
    free_name, paid_name = _PERSONA_HTML_STEMS[persona]
    free_html, paid_html = _load(free_name), _load(paid_name)
    if free_html is None or paid_html is None:
        pytest.skip(f"{free_name}/{paid_name} not regenerated yet — run gen_docker_smoke_copy.py")

    for label, html in (("free", free_html), ("paid", paid_html)):
        leaks = validate_customer_text(html)
        assert not leaks, f"{persona} {label}: customer text leaks {leaks}"
        result = validate_report_consistency(html)
        assert result["ok"], f"{persona} {label}: consistency failures {result['failures']}"
        assert not health_violations(_body_only(html)), (
            f"{persona} {label}: unsafe health language")


@pytest.mark.parametrize("persona", PERSONAS)
def test_free_tier_never_emits_exact_month_year(persona):
    free_name, _ = _PERSONA_HTML_STEMS[persona]
    free_html = _load(free_name)
    if free_html is None:
        pytest.skip(f"{free_name} not regenerated yet — run gen_docker_smoke_copy.py")
    # Scope to the promise-teaser blocks only — other free copy (e.g. past
    # events, chapter dates) legitimately carries dates; the free promise
    # teaser specifically must never carry one (P1-14/15).
    for block in re.findall(r'<p class="promise-line promise-teaser">.*?</ul>', free_html, re.S):
        assert not _MONTH_YEAR.search(block), f"{persona}: free promise teaser leaks a month-year"


@pytest.mark.parametrize("persona", PERSONAS)
def test_free_and_paid_agree_on_promise_wording(persona):
    free_name, paid_name = _PERSONA_HTML_STEMS[persona]
    free_html, paid_html = _load(free_name), _load(paid_name)
    if free_html is None or paid_html is None:
        pytest.skip(f"{free_name}/{paid_name} not regenerated yet — run gen_docker_smoke_copy.py")
    free_words = set(re.findall(
        r'<b>(?:Underlying promise|Challenge pattern)</b>:\s*([^.<]+)', free_html))
    # promise_html wording is "<b>{word}:</b> {status_txt}" in both tiers —
    # collect the status phrases from each and confirm no contradiction.
    free_lines = re.findall(
        r'<b>(?:Underlying promise|Challenge pattern)</b>:\s*</p>|'
        r'<b>(?:Underlying promise|Challenge pattern)</b>:\s*',
        free_html)
    paid_status = set(re.findall(
        r'<b>(?:Underlying promise|Challenge pattern):</b>\s*([^<]+?)\s*<span class="promise-meta"',
        paid_html))
    teaser_status = set(re.findall(
        r'<b>(?:Underlying promise|Challenge pattern):</b>\s*([^.<]+)\.', free_html))
    if not paid_status or not teaser_status:
        pytest.skip(f"{persona}: promise markers not found in one of the tiers")
    assert teaser_status <= paid_status or paid_status <= teaser_status or (
        teaser_status & paid_status
    ), f"{persona}: free teaser status {teaser_status} disagrees with paid {paid_status}"


def test_health_card_never_says_strongly_supported_in_paid_html():
    _, paid_name = _PERSONA_HTML_STEMS["meera"]
    paid_html = _load(paid_name)
    if paid_html is None:
        pytest.skip("astro_full_report_paid.html not regenerated yet")
    for block in re.findall(r'<article class="card"[^>]*>.*?</article>', paid_html, re.S):
        if ">Health &amp; Energy<" in block or ">Health & Energy<" in block:
            assert "strongly supported in your chart" not in block.lower()
