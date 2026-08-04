"""The report, rebuilt as prediction cards instead of prose.

The old report was 68 documents of continuous text. Cleaning its language
helped, but the structure was still an analyst's working file: everything the
engine knew, in the order the engine computed it. A customer does not want the
working. They want to know what happens, when, and what to do about it.

So this does not touch the old HTML at all. It reads the precompute directly
and builds one thing repeatedly:

    ┌──────────────────────────────────────────────┐
    │ WORK & CAREER                    under strain │   ← area + direction
    │ Recognition lags behind the work you're       │   ← the claim, plain
    │ actually doing.                               │
    │ Now → March 2027                              │   ← dated window
    │ Mercury rules your 10th and sits there        │   ← the evidence:
    │ debilitated · Jupiter–Ketu period · score 32  │     planet + dasha
    │ ▸ What helps                                  │   ← remedy, if needed
    └──────────────────────────────────────────────┘

Four rules the card format enforces, which prose did not:

1. **Every claim is dated.** A prediction without a window is a horoscope.
2. **Every claim shows its planet and its period.** That is what separates
   this from "you will have an attractive face"; the reader can see the
   reasoning is specific to their chart.
3. **Nothing runs longer than a few lines.** If it cannot be said in three
   sentences, the reader was going to skim it anyway.
4. **An unfavourable card always carries an action.**

The confluence stays in the engine. It decides the verdict and supplies a
confidence chip — it is not something the customer should have to read.
"""

from __future__ import annotations

import html as _html
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

# ---------------------------------------------------------------------------
# life areas — named the way people think about their lives, not by house
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Area:
    key: str
    label: str
    house: int               # primary house
    support: tuple            # supporting houses
    subject: str              # how the claim refers to it


AREAS: tuple[Area, ...] = (
    Area("career", "Work & Career", 10, (6, 11), "your work"),
    Area("money", "Money", 2, (11,), "money"),
    Area("love", "Love & Marriage", 7, (5,), "your closest relationship"),
    Area("home", "Home & Family", 4, (2,), "home and family"),
    Area("children", "Children", 5, (9,), "children"),
    Area("health", "Health & Energy", 1, (6, 8), "your health"),
    Area("learning", "Learning & Luck", 9, (5,), "study and good fortune"),
    Area("inner", "Inner Life", 12, (9,), "your inner life"),
)

PLANET_VOICE = {
    "Sun": "recognition and authority",
    "Moon": "mood and the people close to you",
    "Mars": "drive, conflict and how hard you push",
    "Mercury": "communication, paperwork and negotiation",
    "Jupiter": "opportunity, teachers and expansion",
    "Venus": "goodwill, comfort and what you enjoy",
    "Saturn": "delay, discipline and what you earn slowly",
    "Rahu": "ambition and the unfamiliar",
    "Ketu": "detachment and what quietly falls away",
}

DIGNITY_WEIGHT = {
    "exalted": 2, "moolatrikona": 2, "own_sign": 1.5, "own sign": 1.5,
    "friendly_sign": 1, "friend": 1, "neutral_sign": 0, "neutral": 0,
    "enemy_sign": -1, "enemy": -1, "debilitated": -2,
}
DIGNITY_PLAIN = {
    "exalted": "at its strongest", "moolatrikona": "on its best ground",
    "own_sign": "in its own sign", "own sign": "in its own sign",
    "friendly_sign": "comfortably placed", "friend": "comfortably placed",
    "neutral_sign": "neutrally placed", "neutral": "neutrally placed",
    "enemy_sign": "on difficult ground", "enemy": "on difficult ground",
    "debilitated": "at its weakest",
}

