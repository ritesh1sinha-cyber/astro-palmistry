"""Regression for the latest-report cleanup pass (post-review10)."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engines" / "astro"))
sys.path.insert(0, str(ROOT))

from area_modules import manifestations_for  # noqa: E402
from evidence_normalizer import (  # noqa: E402
    normalize_casebook_evidence,
    normalize_classical_evidence,
    normalize_vote,
)
from narration.verdict_phrases import (  # noqa: E402
    overall_picture_phrase,
    promise_proof_line,
)
from personalized_confluence import (  # noqa: E402
    clear_promise_cache,
    resolve_wealth_subareas,
    wealth_comparison_sentence,
)
from promise_dashboard import _bucket_for  # noqa: E402
from qa_checks.customer_text_sanitizer import (  # noqa: E402
    is_customer_safe,
    validate_customer_text,
)
from qa_checks.report_consistency import validate_report_consistency  # noqa: E402

_REVIEW = ROOT / "ci-storage" / "review_html"
_STYLE_SCRIPT = re.compile(r"<(style|script)\b.*?</\1>", re.S | re.I)
_FORBIDDEN_BODY = [
    re.compile(r"debt-ridden", re.I),
    re.compile(r"hurt by fire", re.I),
    re.compile(r"Existing chart-rule", re.I),
    re.compile(r"D\d+\s+area ruler", re.I),
    re.compile(r"Life-area promise", re.I),
]


def test_classical_casebook_never_returned_raw():
    vote = SimpleNamespace(
        method="the case-book method",
        value=-1.2,
        because=(
            "He will be debt-ridden, hurt by fire and accident, bereaved "
            "and having inclination in inauspicious deeds."
        ),
    )
    for fn in (normalize_vote, normalize_classical_evidence, normalize_casebook_evidence):
        ev = fn(vote, area="health")
        low = ev.normalized_reason.lower()
        assert "debt-ridden" not in low
        assert "hurt by fire" not in low
        assert ev.normalized_reason.strip()


def test_you_will_be_classical_is_unsafe():
    assert not is_customer_safe(
        "You will be debt-ridden, hurt by fire and accident."
    )


def test_promise_proof_line_uses_underlying_promise():
    line = promise_proof_line(status="supported", kind="promise")
    assert line.startswith("Underlying promise:")
    assert "Life-area promise" not in line
    ch = promise_proof_line(status="strongly_indicated", kind="challenge")
    assert ch.startswith("Challenge pattern:")


def test_overall_picture_reconciles_caution_majority():
    phrase = overall_picture_phrase(
        direction="up", confidence="moderate", agreement="partial",
        support=2, caution=5,
    )
    assert "caution" in phrase.lower()
    assert "although more systems show caution" in phrase.lower() or "mixed" in phrase.lower()


def test_challenge_overall_never_says_supportive_when_indicated():
    phrase = overall_picture_phrase(
        direction="up", confidence="high", agreement="partial",
        support=3, caution=4, kind="challenge",
        challenge_status="strongly_indicated",
    )
    assert "supportive" not in phrase.lower() or "caution" in phrase.lower()
    assert "challenge" in phrase.lower() or "caution" in phrase.lower()


def test_troubles_catalog_strong_is_pressure_not_resilience():
    items = manifestations_for(
        "troubles", promise_status="strongly_indicated", limit=3,
    )
    joined = " ".join(items).lower()
    assert "resilience" not in joined
    assert any(
        k in joined for k in ("stress", "workload", "complications", "routine")
    )


def test_sudden_gains_requires_both_families(monkeypatch):
    clear_promise_cache()

    def fake_natal(pc, cfg, kind="promise"):
        return 1.5, ["natal support"], []

    def fake_varga(pc, cfg, kind="promise"):
        return -0.2, [], ["varga weak"]

    monkeypatch.setattr(
        "personalized_confluence._natal_family", fake_natal,
    )
    monkeypatch.setattr(
        "personalized_confluence._varga_family", fake_varga,
    )
    monkeypatch.setattr(
        "personalized_confluence._cap_divisional_to_natal",
        lambda nf, vf: vf,
    )
    subs = resolve_wealth_subareas({"planets": {}, "house_lords": {}, "divisional": {}})
    sg = subs["sudden_gains"]
    assert sg["status"] not in ("strongly_supported", "supported")


def test_wealth_comparison_grammar():
    subs = {
        "income": {"status": "mixed", "score": 0.2, "status_label": "Mixed"},
        "accumulation": {"status": "weak", "score": -0.5, "status_label": "Weak"},
        "business_gains": {
            "status": "supported", "score": 1.0, "status_label": "Supported",
        },
        "sudden_gains": {
            "status": "insufficient_evidence", "score": -1.0,
            "status_label": "Limited evidence",
        },
    }
    sentence = wealth_comparison_sentence(subs)
    assert " is stronger" not in sentence or "ability to earn is" in sentence
    # Plural subject must not use "is"
    assert "gains through business is" not in sentence


def test_dashboard_weak_challenge_never_strongest():
    card = SimpleNamespace(
        label="Health & Energy",
        confluence={
            "promise": {"kind": "challenge", "status": "weak"},
            "activation": {"status": "inactive"},
        },
    )
    assert _bucket_for(card) != "strongest"

    strong = SimpleNamespace(
        label="Health & Energy",
        confluence={
            "promise": {"kind": "challenge", "status": "strongly_indicated"},
            "activation": {"status": "active"},
        },
    )
    assert _bucket_for(strong) == "needs_care"


def test_consistency_flags_bare_supportive_with_caution_majority():
    html = (
        '<article class="card">'
        '<span class="area">Money</span>'
        "<strong>The overall picture is supportive.</strong>"
        "<span>2 support · 5 caution · 1 neutral</span>"
        "</article>"
    )
    result = validate_report_consistency(html)
    assert not result["ok"]
    assert any("caution count" in f for f in result["failures"])

    # Demanding headlines that mention residual support must not false-positive.
    ok_html = (
        '<article class="card">'
        '<span class="area">Children</span>'
        "<strong>The overall picture is more demanding, although a few "
        "supportive signals remain.</strong>"
        "<span>3 support · 5 caution · 1 neutral</span>"
        "</article>"
    )
    ok = validate_report_consistency(ok_html)
    assert not any("caution count" in f for f in ok["failures"])


@pytest.mark.parametrize(
    "name",
    [
        "astro_full_report_paid.html",
        "astro_full_report_free.html",
        "ramesh_1986-03-08_delhi_paid.html",
        "suresh_1990-01-12_delhi_paid.html",
    ],
)
def test_review_html_has_no_classical_leaks(name):
    path = _REVIEW / name
    if not path.exists():
        pytest.skip(f"{name} not regenerated yet")
    body = _STYLE_SCRIPT.sub(" ", path.read_text(encoding="utf-8", errors="ignore"))
    for pat in _FORBIDDEN_BODY:
        assert not pat.search(body), f"{name}: leaked {pat.pattern}"
    leaks = validate_customer_text(body)
    assert not leaks, f"{name}: {leaks}"


def test_free_locked_list_has_no_dn_codes():
    path = _REVIEW / "astro_full_report_free.html"
    if not path.exists():
        pytest.skip("free HTML not regenerated yet")
    text = path.read_text(encoding="utf-8", errors="ignore")
    for block in re.findall(r'<ul class="promise-locked">.*?</ul>', text, re.S):
        assert not re.search(r"\bD\d+\b", block), block
