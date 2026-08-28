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

PRACTICAL_HINGLISH = {
    "Sun": "Faisla lene wale senior authority person se direct baat karein.",
    "Moon": "Pehle apni neend aur ghar ki routine ko protect karein — aapka mood aur decision making dono isi par depend karte hain.",
    "Mars": "Ek mahine ke liye kisi bhi tarah ke vivaad ya escalation se bachein aur doosre paksh ko pehle kadam uthane dein.",
    "Mercury": "Mahatvapurna baaton ko likh kar rakhein aur bhejne se pehle dobara padhein.",
    "Jupiter": "Kisi anubhavi ya varishth vyakti se margdarshan lein. Yeh sthiti prayas ke sath sahi sahyog se khulti hai.",
    "Venus": "Kisi anurodh ya baat ko aage badhane se pehle sambandho mein aapsi samajh ko theek karein.",
    "Saturn": "Boring lekin zaroori kaam pehle poora karein. Shani keval adhure kaamon mein rukawat dalte hain.",
    "Rahu": "Jo cheez bohot aasan ya convenient lage, uski pehle achhe se pushti karein.",
    "Ketu": "Thode samay ke liye cheezon ko zabardasti karna band karein; yeh tab aage badhti hain jab aap pressure kam karte hain.",
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

WEAR_LABEL_HINGLISH = {
    "recommended": ("Aapki kundli ke liye anukool", "up"),
    "test_required": ("Keval trial wear ke liye", "trial"),
    "mantra_only": ("Yeh ratna na pehnein. Iski jagah mantra ka upyog karein", "down"),
    "avoid": ("Yeh ratna bilkul na pehnein", "down"),
}


def _dig_plain(code: str) -> str:
    key = (code or "").strip().lower()
    return _DIGNITY_PLAIN.get(key, key.replace("_", " "))


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def build(pc: dict, *, domain: str = "", question: str = "",
          name: str = "", question_scoped: bool = False,
          lang: str = "en") -> dict:
    """Gemstone safety plus the practical action, for one chart."""
    try:
        from gemstone_remedy import build_remedy_report
        rep = build_remedy_report(pc, client_name=name, domain=domain,
                                  question=question,
                                  question_scoped=question_scoped)
    except Exception:
        rep = {}

    wear = list(rep.get("primary_wear") or [])
    mantra_only = list(rep.get("mantra_only") or [])
    avoid = list(rep.get("avoid") or [])

    # Chart-level "start here" tip follows the running period lord.
    dasha = rep.get("dasha") or {}
    lord = dasha.get("ad_lord") or dasha.get("md_lord") or ""
    try:
        from interpretation.life_stage import age_band as _ab
        band = _ab(pc)
    except Exception:  # noqa: BLE001
        band = "adult"
    
    is_hinglish = str(lang or "").lower() in ("hi_en", "hinglish", "hi", "hindi")
    practical_txt = PRACTICAL_HINGLISH.get(lord, "") if is_hinglish else practical_remedy(lord, band)
    if not practical_txt:
        practical_txt = practical_remedy(lord, band)

    return {"wear": wear, "mantra_only": mantra_only, "avoid": avoid,
            "practical_planet": lord,
            "practical": practical_txt,
            "lagna_lord": rep.get("lagna_lord", ""),
            "ok": bool(rep.get("ok", True)),
            "lang": lang}


def _free_avoid_reason(item: dict, is_hinglish: bool = False) -> str:
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

    if is_hinglish:
        if house in (6, 8, 12) or "pressure house" in joined:
            return f"{planet} aapki kundli ke sensitive bhav se jude hain, isliye yeh ratna pehanna varjit hai."
        if "overheat" in joined or "strong malefic" in joined:
            return f"{planet} aapki kundli mein pehle se forceful hain; yeh ratna pehanne se unka prabhav ugra ho sakta hai."
        if "debilitat" in joined or dig == "debilitated":
            return f"{planet} kundli mein kamzor sthiti mein hain, isliye ratna ki jagah mantra aur daan adhik surakshit hain."
        if planet in ("Rahu", "Ketu") or "not advised unless" in joined:
            return f"Yeh {planet}-sambandhit ratna bina anukool dasha ke pehanna uchit nahi hai."
        return f"Aapki kundli mein {planet} ki sthiti ke anusar yeh ratna pehanna anukool nahi hai."

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


def _stone_row(item: dict, *, paid: bool = False, is_hinglish: bool = False) -> str:
    gem = item.get("gem") or {}
    verdict = str(item.get("verdict") or "")
    labels_dict = WEAR_LABEL_HINGLISH if is_hinglish else WEAR_LABEL
    label, tone = labels_dict.get(verdict, ("Jyotish paramarsh aavashyak" if is_hinglish else "Check with an astrologer", "mixed"))
    reasons = item.get("reasons") or []
    snap = item.get("snap") or {}
    detail = ""
    if verdict in ("recommended", "test_required"):
        if is_hinglish:
            detail = f"Dhaatu: {_e(gem.get('metal'))} · Ungli: {_e(gem.get('finger'))} · Shuru Din: {_e(gem.get('day'))}"
        else:
            detail = f"Metal: {_e(gem.get('metal'))} · Finger: {_e(gem.get('finger'))} · Start day: {_e(gem.get('day'))}"
    why = ""
    role_html = ""
    if paid:
        role_bits = []
        if item.get("role"):
            try:
                from gemstone_remedy import _customer_role_label
                role_bits.append(_customer_role_label(str(item.get("role"))))
            except Exception:
                role_bits.append("Kundli Indicator" if is_hinglish else "Relevant chart indicator")
        if snap.get("planet") and not role_bits:
            role_bits.append(f"{snap.get('planet')} is relevant" if not is_hinglish else f"{snap.get('planet')} is upay se sambandhit hain")
        if role_bits:
            role_html = f'<div class="stone-role">{_e(". ".join(role_bits))}</div>'
        if reasons:
            why_label = "Karan" if is_hinglish else "Why"
            reason_text = str(reasons[0])
            try:
                from qa_checks.customer_text_sanitizer import sanitize_customer_text
                reason_text = sanitize_customer_text(
                    reason_text, area="", direction="caution" if verdict in ("avoid", "mantra_only") else "support",
                    method_label="Remedy evidence", seed=reason_text[:48])
            except Exception:
                pass
            why = (f'<div class="stone-why"><b>{why_label}:</b> '
                   f'{_e(reason_text)}</div>')
    else:
        # Free refusals
        if verdict in ("avoid", "mantra_only") or reasons:
            why = f'<div class="stone-why">{_e(_free_avoid_reason(item, is_hinglish=is_hinglish))}</div>'
    
    if is_hinglish:
        alt_label = "Mantra Aur Daan" if verdict in ("avoid", "mantra_only") else "Dainik Mantra Aur Puja"
    else:
        alt_label = "Immediate relief (Mantra & charity)" if verdict in ("avoid", "mantra_only") else "Daily strengthening mantra & offering"
    
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
                  paid: bool = False, is_hinglish: bool = False) -> str:
    if not items:
        return ""
    return f"""
  <div class="stones-group {tone}">
    <div class="stones-group-label">{_e(label)}</div>
    <ul class="stones">{''.join(_stone_row(st, paid=paid, is_hinglish=is_hinglish) for st in items)}</ul>
  </div>"""


