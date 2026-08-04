"""Machine seams — the small tells that a person did not write this.

None of these change a single fact. They are the difference between output and
writing, and a reader registers them long before they could name them:

    DOB: 1985-03-08 Time: 12:56:00        →  Born 8 March 1985 at 12:56
    aspects house(s) 3rd, 8th, 12th        →  aspects houses 3, 8 and 12
    Debilitated house lord(s): 1st lord    →  Debilitated house lord: 1st lord
    ▼ 1/4 ▼ ◆ ◆ ▼                          →  a row that also says what it means

Counted across the real report set before this ran: 301 ISO dates, 88 `(s)`
plurals, 134 bare glyphs.

The `(s)` rule is the interesting one. "house(s)" is not wrong, it is *lazy* —
the writer did not know whether there would be one or several, so they made the
reader do the disambiguation. We do know: the list is right there. So we count
it and write the correct word.
"""

from __future__ import annotations

import re
from datetime import date

MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December")

# Irregular plurals that -s would mangle.
PLURALS = {
    "child": "children", "person": "people", "life": "lives",
    "wife": "wives", "half": "halves", "analysis": "analyses",
    "axis": "axes", "crisis": "crises", "index": "indices",
}

_PROTECTED = re.compile(r"<(script|style|code|pre)\b[^>]*>.*?</\1>", re.S | re.I)


def _map_text(html: str, fn) -> str:
    out, pos = [], 0
    for block in _PROTECTED.finditer(html):
        out.append(_outside_tags(html[pos:block.start()], fn))
        out.append(block.group(0))
        pos = block.end()
    out.append(_outside_tags(html[pos:], fn))
    return "".join(out)


def _outside_tags(chunk: str, fn) -> str:
    parts = re.split(r"(<[^>]+>)", chunk)
    return "".join(p if p.startswith("<") else fn(p) for p in parts)


# --- dates ------------------------------------------------------------------

_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_HMS = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d):([0-5]\d)\b")


def human_dates(text: str, *, long_form: bool = True) -> str:
    """1985-03-08 → 8 March 1985. Same fact, written the way people write it."""
    def sub(m: re.Match) -> str:
        y, mo, d = int(m[1]), int(m[2]), int(m[3])
        if not (1 <= mo <= 12 and 1 <= d <= 31):
            return m.group(0)
        try:
            date(y, mo, d)
        except ValueError:
            return m.group(0)
        month = MONTH_NAMES[mo - 1]
        return f"{d} {month} {y}" if long_form else f"{d} {month[:3]} {y}"
    return _ISO.sub(sub, text)


def human_times(text: str) -> str:
    """12:56:00 → 12:56. Nobody was born at a specific second."""
    return _HMS.sub(lambda m: f"{int(m[1]):02d}:{m[2]}"
                    if m[3] == "00" else m.group(0), text)


# --- plurals ----------------------------------------------------------------

_PLURAL_HEDGE = re.compile(r"\b([A-Za-z][\w-]*?)\(s\)(?=([^.<]{0,80}))")


def _looks_plural(tail: str) -> bool:
    """Is the list that follows one item, or several?"""
    head = tail.split(".")[0][:80]
    # "3rd, 8th, 12th" / "Venus, Mars" / "3 and 8"
    if re.search(r"\d+(?:st|nd|rd|th)?\s*(?:,|\band\b)\s*\d+", head):
        return True
    if head.count(",") >= 1:
        return True
    if re.search(r"\band\b", head) and len(re.findall(r"\b[A-Z][a-z]{2,}", head)) >= 2:
        return True
    return False


def fix_plurals(text: str) -> str:
    """house(s) → house or houses, decided by what actually follows."""
    def sub(m: re.Match) -> str:
        word, tail = m[1], m[2]
        if _looks_plural(tail):
            lower = word.lower()
            plural = PLURALS.get(lower)
            if plural:
                return plural.capitalize() if word[0].isupper() else plural
            if lower.endswith(("s", "x", "z", "ch", "sh")):
                return word + "es"
            if lower.endswith("y") and lower[-2:-1] not in "aeiou":
                return word[:-1] + "ies"
            return word + "s"
        return word
    return _PLURAL_HEDGE.sub(sub, text)


# --- ordinal house lists ----------------------------------------------------

_HOUSE_LIST = re.compile(
    r"\bhouses\s+((?:\d{1,2}(?:st|nd|rd|th)?\s*,\s*)+\d{1,2}(?:st|nd|rd|th)?)\b")


def tidy_house_lists(text: str) -> str:
    """"houses 3rd, 8th, 12th" → "houses 3, 8 and 12"."""
    def sub(m: re.Match) -> str:
        nums = re.findall(r"\d{1,2}", m[1])
        if len(nums) < 2:
            return m.group(0)
        return f"houses {', '.join(nums[:-1])} and {nums[-1]}"
    return _HOUSE_LIST.sub(sub, text)


# --- glyph legends ----------------------------------------------------------

GLYPH_MEANING = {
    "▲": "favourable", "⊕": "favourable", "★": "a strength",
    "▼": "under pressure", "⊖": "under pressure", "△": "weak",
    "◆": "mixed", "◐": "mixed",
}


