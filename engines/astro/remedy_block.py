"""Remedies and gemstones, wherever the reading turns difficult.

A prediction that closes on "this will be hard" and stops there is bad product
and worse ethics. Someone paying for a reading is usually paying because they
are worried, and the thing they actually want is something to *do*. That is
what a remedy is for.

Two rules keep this honest rather than exploitative:

1. **What not to wear is as important as what to wear.** The gemstone engine
   already refuses stones classically contraindicated for a chart — on the test
   chart it blocks Yellow Sapphire outright, because Jupiter rules the 8th and
   is debilitated there. Saying "do not wear this, here is a mantra instead" is
   the single most credible thing a remedy section can do, because it is the
   opposite of an upsell.

2. **Practical action comes before ritual.** Every block leads with something
   the reader can do on Monday morning that would help even if they believe
   none of this. The traditional remedy follows it, not the reverse.

Hope, not fear. No remedy here is framed as averting disaster — that is the
oldest trick in the trade and it is the reason people distrust astrologers.
"""

from __future__ import annotations

import html as _html
from typing import Any, Optional


def _ord(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    return f"{n}" + ("th" if 10 <= n % 100 <= 20
                     else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


PRACTICAL = {
    "Sun": "Take it to the person who can actually decide. This stalls one level below the authority.",
    "Moon": "Protect your sleep and the routine at home first — your judgement is downstream of both.",
    "Mars": "Stop escalating for one month and let the other side move first.",
    "Mercury": "Put it in writing, then re-read what you already sent.",
    "Jupiter": "Ask one senior person to speak for you. This opens through a sponsor, not through effort.",
    "Venus": "Repair the relationship before you press the request again.",
    "Saturn": "Finish the dull, verifiable part first. Saturn only blocks what is half-done.",
    "Rahu": "Verify the thing that looks too convenient.",
    "Ketu": "Loosen your grip for a fortnight. This one moves when you stop forcing it.",
}

STAGE_PRACTICAL: dict[str, dict[str, str]] = {
    "Sun": {
        "child": "Show consistent effort on something you care about and ask a teacher or parent for feedback.",
        "teen": "Put your name on work that matters — ask a teacher or mentor to notice your effort.",
    },
    "Moon": {
        "child": "Protect sleep and routine at home first — judgement follows from both.",
        "teen": "Protect sleep and home routine first — your mood follows from both.",
    },
    "Mars": {
        "child": "Finish what you started before trying to win an argument.",
        "teen": "Finish what you started before escalating — patience often works better than force.",
    },
    "Mercury": {
        "child": "Write down what you need to remember and check it twice before acting.",
        "teen": "Put important plans in writing and re-read before you send or commit.",
    },
    "Jupiter": {
        "child": "Ask a parent, teacher or trusted adult for guidance. This opens through support, not shortcuts.",
        "teen": "Ask a teacher, mentor or parent for guidance. This opens through experienced support.",
        "young_adult": "Ask a mentor or experienced person for guidance. This opens through sponsorship, not effort alone.",
        "senior": "Use the support of experienced family members or trusted advisors.",
    },
    "Venus": {
        "child": "Clear up a misunderstanding with a friend or family member before pressing for what you want.",
        "teen": "Clear up a misunderstanding with a friend or close peer before pressing for what you want.",
        "young_adult": "Repair goodwill in the relationship before you press the request again.",
        "senior": "Protect companionship through patient, clear conversation before pressing a request.",
    },
    "Saturn": {
        "child": "Finish the steady part of a task carefully — half-done work is harder to recover.",
        "teen": "Finish the verifiable part of school or project work before expecting recognition.",
        "young_adult": "Finish the dull, verifiable part first. Progress follows completion, not hype.",
    },
    "Rahu": {
        "child": "Check with a trusted adult before acting on something that looks too easy.",
        "teen": "Verify what looks too convenient before you commit time or reputation to it.",
    },
    "Ketu": {
        "child": "Take a short break from pushing — some things move when you stop forcing them.",
        "teen": "Step back for a week rather than grip harder — not every battle needs fighting now.",
    },
}


def practical_remedy(planet: str, band: str = "adult") -> str:
    by_planet = STAGE_PRACTICAL.get(planet) or {}
    return by_planet.get(band) or PRACTICAL.get(planet, "")

WEAR_LABEL = {
    "recommended": ("Considered suitable for your chart", "up"),
    "test_required": ("Trial wear only", "trial"),
    "mantra_only": ("Do not wear this stone. Use mantra instead", "down"),
    "avoid": ("Do not wear this stone", "down"),
}

_DIGNITY_PLAIN = {
    "exalted": "very strong",
    "moolatrikona": "on its best ground",
    "own_sign": "in its own sign",
    "friendly_sign": "comfortably placed",
    "neutral_sign": "neither strong nor weak",
    "enemy_sign": "under strain",
    "debilitated": "very weak",
}


def _dig_plain(code: str) -> str:
    key = (code or "").strip().lower()
    return _DIGNITY_PLAIN.get(key, key.replace("_", " "))


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def build(pc: dict, *, domain: str = "", question: str = "",
          name: str = "") -> dict:
    """Gemstone safety plus the practical action, for one chart."""
    try:
        from gemstone_remedy import build_remedy_report
        rep = build_remedy_report(pc, client_name=name, domain=domain,
                                  question=question)
    except Exception:
        rep = {}

    wear = list(rep.get("primary_wear") or [])
    mantra_only = list(rep.get("mantra_only") or [])
    avoid = list(rep.get("avoid") or [])

    # Chart-level "start here" tip follows the running period lord.
    # Per-area cards must NOT reuse this — see area_report.classical_area_remedy.
    dasha = rep.get("dasha") or {}
    lord = dasha.get("ad_lord") or dasha.get("md_lord") or ""
    try:
        from interpretation.life_stage import age_band as _ab
        band = _ab(pc)
    except Exception:  # noqa: BLE001
        band = "adult"
    return {"wear": wear, "mantra_only": mantra_only, "avoid": avoid,
            "practical_planet": lord,
            "practical": practical_remedy(lord, band),
            "lagna_lord": rep.get("lagna_lord", ""),
            "ok": bool(rep.get("ok", True))}


def _free_avoid_reason(item: dict) -> str:
    """Human Free-report language for gemstone refusals (no house/lord jargon)."""
    snap = item.get("snap") or {}
    planet = (snap.get("planet") or item.get("planet")
              or (item.get("gem") or {}).get("planet") or "This planet")
    dig = (snap.get("dignity") or "").lower().replace(" ", "_")
    try:
        house = int(snap.get("house") or 0)
    except (TypeError, ValueError):
        house = 0
    joined = " ".join(str(r) for r in (item.get("reasons") or [])).lower()

    if house in (6, 8, 12) or "pressure house" in joined:
        return (f"{planet} is strongly connected with a sensitive area of your "
                f"chart, so this stone is not recommended for you.")
    if "overheat" in joined or "strong malefic" in joined:
        return (f"{planet} is already forceful in your chart; wearing this stone "
                f"can increase that pressure rather than ease it.")
    if "debilitat" in joined or dig == "debilitated":
        return (f"{planet} is under strain in your chart, so mantra and charity "
                f"are safer here than wearing this stone.")
    if planet in ("Rahu", "Ketu") or "not advised unless" in joined:
        return (f"This {planet}-linked stone is not advised for your chart without "
                f"clearly supportive timing.")
    if "12th" in joined or house == 12:
        return (f"{planet} sits in an area of your chart that favours rest and "
                f"release, so this stone is not recommended.")
    return (f"Based on how {planet} sits in your chart, this stone is not "
            f"recommended for you.")


def _stone_row(item: dict, *, paid: bool = False) -> str:
    gem = item.get("gem") or {}
    verdict = str(item.get("verdict") or "")
    label, tone = WEAR_LABEL.get(verdict, ("Check with an astrologer", "mixed"))
    reasons = item.get("reasons") or []
    snap = item.get("snap") or {}
    detail = ""
    if verdict in ("recommended", "test_required"):
        detail = (f"Metal: {_e(gem.get('metal'))} · Finger: {_e(gem.get('finger'))} · "
                  f"Start day: {_e(gem.get('day'))}")
    why = ""
    role_html = ""
    if paid:
        role_bits = []
        if item.get("role"):
            role_bits.append(str(item.get("role")))
        if snap:
            role_bits.append(
                f"{snap.get('planet')} in your {_ord(snap.get('house'))} house, "
                f"{_dig_plain(snap.get('dignity', ''))}")
        if role_bits:
            role_html = f'<div class="stone-role">{_e(". ".join(role_bits))}</div>'
        if reasons:
            why_label = ("Technical reason"
                         if verdict in ("avoid", "mantra_only") else "Why")
            why = (f'<div class="stone-why"><b>{why_label}:</b> '
                   f'{_e(reasons[0])}</div>')
    else:
        # Free refusals: keep the verdict, drop lord/house mechanics.
        if verdict in ("avoid", "mantra_only") or reasons:
            why = f'<div class="stone-why">{_e(_free_avoid_reason(item))}</div>'
    alt_label = "If you choose not to wear it / alongside"
    if verdict in ("avoid", "mantra_only"):
        alt_label = "Instead"
    return f"""
  <li class="stone {tone}" data-verdict="{tone}">
    <div class="stone-top">
      <b>{_e(gem.get('gem'))}</b>
      <span class="stone-verdict">{_e(label)}</span>
    </div>
    {role_html}
    {f'<div class="stone-detail">{detail}</div>' if detail else ''}
    {why}
    <div class="stone-alt"><b>{alt_label}:</b>
      {_e(gem.get('mantra'))}{f" · {_e(gem.get('charity'))}" if gem.get('charity') else ""}</div>
  </li>"""


def _stones_group(items: list, *, tone: str, label: str,
                  paid: bool = False) -> str:
    if not items:
        return ""
    return f"""
  <div class="stones-group {tone}">
    <div class="stones-group-label">{_e(label)}</div>
    <ul class="stones">{''.join(_stone_row(st, paid=paid) for st in items)}</ul>
  </div>"""


def render(block: dict, *, paid: bool = False, price: int = 0,
           heading: str = "What you can actually do about it",
           lede: str = "") -> str:
    """Remedies are paid. The refusals are free, and they do the selling.

    Operator's call and it is the sharper play: telling someone which stone is
    *wrong* for them costs us nothing and proves we are not just moving
    inventory. Every jeweller in the country will sell a Gemini a yellow
    sapphire; being the one who says "not you, not this stone, and here is the
    classical reason" is the whole trust argument in one paragraph.

    So the free view shows only the avoid list. The stones that would help, the
    metal, the finger, the day to begin, and the practical action all sit behind
    the paywall.

    Wear / do items are always in a green block; avoid / do-not-wear items in a
    red block — never interleaved in one list.
    """
    if not block:
        return ""
    avoid = block.get("avoid") or []
    mantra_only = block.get("mantra_only") or []
    wear = block.get("wear") or []
    practical = block.get("practical")

    if paid:
        do_block = ""
        if practical:
            do_block = f"""
  <div class="remedy-do">
    <div class="remedy-do-label">Do this first · no belief required</div>
    <p>{_e(practical)}</p>
  </div>"""
        safe = [w for w in wear if str(w.get("verdict") or "") == "recommended"]
        trial = [w for w in wear if str(w.get("verdict") or "") == "test_required"]
        # Any other wear verdicts (defensive) stay with safe list styling.
        other = [w for w in wear
                 if str(w.get("verdict") or "") not in ("recommended", "test_required")]
        wear_group = _stones_group(
            safe + other, tone="up", paid=True,
            label="Gemstones · considered suitable for your chart")
        trial_group = _stones_group(
            trial, tone="trial", paid=True,
            label="Gemstones · trial first (caution)")
        avoid_group = _stones_group(
            list(mantra_only) + list(avoid), tone="down", paid=True,
            label="Do not wear · mantra and charity instead")
        return f"""
<section class="remedy-card">
  <div class="ev-label">{_e(heading)}</div>
  {f'<p class="remedy-lede">{_e(lede)}</p>' if lede else ''}
  {do_block}
  {wear_group}
  {trial_group}
  {avoid_group}
  <p class="fine">A remedy is not a lever that overrides the chart. It works the
  way preparation works — it changes what you are ready for when the timing
  turns. If you choose a trial approach, follow the specific trial period
  shown for that stone before deciding whether to continue.</p>
</section>"""

    # --- free view: refusals only ------------------------------------------
    refused = avoid + mantra_only
    helpful_count = len(wear)

    if not refused:
        # Nothing is contraindicated, which is itself worth saying.
        body = f"""
  <p class="remedy-lede">Nothing in your chart is actively harmed by a
  gemstone — which is less common than you would think, and good news.</p>
  <div class="remedy-locked">
    <b>{helpful_count} stone{'s' if helpful_count != 1 else ''} assessed as
    suitable for you</b>, with metal, finger and the day to begin, plus the
    practical steps that matter more than any of them.
  </div>"""
    else:
        body = f"""
  <p class="remedy-lede">Before we suggest anything to wear, here is what your
  chart says to avoid.</p>
  {_stones_group(refused, tone="down", paid=False,
                 label="Do not wear · already clear from your chart")}
  <div class="remedy-locked">
    <b>We are showing this part for free because knowing what not to use is
    just as important.</b>
    {helpful_count} stone{'s' if helpful_count != 1 else ''} came back suitable
    for your chart — with the metal, the finger, the day to begin and the trial
    period — alongside the mantras, the charity, and the practical action that
    matters more than any stone.
  </div>"""

    return f"""
<section class="remedy-card">
  <div class="ev-label">Gemstones — what is wrong for you, free</div>
  {body}
  <p class="fine">A gemstone should be considered from your individual chart,
  not simply from your zodiac sign.</p>
</section>"""