def render(block: dict, *, paid: bool = False, price: int = 0,
           heading: str = "",
           lede: str = "",
           lang: str = "en") -> str:
    if not block:
        return ""
    avoid = block.get("avoid") or []
    mantra_only = block.get("mantra_only") or []
    wear = block.get("wear") or []
    practical = block.get("practical")
    is_hinglish = str(lang or block.get("lang") or "").lower() in ("hi_en", "hinglish", "hi", "hindi")

    if not heading:
        heading = "Aapke Liye Upay Aur Rashi Ratna" if is_hinglish else "What you can actually do about it"
    if not lede:
        if is_hinglish:
            lede = "Jin kshetron mein savdhani ki aavashyakta hai, wahan dainik vyavaharik aadat, mantra, daan aur anukool ratna se sahyog liya jata hai. Jo ratna varjit hain unhe pehanna mana hota hai."
        else:
            lede = ("For the areas that need more care, the traditional approach is to "
                    "support them through practical habits, mantra, charity and — where "
                    "appropriate — gemstones.")

    if paid:
        do_block = ""
        if practical:
            do_lbl = "Dainik Vyavaharik Upay · Sabse Pehle Karein" if is_hinglish else "Do this first · no belief required"
            do_block = f"""
  <div class="remedy-do">
    <div class="remedy-do-label">{do_lbl}</div>
    <p>{_e(practical)}</p>
  </div>"""
        safe = [w for w in wear if str(w.get("verdict") or "") == "recommended"]
        trial = [w for w in wear if str(w.get("verdict") or "") == "test_required"]
        other = [w for w in wear
                 if str(w.get("verdict") or "") not in ("recommended", "test_required")]
        
        w_lbl = "Anukool Grah · Shubh Rashi Ratna Aur Grah Bal" if is_hinglish else "Supporting planets · Auspicious gemstone & strengthening"
        t_lbl = "Secondary Grah Sahyog · Pehle Trial Wear Karein" if is_hinglish else "Secondary planetary support · Trial wear first"
        a_lbl = "Varjit Grah · Turant Rahat (Mantra Aur Daan)" if is_hinglish else "Obstructing & friction planets · Immediate relief (mantra & charity)"

        wear_group = _stones_group(
            safe + other, tone="up", paid=True, is_hinglish=is_hinglish,
            label=w_lbl)
        trial_group = _stones_group(
            trial, tone="trial", paid=True, is_hinglish=is_hinglish,
            label=t_lbl)
        avoid_group = _stones_group(
            list(mantra_only) + list(avoid), tone="down", paid=True, is_hinglish=is_hinglish,
            label=a_lbl)
        
        fine_text = (
            "Upay kundli ki sthiti ko zabardasti badalne ke liye nahi balki sahi samay par uchit disha aur sakaratmak urja pane ke liye hote hain."
            if is_hinglish else
            "A remedy is not a lever that overrides the chart. It works the way preparation works — it changes what you are ready for when the timing turns. If you choose a trial approach, follow the specific trial period shown for that stone before deciding whether to continue."
        )

        return f"""
<section class="remedy-card">
  <div class="ev-label">{_e(heading)}</div>
  {f'<p class="remedy-lede">{_e(lede)}</p>' if lede else ''}
  {do_block}
  {wear_group}
  {trial_group}
  {avoid_group}
  <p class="fine">{fine_text}</p>
</section>"""

    # --- free view: refusals only ------------------------------------------
    refused = avoid + mantra_only
    helpful_count = len(wear)

    if not refused:
        if is_hinglish:
            body = f"""
  <p class="remedy-lede">Aapki kundli mein kisi bhi rashi ratna se koi hani nahi hai — yeh shubh sanket hai.</p>
  <div class="remedy-locked">
    <b>{helpful_count} ratna aapki kundli ke liye anukool hain</b>, dhaatu, ungli, pehanne ka din aur zaroori vyavaharik kadam full reading mein shamil hain.
  </div>"""
        else:
            body = f"""
  <p class="remedy-lede">Nothing in your chart is actively harmed by a
  gemstone — which is less common than you would think, and good news.</p>
  <div class="remedy-locked">
    <b>{helpful_count} stone{'s' if helpful_count != 1 else ''} assessed as
    suitable for you</b>, with metal, finger and the day to begin, plus the
    practical steps that matter more than any of them.
  </div>"""
    else:
        if is_hinglish:
            body = f"""
  <p class="remedy-lede">Ratna pehanne se pehle, yeh dekhein ki aapki kundli ke anusar kya varjit hai.</p>
  {_stones_group(refused, tone="down", paid=False, is_hinglish=is_hinglish,
                 label="Yeh ratna na pehnein · aapki kundli se spasht hai")}
  <div class="remedy-locked">
    <b>Hum yeh hissa isliye dikha rahe hain kyunki kya nahi pehanna chahiye yeh janna utna hi zaroori hai.</b>
    {helpful_count} ratna aapki kundli ke anukool hain — metal, ungli, din, mantra aur daan ke sath poori reading mein uplabdh hain.
  </div>"""
        else:
            body = f"""
  <p class="remedy-lede">Before we suggest anything to wear, here is what your
  chart says to avoid.</p>
  {_stones_group(refused, tone="down", paid=False, is_hinglish=is_hinglish,
                 label="Do not wear · already clear from your chart")}
  <div class="remedy-locked">
    <b>We are showing this part for free because knowing what not to use is
    just as important.</b>
    {helpful_count} stone{'s' if helpful_count != 1 else ''} came back suitable
    for your chart — with the metal, the finger, the day to begin and the trial
    period — alongside the mantras, the charity, and the practical action that
    matters more than any stone.
  </div>"""

    free_ev_label = "Rashi Ratna — Kya Na Pehnein (Nishulk)" if is_hinglish else "Gemstones — what is wrong for you, free"
    free_fine = "Rashi ratna hamesha vyaktigat kundli ke adhar par lena chahiye, keval rashi ke adhar par nahi." if is_hinglish else "A gemstone should be considered from your individual chart, not simply from your zodiac sign."

    return f"""
<section class="remedy-card">
  <div class="ev-label">{free_ev_label}</div>
  {body}
  <p class="fine">{free_fine}</p>
</section>"""
