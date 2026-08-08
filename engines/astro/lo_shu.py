"""The Lo Shu grid — the one numerology visual people already recognise.

Every digit of the date of birth is dropped into a fixed 3×3 magic square. What
the reader is looking for is not the arithmetic, it is the **holes**: a number
that appears three times is an over-supplied trait, and a number missing
entirely is the classical marker of a lesson unlearned.

It earns its place in the product for a reason that has nothing to do with
belief. It is a picture. The rest of numerology is a list of numbers with
paragraphs attached; this is a grid the reader can look at and immediately see
that three of the nine cells are empty. Curiosity does the rest, and the missing
numbers are the natural paid hook because each one has a specific remedy.

The layout is the standard one used in Indian and Chinese practice:

    4 9 2
    3 5 7
    8 1 6

This module is now data and arithmetic only. The grid is drawn by
`numerology_cards`, so that the cells it calls empty are the same cells the
remedies below it address.
"""

from __future__ import annotations

#: display order, row by row
GRID = ((4, 9, 2), (3, 5, 7), (8, 1, 6))

PLANE = {
    "mind": (4, 9, 2), "emotion": (3, 5, 7), "practical": (8, 1, 6),
    "thought": (4, 3, 8), "will": (9, 5, 1), "action": (2, 7, 6),
}

MEANING = {
    1: ("Self-expression", "how easily you say what you mean"),
    2: ("Sensitivity", "how much of other people you pick up"),
    3: ("Memory & thinking", "how you hold and order information"),
    4: ("Order & method", "your patience for doing it properly"),
    5: ("Balance & freedom", "the middle cell — the one everything routes through"),
    6: ("Home & creativity", "what you build and who you build it for"),
    7: ("Loss & learning", "what life has taught you the hard way"),
    8: ("Method & money", "your grip on the material side"),
    9: ("Ambition & drive", "how far you intend to go"),
}

MISSING = {
    1: "Saying the difficult thing out loud has never come easily to you.",
    2: "You read situations well but doubt your reading of them.",
    3: "You lose track of detail unless you write it down — and you know it.",
    4: "Routine feels like a cage rather than a floor.",
    5: "The centre cell is empty, which classically means life has taught you balance by removing it first.",
    6: "You give to family more easily than you receive from them.",
    7: "You have not yet had the loss that the system says teaches this one.",
    8: "Money management is learned behaviour for you, not instinct.",
    9: "You aim lower than your capacity, and other people notice before you do.",
}

REPEATED = {
    1: "You express yourself more than you realise — sometimes past the point of being heard.",
    2: "You carry other people's moods as if they were assignments.",
    3: "A strong memory, and a tendency to relitigate the past with it.",
    4: "Method is your default answer, including to problems method cannot solve.",
    5: "An unusually strong centre — you recover balance faster than most.",
    6: "Home and duty pull at you constantly, and you rarely resent it.",
    7: "Life has taught you through loss more than once. It shows.",
    8: "Money and structure are instinctive for you.",
    9: "Drive in surplus. The risk is spending it on the wrong target.",
}


PLANE_NAME = {
    "mind": "mind", "emotion": "emotion", "practical": "practical",
    "thought": "thought", "will": "will", "action": "action",
}


def planes(counts) -> dict:
    """Which of the six three-in-a-row lines are complete, and which are bare.

    `counts` is any mapping of digit to how many times it appears in the square.
    The caller decides what goes into the square — the date alone, or the date
    with the birth-day and life-path pillars placed — because that choice has to
    match whatever the same page calls "missing", or the reader is told two
    different things about the same grid.
    """
    out = {}
    for name, cells in PLANE.items():
        filled = sum(1 for c in cells if counts.get(c, 0) > 0)
        out[name] = {"filled": filled, "complete": filled == 3,
                     "empty": filled == 0}
    return out


def build(dob) -> dict:
    """Digits of the birth date, dropped into the square."""
    digits = [int(c) for c in f"{dob:%d%m%Y}" if c != "0"]
    counts = {n: digits.count(n) for n in range(1, 10)}
    p = planes(counts)
    return {"digits": digits, "counts": counts,
            "missing": [n for n, c in counts.items() if c == 0],
            "strong": [n for n, c in counts.items() if c >= 2],
            "planes": p,
            "complete_planes": [k for k, v in p.items() if v["complete"]]}