# Claims, keyed (area, direction). Short, specific, and about the reader.
CLAIMS: dict[tuple[str, str], str] = {
    ("career", "up"): "Your work gets seen. This is a period where effort converts into position.",
    ("career", "mixed"): "The work is solid; the recognition is slower than the work. Both are true at once.",
    ("career", "down"): "Recognition lags behind what you are actually delivering. This is a build phase, not a reward phase.",
    ("money", "up"): "Money arrives more easily than usual, and more of it stays.",
    ("money", "mixed"): "Income holds, but it leaks. What you keep matters more than what you earn right now.",
    ("money", "down"): "Money is tight relative to the effort. Protect what exists before chasing more.",
    ("love", "up"): "Your closest relationship steadies and deepens through this stretch.",
    ("love", "mixed"): "Warmth is there, but so is friction. This is a period that rewards saying the awkward thing early.",
    ("love", "down"): "Distance shows up in your closest relationship — usually as silence rather than argument.",
    ("home", "up"): "Home becomes the steady base you work from.",
    ("home", "mixed"): "Home is mostly settled, with one recurring pull on your attention.",
    ("home", "down"): "Something at home takes more of you than you have been admitting.",
    ("children", "up"): "Children and creative work both go well — the same part of your chart runs them.",
    ("children", "mixed"): "Progress with children is real but uneven; patience does more than pressure.",
    ("children", "down"): "A worry about a child sits in the background of this period.",
    ("health", "up"): "Your energy holds well. Your body recovers faster than you expect.",
    ("health", "mixed"): "Energy is adequate but not abundant. Sleep is the variable that decides the rest.",
    ("health", "down"): "Your energy runs lower than your schedule assumes. This is the area to protect first.",
    ("learning", "up"): "Study, teachers and the right introductions all come easily now.",
    ("learning", "mixed"): "Opportunity comes, but through effort rather than luck.",
    ("learning", "down"): "Doors open slower than they should. Ask directly rather than waiting to be noticed.",
    ("inner", "up"): "You have unusual clarity about what actually matters to you.",
    ("inner", "mixed"): "A quiet restlessness runs under the surface of this period.",
    ("inner", "down"): "Rest is not optional in this stretch. Withdrawal is doing something, not avoiding it.",
}

ACTIONS: dict[str, str] = {
    "Sun": "Deal directly with whoever actually decides. This stalls one level below the authority.",
    "Moon": "Protect your sleep and your home routine — your focus is downstream of both.",
    "Mars": "Do not escalate this month. Let the other side move first.",
    "Mercury": "Put it in writing. The misunderstanding here is in the wording, not the intent.",
    "Jupiter": "Ask someone senior to speak for you. This opens through a sponsor.",
    "Venus": "Repair the relationship before pressing the request again.",
    "Saturn": "Finish the boring, verifiable part first. Saturn only blocks what is half-done.",
    "Rahu": "Verify the thing that looks too convenient.",
    "Ketu": "Step back for a fortnight. This one loosens when you stop gripping it.",
}

MANTRA = {
    "Sun": "Om Suryaya Namah at sunrise", "Moon": "Om Chandraya Namah on Mondays",
    "Mars": "Om Angarakaya Namah on Tuesdays", "Mercury": "Om Budhaya Namah on Wednesdays",
    "Jupiter": "Om Gurave Namah on Thursdays", "Venus": "Om Shukraya Namah on Fridays",
    "Saturn": "Om Sham Shanaishcharaya Namah on Saturdays",
    "Rahu": "Om Rahave Namah on Saturday evenings",
    "Ketu": "Om Ketave Namah on Tuesday evenings",
}


# ---------------------------------------------------------------------------

@dataclass
class Card:
    area: str
    label: str
    direction: str                 # up | mixed | down
    headline: str
    window: str
    evidence: list = field(default_factory=list)
    action: str = ""
    mantra: str = ""
    agreement: str = ""            # confluence, reduced to a chip
    locked: bool = False           # kept for callers that still gate whole cards


def _d(value: Any) -> Optional[date]:
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _pretty(d: Optional[date]) -> str:
    return f"{d:%b %Y}".replace(" 0", " ") if d else ""


def _window(start: Any, end: Any, today: Optional[date] = None) -> str:
    today = today or date.today()
    a, b = _d(start), _d(end)
    if not b:
        return ""
    if a and a <= today <= b:
        return f"Now → {_pretty(b)}"
    return f"{_pretty(a)} → {_pretty(b)}"


def current_ad(pc: dict) -> dict:
    for ad in (pc.get("vimshottari", {}).get("current_md_antardashas") or []):
        if ad.get("status") == "current":
            return ad
    return {}


def _dasha_touches(pc: dict, house: int, lords: list) -> bool:
    """Is the running period pointed at this house?"""
    hl = pc.get("house_lords", {})
    info = hl.get(str(house)) or {}
    planets = pc.get("planets", {})
    for lord in lords:
        if not lord:
            continue
        if info.get("lord") == lord:
            return True
        if (planets.get(lord) or {}).get("house") == house:
            return True
    return False


