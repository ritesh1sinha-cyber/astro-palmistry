import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from question_domain import keyword_domain

NAMED = {
    "marriage_relationship": [
        "when will i get girlfriend", "when will I get a girlfriend?", "Will my boyfriend propose",
        "will my crush say yes", "will I get back with my ex", "when will I meet my soulmate",
        "when will i find love", "when will i get married", "is my relationship going to last",
        "kab milegi meri girlfriend", "naaku girlfriend eppudu dorukutundi", "will I ever fall in love",
        "when will my breakup heal", "my gf and i fight a lot",
    ],
    "children_progeny": ["when will we have a baby", "will I conceive this year", "kab hoga bachcha"],
    "health_vitality": ["will my health improve", "will the surgery go well", "when will I recover"],
    "career_profession": ["when will I get a job", "will I get promoted", "should I start a business"],
    "wealth_finances": ["will I ever clear my debt", "when will my money problems end"],
    "property_assets": ["will I buy a house this year", "when can I buy a car"],
    "foreign_relocation": ["will I settle abroad", "will my visa be approved"],
    "education_learning": ["will I crack the upsc exam", "will I get college admission"],
    "litigation_disputes": ["will I win my court case"],
}

# Two areas named, or none: the softer routers decide.
UNSURE = ["will I get a job abroad", "will my girlfriend's health improve",
          "what does my future hold", "should I take the offer", "my exam results and my career"]


def test_a_question_that_names_its_subject_gets_that_area():
    for area, questions in NAMED.items():
        for q in questions:
            assert keyword_domain(q) == area, (q, keyword_domain(q), area)


def test_mixed_or_unnamed_questions_are_left_to_the_planner():
    for q in UNSURE:
        assert keyword_domain(q) == "", (q, keyword_domain(q))


def test_whole_words_only():
    # "exam" must not trip "ex", "single" is a relationship word but "singled out" is not
    assert keyword_domain("will my exam go well") == "education_learning"
    assert keyword_domain("") == ""


if __name__ == "__main__":
    test_a_question_that_names_its_subject_gets_that_area()
    test_mixed_or_unnamed_questions_are_left_to_the_planner()
    test_whole_words_only()
    print("ok")
