"""chart_lines: sentences must follow the chart, never a single flattering default."""
import chart_lines as CL


def _pc(sun_house, sun_dignity, lords=None, others=None):
    planets = {"Sun": {"sign": "Aries", "house": sun_house, "dignity": sun_dignity}}
    planets.update(others or {})
    return {"planets": planets, "house_lords": lords or {}}


def test_grade_follows_dignity_and_house():
    strong = _pc(10, "exalted")
    strained = _pc(8, "debilitated")
    assert CL.planet_grade(strong, "Sun") == "strong"
    assert CL.planet_grade(strained, "Sun") == "strained"


def test_malefic_company_lowers_score():
    alone = _pc(5, "friend")
    crowded = _pc(5, "friend", others={"Saturn": {"sign": "Aries", "house": 5, "dignity": ""}})
    assert CL.score_planet(crowded, "Sun") < CL.score_planet(alone, "Sun")


def test_owns_and_lord_of_read_the_chart():
    lords = {"4": {"lord": "Moon"}, "9": {"lord": "Moon"}, "1": {"lord": "Sun"}}
    pc = _pc(1, "", lords=lords)
    assert CL.owns(pc, "Moon") == [4, 9]
    assert CL.lord_of(pc, 1) == "Sun"


def test_period_line_differs_between_strong_and_strained():
    lords = {"10": {"lord": "Sun"}}
    a = CL.period_line(_pc(10, "exalted", lords), "Sun", "now")
    b = CL.period_line(_pc(8, "debilitated", lords), "Sun", "now")
    assert a and b and a != b