def score_area(pc: dict, area: Area) -> tuple:
    """Verdict for one life area — six methods voting, not one.

    Reading the house lord's dignity alone was the original approach, and on a
    real chart it produced a confidently wrong answer: Mercury debilitated
    reads as "recognition lags", while the neecha bhanga cancellation from
    exalted Venus classically inverts exactly that into strength. The vote is
    what catches it.
    """
    try:
        import report_confluence as CF
        verdict = CF.area_verdict(pc, area.key, area.house)
        evidence = [f"<b>{v.method.capitalize()}</b> — {v.because}"
                    for v in verdict["votes"]]
        return verdict["direction"], evidence, verdict["score"], verdict
    except Exception:
        pass

    # fall back to the single-method read rather than failing a report
    hl = pc.get("house_lords", {})
    info = hl.get(str(area.house)) or {}
    dignity = str(info.get("lord_dignity") or "").lower()
    score = DIGNITY_WEIGHT.get(dignity, 0.0)
    direction = "up" if score >= 1.5 else ("down" if score <= -1 else "mixed")
    lord = info.get("lord") or ""
    return direction, [f"<b>{lord}</b> rules this area"], score, {}


def _ord(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def build_cards(pc: dict, *, today: Optional[date] = None,
                free_areas: int = 0) -> list:
    """One card per life area, ordered so the sharpest reading leads."""
    today = today or date.today()
    vim = pc.get("vimshottari", {}) or {}
    md = vim.get("current_md", {}) or {}
    ad = current_ad(pc)
    md_lord, ad_lord = md.get("md_lord", ""), ad.get("ad_lord", "")
    period_line = (f"{md_lord}–{ad_lord} period" if md_lord and ad_lord
                   else f"{md_lord} period")
    window = _window(ad.get("start"), ad.get("end"), today) or \
        _window(md.get("start"), md.get("end"), today)

    cards = []
    for area in AREAS:
        direction, evidence, score, verdict = score_area(pc, area)
        live = _dasha_touches(pc, area.house, [md_lord, ad_lord])
        ev = list(evidence)
        ev.append(f"Running now: <b>{period_line}</b>"
                  + (" — and it points straight at this area"
                     if live else " — this area is not its main focus"))
        lord = (pc.get("house_lords", {}).get(str(area.house)) or {}).get("lord", "")
        card = Card(
            area=area.key, label=area.label, direction=direction,
            headline=CLAIMS.get((area.key, direction), ""),
            window=window, evidence=ev,
            action=ACTIONS.get(lord, "") if direction != "up" else "",
            mantra=MANTRA.get(lord, "") if direction == "down" else "",
            agreement=(verdict or {}).get("agreement", ""),
        )
        cards.append((abs(score) + (1 if live else 0), card))

    # sharpest and most active first — a reader should meet the strongest
    # statement about their life on line one, not the 1st house by convention
    cards.sort(key=lambda kv: -kv[0])
    ordered = [c for _, c in cards]
    # free_areas=0 is the default now: EVERY headline is free, and the paywall
    # sits on the dated window and the remedy inside each card. Locking whole
    # cards hid whichever areas the chart happened to speak loudest about —
    # on a test chart that meant Career was hidden and Children was free.
    # Seeing the whole picture and paying for "when" and "what to do" is both
    # a better hook and an honest one.
    for c in ordered[free_areas:] if free_areas else []:
        c.locked = True
    return ordered


def build_timeline(pc: dict, *, today: Optional[date] = None,
                   limit: int = 6) -> list:
    """The next few chapters, one line each, with real dates."""
    today = today or date.today()
    vim = pc.get("vimshottari", {}) or {}
    hl = pc.get("house_lords", {}) or {}
    planets = pc.get("planets", {}) or {}
    rows = []
    for ad in (vim.get("current_md_antardashas") or []):
        end = _d(ad.get("end"))
        if not end or end < today:
            continue
        lord = ad.get("ad_lord", "")
        houses = [int(h) for h, v in hl.items() if v.get("lord") == lord]
        sits = (planets.get(lord) or {}).get("house")
        areas = sorted({a.label for a in AREAS
                        if a.house in houses or a.house == sits
                        or any(h in a.support for h in houses)
                        or sits in a.support})
        rows.append({
            "window": _window(ad.get("start"), ad.get("end"), today),
            "lord": lord,
            "theme": PLANET_VOICE.get(lord, ""),
            "areas": areas[:3],
            "current": ad.get("status") == "current",
        })
        if len(rows) >= limit:
            break
    return rows


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


DIRECTION_LABEL = {"up": "favourable", "mixed": "mixed", "down": "under strain"}


def render(pc: dict, *, name: str = "", question_html: str = "",
           price: int = 1499, today: Optional[date] = None,
           paid: bool = False, proof_html: str = "",
           daily_html: str = "") -> str:
    today = today or date.today()
    cards = build_cards(pc, today=today)
    timeline = build_timeline(pc, today=today)
    vim = pc.get("vimshottari", {}) or {}
    md, ad = vim.get("current_md", {}) or {}, current_ad(pc)
    lagna = (pc.get("lagna") or {}).get("sign", "")
    moon = (pc.get("planets", {}).get("Moon") or {})
    first = (name or "").split()[0] if name else "You"

    # Three timing systems, not one. Vimshottari alone is a single opinion;
    # Yogini carries its own tone and Jaimini's sign periods move
    # independently. Agreement between them is the honest confidence signal.
    dasha_html = personality_html = ""
    try:
        import report_confluence as CF
        dc = CF.dasha_confluence(pc, today)
        rows = "".join(
            f'<div class="dsys"><span>{_e(r["system"])}</span>'
            f'<b>{_e(r["label"])}</b></div>' for r in dc["readings"])
        verdict = {"up": "All three are pointing the same way, and it is a "
                         "supportive way.",
                   "down": "The timing systems agree this is a demanding "
                           "stretch rather than an easy one.",
                   "mixed": "The systems do not fully agree here — which "
                            "usually means a period that rewards patience "
                            "over big moves."}[dc["direction"]]
        dasha_html = (f'<div class="dasha-conf">{rows}'
                      f'<div class="dagree">{_e(dc["agreement"])} · '
                      f'{_e(verdict)}</div></div>')

        pers = CF.personality(pc)
        traits = "".join(f"<li>{_e(t)}</li>" for t in pers["traits"])
        yogas = "".join(f"<li>{_e(y)}</li>" for y in pers["yogas"])
        personality_html = f"""
<h3 class="sec">Who your chart says you are</h3>
<p class="sec-note">Read this first. If it does not describe you, nothing
after it is worth your money.</p>
<div class="card persona">
  <ul class="traits">{traits}</ul>
  {f'<div class="yogas"><span class="ev-label">Standing combinations in your chart</span><ul>{yogas}</ul></div>' if yogas else ''}
</div>"""
    except Exception:
        pass

    def card_html(c: Card) -> str:
        # Evidence is shown, never hidden behind a toggle. It is the proof the
        # reading is computed from THIS chart rather than written for anyone —
        # collapsing it hides the one thing that separates us from a horoscope
        # column.
        ev = "".join(f"<li>{e}</li>" for e in c.evidence)

        if paid:
            when = f'<div class="when">{_e(c.window)}</div>'
            act = (f'<div class="action"><span class="act-label">What helps</span>'
                   f'<p>{_e(c.action)}</p>'
                   + (f'<p class="mantra">{_e(c.mantra)}</p>' if c.mantra else "")
                   + "</div>") if c.action else ""
        else:
            when = ('<div class="when locked-inline">'
                    '<span class="lockicon">•</span> Exact dates in the full reading</div>')
            act = ('<div class="action locked-inline">'
                   '<span class="act-label">What helps</span>'
                   '<p class="blurred">{}</p></div>'.format(_e(c.action))
                   ) if c.action else ""

        return f"""
<article class="card" data-verdict="{c.direction}">
  <div class="card-top"><span class="area">{_e(c.label)}</span>
    <span class="pill {c.direction}">{DIRECTION_LABEL[c.direction]}</span></div>
  <p class="claim">{_e(c.headline)}</p>
  {when}
  <div class="evidence">
    <span class="ev-label">Why your chart says this</span>
    {f'<span class="agree">{_e(c.agreement)}</span>' if c.agreement else ''}
    <ul>{ev}</ul></div>
  {act}
</article>"""

    tl = "".join(f"""
<li class="{'now' if r['current'] else ''}">
  <div class="tl-when">{_e(r['window'])}</div>
  <div class="tl-body"><b>{_e(r['lord'])}</b> — {_e(r['theme'])}
  {f'<span class="tl-areas">{_e(" · ".join(r["areas"]))}</span>' if r['areas'] else ''}</div>
</li>""" for r in timeline)

    cards_html = "".join(card_html(c) for c in cards)

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{_e(first)} — your reading</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet"/>
<style>
:root{{--ink:#16181d;--muted:#6a7080;--line:#e6e4df;--bg:#fbfaf8;
--up:#1c6b45;--down:#a3341f;--mixed:#8a6a1f;--card:#fff}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,system-ui,sans-serif;
line-height:1.55;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:640px;margin:0 auto;padding:0 20px 80px}}
header{{padding:44px 0 22px}}
.eyebrow{{font-size:.7rem;letter-spacing:.16em;text-transform:uppercase;
color:var(--muted);font-weight:600}}
h1{{font-family:Fraunces,Georgia,serif;font-size:2rem;line-height:1.12;
margin:10px 0 12px;font-weight:600;letter-spacing:-.015em}}
.chartline{{font-size:.86rem;color:var(--muted)}}
.now-box{{background:var(--ink);color:#f7f5f1;border-radius:14px;
padding:20px 22px;margin:22px 0 30px}}
.now-box .lbl{{font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;
opacity:.6;font-weight:600}}
.now-box h2{{font-family:Fraunces,serif;font-size:1.3rem;margin:8px 0 6px;font-weight:600}}
.now-box p{{margin:0;font-size:.9rem;opacity:.85}}
h3.sec{{font-family:Fraunces,serif;font-size:1.25rem;margin:38px 0 4px;font-weight:600}}
.sec-note{{font-size:.82rem;color:var(--muted);margin:0 0 16px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;
padding:18px 20px;margin-bottom:12px}}
.card-top{{display:flex;justify-content:space-between;align-items:center;gap:10px}}
.area{{font-size:.68rem;letter-spacing:.13em;text-transform:uppercase;
font-weight:600;color:var(--muted)}}
.pill{{font-size:.66rem;font-weight:600;padding:3px 9px;border-radius:99px;
letter-spacing:.04em}}
.pill.up{{background:#e4f2ea;color:var(--up)}}
.pill.down{{background:#fbeae6;color:var(--down)}}
.pill.mixed{{background:#fbf1de;color:var(--mixed)}}
.claim{{font-family:Fraunces,serif;font-size:1.12rem;line-height:1.4;
margin:12px 0 10px}}
.when{{font-size:.78rem;font-weight:600;color:var(--muted);
letter-spacing:.02em;margin-bottom:10px}}
details{{border-top:1px solid var(--line);padding-top:10px}}
summary{{font-size:.78rem;color:var(--muted);cursor:pointer;font-weight:500}}
details ul{{margin:10px 0 0;padding-left:18px;font-size:.85rem;color:#3d4250}}
details li{{margin:6px 0}}
.action{{margin-top:12px;background:#f6f4ef;border-radius:10px;padding:12px 14px}}
.act-label{{font-size:.66rem;letter-spacing:.13em;text-transform:uppercase;
font-weight:600;color:var(--mixed)}}
.action p{{margin:6px 0 0;font-size:.88rem}}
.mantra{{font-style:italic;color:var(--muted);font-size:.82rem!important}}
.blurred{{filter:blur(4.5px);user-select:none;opacity:.6}}
.locked-inline .lockicon{{color:var(--mixed);font-weight:700}}
.when.locked-inline{{color:var(--mixed);font-weight:600}}
.evidence{{border-top:1px solid var(--line);padding-top:10px;margin-top:4px}}
.ev-label{{font-size:.64rem;letter-spacing:.13em;text-transform:uppercase;
font-weight:600;color:var(--muted)}}
.agree{{float:right;font-size:.66rem;font-weight:600;color:var(--muted);
background:#f1efea;border-radius:99px;padding:2px 9px}}
.evidence ul{{margin:8px 0 0;padding-left:18px;font-size:.85rem;color:#3d4250}}
.evidence li{{margin:6px 0}}
.proof{{background:#fff;border:2px solid var(--ink);border-radius:14px;
padding:22px;margin:26px 0}}
.proof h3{{font-family:Fraunces,serif;font-size:1.22rem;margin:0 0 8px;font-weight:600}}
.proof p{{font-size:.9rem;margin:0 0 12px}}
.proof .hits{{list-style:none;margin:14px 0 0;padding:0}}
.proof .hits li{{display:flex;gap:10px;align-items:flex-start;padding:9px 0;
border-top:1px solid var(--line);font-size:.88rem}}
.proof .tick{{color:var(--up);font-weight:700}}
.proof .miss{{color:var(--muted);font-weight:700}}
.daily{{background:#f2efe9;border-radius:14px;padding:20px 22px;margin:26px 0}}
.daily .lbl{{font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;
font-weight:600;color:var(--muted)}}
.daily h3{{font-family:Fraunces,serif;font-size:1.16rem;margin:8px 0 10px;font-weight:600}}
.dodont{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:12px 0}}
@media(max-width:520px){{.dodont{{grid-template-columns:1fr}}}}
.dodont div{{background:#fff;border-radius:10px;padding:10px 12px;font-size:.84rem}}
.dodont .t{{font-size:.64rem;letter-spacing:.12em;text-transform:uppercase;
font-weight:600;margin-bottom:5px}}
.do .t{{color:var(--up)}} .dont .t{{color:var(--down)}}
.windows{{list-style:none;margin:10px 0 0;padding:0;font-size:.85rem}}
.windows li{{display:flex;gap:10px;padding:6px 0;border-top:1px solid #e0dcd4}}
.windows b{{min-width:96px;font-variant-numeric:tabular-nums}}
.dasha-conf{{margin-top:14px;border-top:1px solid rgba(255,255,255,.18);
padding-top:12px}}
.dsys{{display:flex;justify-content:space-between;font-size:.82rem;
padding:3px 0;opacity:.9}}
.dsys span{{opacity:.65}}
.dagree{{margin-top:9px;font-size:.8rem;opacity:.8}}
.persona .traits{{list-style:none;margin:0;padding:0}}
.persona .traits li{{font-family:Fraunces,serif;font-size:1.02rem;
line-height:1.45;padding:9px 0;border-bottom:1px solid var(--line)}}
.persona .traits li:last-child{{border-bottom:0}}
.yogas{{margin-top:12px;background:#f6f4ef;border-radius:10px;padding:12px 14px}}
.yogas ul{{margin:8px 0 0;padding-left:18px;font-size:.84rem}}
ol.timeline{{list-style:none;margin:0;padding:0;border-left:2px solid var(--line)}}
ol.timeline li{{position:relative;padding:0 0 20px 20px}}
ol.timeline li::before{{content:"";position:absolute;left:-7px;top:5px;width:12px;
height:12px;border-radius:50%;background:#fff;border:2px solid var(--line)}}
ol.timeline li.now::before{{background:var(--ink);border-color:var(--ink)}}
.tl-when{{font-size:.74rem;font-weight:600;color:var(--muted);letter-spacing:.03em}}
.tl-body{{font-size:.92rem;margin-top:2px}}
.tl-areas{{display:block;font-size:.78rem;color:var(--muted);margin-top:2px}}
.buy{{background:var(--ink);color:#f7f5f1;border-radius:14px;padding:24px;
margin-top:32px;text-align:center}}
.buy h3{{font-family:Fraunces,serif;font-size:1.2rem;margin:0 0 8px;font-weight:600}}
.buy p{{font-size:.88rem;opacity:.85;margin:0 0 16px}}
.buy .cta{{display:inline-block;background:#f7f5f1;color:var(--ink);
padding:12px 26px;border-radius:99px;font-weight:600;font-size:.9rem;
text-decoration:none}}
footer{{margin-top:40px;font-size:.74rem;color:var(--muted);text-align:center}}
</style></head><body><div class="wrap">
<header>
  <div class="eyebrow">Your reading</div>
  <h1>{_e(first)}, here is what your chart<br/>is doing right now.</h1>
  <div class="chartline">{_e(lagna)} rising · Moon in {_e(moon.get('sign',''))}
  ({_e(moon.get('nakshatra',''))}) · read {today:%d %B %Y}</div>
</header>

<div class="now-box">
  <div class="lbl">The chapter you are in</div>
  <h2>{_e(md.get('md_lord',''))}–{_e(ad.get('ad_lord',''))},
      to {_e(_pretty(_d(ad.get('end'))))}</h2>
  <p>{_e(PLANET_VOICE.get(md.get('md_lord',''),''))} sets the background;
     {_e(PLANET_VOICE.get(ad.get('ad_lord',''),''))} is what you are feeling week to week.</p>
  {dasha_html}
</div>

{personality_html}

{proof_html}
{daily_html}
<h3 class="sec">What this period is doing to each part of your life</h3>
<p class="sec-note">Ordered by how strongly your chart speaks — not by convention.</p>
{cards_html}

<h3 class="sec">What comes next</h3>
<p class="sec-note">Your own timing sequence, with real dates.</p>
<ol class="timeline">{tl}</ol>

{question_html}

<div class="buy">
  <h3>Unlock the full reading</h3>
  <p>Every life area above, the dated windows for each, and the remedies
  matched to your chart.</p>
  <a class="cta" href="#unlock">Unlock — ₹{price}</a>
</div>
<footer>Calculated from your birth details alone · guidance, not a substitute
for professional advice</footer>
</div></body></html>"""
