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
"""

from __future__ import annotations

import html as _html
from typing import Any

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


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def build(dob) -> dict:
    """Digits of the birth date, dropped into the square."""
    digits = [int(c) for c in f"{dob:%d%m%Y}" if c != "0"]
    counts = {n: digits.count(n) for n in range(1, 10)}
    missing = [n for n, c in counts.items() if c == 0]
    strong = [n for n, c in counts.items() if c >= 2]

    planes = {}
    for name, cells in PLANE.items():
        filled = sum(1 for c in cells if counts.get(c, 0) > 0)
        planes[name] = {"filled": filled, "complete": filled == 3,
                        "empty": filled == 0}
    return {"digits": digits, "counts": counts, "missing": missing,
            "strong": strong, "planes": planes,
            "complete_planes": [k for k, v in planes.items() if v["complete"]]}


def render(grid: dict, dob, *, paid: bool = False, price: int = 199) -> str:
    counts = grid["counts"]
    cells = ""
    for row in GRID:
        for n in row:
            c = counts.get(n, 0)
            label, what = MEANING.get(n, ("", ""))
            cells += (
                f'<div class="lo-cell {"has" if c else "empty"}">'
                f'<span class="lo-n">{n}</span>'
                f'<span class="lo-count">{"".join(str(n) for _ in range(c)) if c else "—"}</span>'
                f'<span class="lo-what">{_e(label)}</span></div>')

    missing = grid["missing"]
    strong = grid["strong"]

    # Free: the grid, what is missing, and one line about each. Paid: the
    # remedies for the gaps, which is the part with an action attached.
    free_notes = ""
    if missing:
        first = missing[0]
        free_notes = (
            f'<p class="lo-note"><b>{len(missing)} of the 9 cells are empty '
            f'for you — {", ".join(str(m) for m in missing)}.</b> '
            f'{_e(MISSING.get(first, ""))}</p>')
    if strong:
        s0 = strong[0]
        free_notes += f'<p class="lo-note">{_e(REPEATED.get(s0, ""))}</p>'

    complete = grid["complete_planes"]
    plane_note = ""
    if complete:
        plane_note = (
            f'<p class="lo-note">You have a complete '
            f'<b>{_e(complete[0])}</b> line — three cells in a row filled, '
            f'which the system treats as an unusual strength.</p>')

    locked = "" if paid else f"""
  <div class="remedy-locked">
    <b>Each empty cell has a named remedy</b> — the number to strengthen, how,
    and which of your missing numbers to work on first (they are not equal).
    The full reading also dates your next three personal years. ₹{price}
  </div>"""

    return f"""
<section class="lo-shu">
  <div class="ev-label">Your Lo Shu grid — from {dob:%d %B %Y}</div>
  <p class="lo-lede">Every digit of your birth date drops into a fixed square.
  What matters is not what is there — it is what is missing.</p>
  <div class="lo-grid">{cells}</div>
  {free_notes}
  {plane_note}
  {locked}
</section>"""
