from llm.facts import _dedupe_evidence
from llm.schemas import CardFacts, EvidenceFact, ReportFacts, ReportProse, CardProse
from llm.fallback import card_fallback, report_fallback


def test_public_evidence_deduplicates_same_semantic_fact():
    items = [
        EvidenceFact(polarity="support", text="Recognition may grow through steady responsibility."),
        EvidenceFact(polarity="support", text=" Recognition may grow through steady responsibility. "),
        EvidenceFact(polarity="caution", text="Recognition may grow through steady responsibility."),
    ]
    out = _dedupe_evidence(items)
    # One sentence, kept once. Reading it as both support and caution told the
    # reader nothing and used up the card's evidence budget.
    assert len(out) == 1
    assert "contested" in out[0].semantic_tags


def test_card_fallback_is_conversational_not_technical():
    card = CardFacts(
        area="profession", label="Career & Recognition", status="mixed",
        activation_status="active", prediction_strength="mixed",
        question_lens="Will my career grow, and when will recognition become easier?",
    )
    out = card_fallback(card)
    assert "question_lens" in out
    assert "house" not in out["headline"].lower()
    assert "technical" not in out["summary"].lower()


def test_report_prose_has_master_narrative():
    p = ReportProse(
        opening="Your chart is asking you to choose where effort matters most.",
        master_narrative="Career is active while money asks for patience; relationships move on a different clock.",
        cards=[CardProse(area="profession", question_lens="Will my career grow?", headline="Recognition may take time, but responsibility is building.")],
    )
    assert p.master_narrative
    assert p.cards[0].question_lens


def test_fallback_report_contains_master_story():
    facts = ReportFacts(
        first_name="Meera", age_band="adult", age_years=36, gender="female",
        cards=[CardFacts(area="profession", label="Career & Recognition")],
    )
    out = report_fallback(facts)
    assert out["master_narrative"]
    assert out["opening"].startswith("Meera")