def label_glyphs(html: str) -> str:
    """Give every verdict glyph a machine-readable direction.

    The glyphs are fine as visual shorthand — they are not fine as the *only*
    statement of a verdict, and a screen reader gets nothing from them at all.
    The direction marker also lets report_fact_guard verify that a rewrite kept
    the verdict pointing the same way.
    """
    def sub(m: re.Match) -> str:
        glyph = m.group(0)
        meaning = GLYPH_MEANING.get(glyph, "")
        direction = ("up" if meaning in ("favourable", "a strength")
                     else "down" if meaning in ("under pressure", "weak")
                     else "mixed")
        return (f'<span class="glyph" data-verdict="{direction}" '
                f'title="{meaning}" aria-label="{meaning}">{glyph}</span>')
    return _outside_tags(html, lambda t: re.sub(r"[▲▼◆△◐⊕⊖★]", sub, t))


# --- the pass ---------------------------------------------------------------

def depersonalise_slug(text: str, real_name: str = "") -> str:
    """"Name: ritxx" is a test handle, not a customer."""
    if not real_name:
        return re.sub(r"\b(?:Name|नाम)\s*:\s*(?:ritxx|ritz|sample|test)\b", "", text)
    return re.sub(r"\b(ritxx|ritz)\b", real_name, text)


def smooth(html: str, *, real_name: str = "") -> str:
    """Every seam fix, in one pass over the visible text."""
    def convert(text: str) -> str:
        text = human_dates(text)
        text = human_times(text)
        text = fix_plurals(text)
        text = tidy_house_lists(text)
        text = depersonalise_slug(text, real_name)
        text = re.sub(r"\s+([,.;:])", r"\1", text)     # " ," → ","
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text
    return label_glyphs(restructure_matrix(_map_text(html, convert)))


# --- the period grid --------------------------------------------------------
# The dasha confluence table is nine columns of ▲◆▼ with the key printed
# *underneath* it. A reader meets the glyphs before they are told what a glyph
# means, and even after the key, a row of nine symbols is something you decode
# rather than read.
#
# Two changes, no new facts: the key moves above the grid, and each row gains a
# sentence naming which areas are favourable and which are under pressure. The
# sentence uses only the column headings and the verdict directions already in
# the row — no counts are invented.

_MATRIX = re.compile(
    r"(<table[^>]*class=['\"][^'\"]*matrix[^'\"]*['\"][^>]*>)(.*?)(</table>)",
    re.S | re.I)
_NOTE_AFTER = re.compile(
    r"(</table>\s*(?:</div>\s*)?)(<div[^>]*class=['\"][^'\"]*note[^'\"]*['\"][^>]*>"
    r"\s*<b>\s*How to read this:.*?</div>)", re.S | re.I)

_UP, _DOWN = "▲⊕★", "▼⊖△"


def _row_sentence(fields: list[str], cells: list[str]) -> str:
    good = [f for f, c in zip(fields, cells) if any(g in c for g in _UP)]
    bad = [f for f, c in zip(fields, cells) if any(g in c for g in _DOWN)]

    def join(items: list[str]) -> str:
        items = [i.strip().rstrip(".") for i in items if i.strip()]
        if len(items) == 1:
            return items[0]
        return ", ".join(items[:-1]) + " and " + items[-1]

    if good and bad:
        return (f"{join(good)} carry this window; {join(bad)} need care.")
    if good:
        return f"{join(good)} are the areas working for you here."
    if bad:
        return f"{join(bad)} are where this window asks the most of you."
    return "A level window — nothing pulling strongly either way."


def restructure_matrix(html: str) -> str:
    """Key above the grid, and a plain sentence on every row."""
    # 1. lift the "How to read this" note above its table
    def lift(m: re.Match) -> str:
        return m.group(2) + m.group(1)
    out = _NOTE_AFTER.sub(lift, html)

    # 2. add a readable summary line to each data row
    def table(m: re.Match) -> str:
        open_tag, body, close = m.group(1), m.group(2), m.group(3)
        heads = re.findall(r"<th[^>]*class=['\"]fld['\"][^>]*>(.*?)</th>", body,
                           re.S | re.I)
        fields = [re.sub(r"<[^>]+>", "", h).strip() for h in heads]
        if not fields:
            return m.group(0)

        def row(rm: re.Match) -> str:
            inner = rm.group(0)
            if "<th" in inner.lower():
                return inner
            cells = re.findall(r"<td[^>]*>(.*?)</td>", inner, re.S | re.I)
            if len(cells) < len(fields):
                return inner
            tail = cells[-len(fields):]
            sentence = _row_sentence(fields, tail)
            span = len(cells)
            return (inner + f'<tr class="row-plain"><td colspan="{span}" '
                            f'style="font-size:.86em;color:#555;padding:2px 8px 10px">'
                            f'{sentence}</td></tr>')

        body = re.sub(r"<tr\b.*?</tr>", row, body, flags=re.S | re.I)
        return open_tag + body + close

    return _MATRIX.sub(table, out)
