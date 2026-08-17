"""Age-aware area labels for cards and past events."""

from __future__ import annotations

from interpretation.life_stage import is_minor

ADULT_LABELS: dict[str, str] = {
    "career": "Work & Career",
    "money": "Money",
    "love": "Relationships & Partnership",
    "home": "Home & Family",
    "children": "Children",
    "health": "Health & Energy",
    "learning": "Learning & Luck",
    "inner": "Inner Peace & Spirituality",
}

YOUNG_ADULT_LABELS: dict[str, str] = {
    "career": "Education & Early Career",
    "money": "Money",
    "love": "Relationships",
    "home": "Home & Family",
    "children": "Creativity & Projects",
    "health": "Health & Energy",
    "learning": "Learning & Luck",
    "inner": "Inner Peace & Spirituality",
}

MINOR_LABELS: dict[str, str] = {
    "career": "Studies & Recognition",
    "money": "Resources & Money Habits",
    "love": "Friendships & Close Bonds",
    "home": "Home & Family",
    "children": "Creativity & Projects",
    "health": "Health & Energy",
    "learning": "Learning & Luck",
    "inner": "Inner Peace & Spirituality",
}

ADULT_AREA_NAMES: dict[str, str] = {
    "career": "work and career",
    "money": "money and financial decisions",
    "love": "relationships and partnership",
    "home": "home and family",
    "children": "children and creativity",
    "health": "health and energy",
    "learning": "learning and direction",
    "inner": "your peace of mind and spirituality",
}

YOUNG_ADULT_AREA_NAMES: dict[str, str] = {
    "career": "education and early career",
    "money": "money and financial independence",
    "love": "relationships and emotional connection",
    "home": "home and family",
    "children": "creativity and projects",
    "health": "health and energy",
    "learning": "learning and direction",
    "inner": "your peace of mind and spirituality",
}

MINOR_AREA_NAMES: dict[str, str] = {
    "career": "studies and recognition",
    "money": "resources and money habits",
    "love": "friendships and close bonds",
    "home": "home and family",
    "children": "creativity and projects",
    "health": "health and energy",
    "learning": "learning and direction",
    "inner": "your peace of mind and spirituality",
}


def area_label(area: str, age_band: str) -> str:
    if is_minor(age_band):
        table = MINOR_LABELS
    elif age_band == "young_adult":
        table = YOUNG_ADULT_LABELS
    else:
        table = ADULT_LABELS
    return table.get(area, ADULT_LABELS.get(area, area.replace("_", " ").title()))


def area_name(area: str, age_band: str) -> str:
    if is_minor(age_band):
        table = MINOR_AREA_NAMES
    elif age_band == "young_adult":
        table = YOUNG_ADULT_AREA_NAMES
    else:
        table = ADULT_AREA_NAMES
    return table.get(area, area.replace("_", " "))
