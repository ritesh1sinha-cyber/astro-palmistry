"""Hand shape, fingers, and the special marks — the curiosity layer.

Palmistry has one advantage no other technique in this product has: the reader
can look at their own hand while they read. So the free half should be the
things they can immediately verify by turning their palm over — the shape, the
finger proportions, and whether that mark near the base of the index finger is
in fact a trident.

Special marks are the strongest curiosity hook in the whole product. A star, a
trident, a fish or a temple sign are rare, visually distinctive, and carry
famous classical meanings. Naming that a mark is *present* and where, while
holding back what it means for that specific hand, is the cleanest paid split
available: the reader is not being denied an answer they already had, they are
being told something exists that they did not know to look for.

The honest constraint: these are read from what the CV pipeline actually
detected. A mark we did not detect is never asserted, and the tab says how many
were searched for so the absence of marks reads as a finding rather than a gap.
"""

from __future__ import annotations

import html as _html
from typing import Any

# ---------------------------------------------------------------------------
# hand shape → temperament. Free: the reader can check it in two seconds.
# ---------------------------------------------------------------------------

HAND_SHAPE = {
    "earth": ("Earth hand — square palm, short fingers",
              "You trust what you can handle. Abstractions have to be turned "
              "into something concrete before you believe them, which makes you "
              "slower to start and much harder to fool."),
    "air": ("Air hand — square palm, long fingers",
            "You think in words and need to talk things through to know what "
            "you believe. Silence in a room reads to you as a problem to solve."),
    "water": ("Water hand — long palm, long fingers",
              "You absorb the mood of a room before anyone speaks, and you pay "
              "for it afterwards. Your instincts are usually right and rarely "
              "explainable."),
    "fire": ("Fire hand — long palm, short fingers",
             "You decide fast and correct on the move. Waiting costs you more "
             "than being wrong does."),
    "philosophical": ("Philosophical hand — knotted joints, long fingers",
                      "You cannot take a claim on trust; you have to take it "
                      "apart first. It makes you excellent at analysis and "
                      "exhausting in an argument."),
    "spatulate": ("Spatulate hand — flared fingertips",
                  "Restlessness with a purpose. You are the person who changes "
                  "the method rather than working harder at the old one."),
    "conic": ("Conic hand — tapering fingers",
              "Aesthetics register with you before function does. You are "
              "impatient with ugly solutions even when they work."),
}

FINGER_NOTE = {
    "jupiter_long": "Your index finger is long relative to the ring finger — "
                    "classically the mark of someone who needs to be in charge "
                    "of their own work, and chafes when they are not.",
    "jupiter_short": "A shorter index finger — you would rather do the work "
                     "well than run the room, and you have turned down "
                     "authority at least once.",
    "saturn_long": "A long middle finger — caution and duty run deep. You are "
                   "the one who reads the terms before signing.",
    "apollo_long": "A long ring finger — you need an audience for your work, "
                   "even a small one. Recognition is not vanity for you, it is "
                   "fuel.",
    "mercury_long": "A long little finger — you talk and negotiate well, and "
                    "you have talked your way into and out of things.",
    "mercury_short": "A short little finger — you struggle to say the "
                     "self-promoting thing, even when it is true.",
    "thumb_flexible": "A flexible thumb — you bend rather than break, and you "
                      "have been called too accommodating.",
    "thumb_stiff": "A stiff thumb — once you have decided, you are immovable, "
                   "and you know which arguments this has cost you.",
}

# ---------------------------------------------------------------------------
# special marks — named freely, interpreted behind the paywall
# ---------------------------------------------------------------------------

MARKS = {
    "trident": ("Trident (trishul)", "one of the most fortunate marks in the "
                "tradition — rare enough that most hands do not carry one"),
    "star": ("Star", "sudden, unearned events — famously double-edged, and it "
             "matters enormously which mount it sits on"),
    "fish": ("Fish (matsya)", "the classical sign of protected fortune, "
             "specially noted in Indian palmistry"),
    "temple": ("Temple sign", "the mark of a life with a genuine spiritual "
               "thread running through it"),
    "triangle": ("Triangle", "aptitude — where it sits names the specific talent"),
    "square": ("Square", "protection. A square over a break means the damage "
               "was contained"),
    "cross": ("Cross", "an obstacle or a turning point, depending entirely on "
              "placement"),
    "island": ("Island", "a period of confinement or drain on the line it sits on"),
    "grille": ("Grille", "energy scattered rather than lost"),
    "circle": ("Circle", "the rarest mark of all, and its meaning depends on "
               "which mount carries it"),
    "vertical_lines": ("Vertical lines on a mount",
                       "concentrated strength in that mount's department"),
}

MOUNT_AREA = {
    "jupiter": "ambition and authority", "saturn": "discipline and solitude",
    "apollo": "recognition and creative work", "sun": "recognition and creative work",
    "mercury": "communication and business", "venus": "affection and vitality",
    "mars": "courage and resistance", "moon": "imagination and travel",
    "luna": "imagination and travel",
}


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def build(raw: dict) -> dict:
    """Pull shape, finger notes and detected marks out of the engine output."""
    features = (raw.get("features") or {})
    morph = features.get("morphology") or {}
    shape = str(morph.get("hand_type") or "").lower()

    fingers = []
    for key in ("jupiter_long", "jupiter_short", "saturn_long", "apollo_long",
                "mercury_long", "mercury_short", "thumb_flexible", "thumb_stiff"):
        if morph.get(key) or (features.get("fingers") or {}).get(key):
            fingers.append(FINGER_NOTE[key])

    found = []
    for mark in (raw.get("special_marks") or []):
        kind = str(mark.get("kind") or mark.get("type") or "").lower()
        where = str(mark.get("mount") or mark.get("on") or mark.get("line") or "").lower()
        if kind in MARKS:
            found.append({"kind": kind, "label": MARKS[kind][0],
                          "teaser": MARKS[kind][1], "where": where,
                          "where_plain": MOUNT_AREA.get(where, where)})
    return {"shape": shape, "shape_text": HAND_SHAPE.get(shape),
            "fingers": fingers, "marks": found,
            "searched": raw.get("marks_searched") or len(MARKS)}


def render(block: dict, *, paid: bool = False, price: int = 499) -> str:
    shape = block.get("shape_text")
    fingers = block.get("fingers") or []
    marks = block.get("marks") or []

    shape_html = ""
    if shape:
        shape_html = f"""
  <div class="palm-shape">
    <div class="ev-label">Your hand shape — check this against your own palm</div>
    <h4>{_e(shape[0])}</h4>
    <p>{_e(shape[1])}</p>
  </div>"""

    finger_html = ""
    if fingers:
        finger_html = (
            '<div class="evidence"><span class="ev-label">What your fingers say'
            '</span><ul>'
            + "".join(f"<li>{_e(f)}</li>" for f in fingers[:3]) + "</ul></div>")

    if marks:
        rows = "".join(f"""
    <li class="mark">
      <div class="mark-top"><b>{_e(m['label'])}</b>
        <span class="mark-where">{_e(('on the mount of ' + m['where'].title())
                                     if m['where'] else 'detected')}</span></div>
      <div class="mark-teaser">{_e(m['teaser'])}
        {f"— the {_e(m['where'].title())} mount governs {_e(m['where_plain'])}." if m['where'] else ""}</div>
      {'' if paid else '<div class="mark-locked">What it means for your hand specifically — locked</div>'}
    </li>""" for m in marks)
        marks_html = f"""
  <div class="palm-marks">
    <div class="ev-label">Special marks found on your hands</div>
    <p class="marks-lede">Most hands carry none of these. Yours carries
    <b>{len(marks)}</b>. We are naming them and where they sit — what each one
    means for your hand is the part worth paying for, because placement changes
    the reading completely.</p>
    <ul class="marks">{rows}</ul>
    {'' if paid else f'''<div class="remedy-locked">
      <b>Full interpretation of all {len(marks)} marks</b> — placement, which
      line each one touches, and what it has already done in your life. ₹{price}
    </div>'''}
  </div>"""
    else:
        marks_html = f"""
  <div class="palm-marks">
    <div class="ev-label">Special marks</div>
    <p class="marks-lede">We checked your palms for {block.get('searched')}
    classical marks — trident, star, fish, temple sign, triangle and the rest —
    and found none clearly formed. That is the common case, and saying so is
    more useful than inventing one.</p>
  </div>"""

    return shape_html + finger_html + marks_html
