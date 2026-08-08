#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Question engine  -  semantic routing + live multi-technique confluence.

Maps any client question to life domain + bhavas (1-12), runs applicable
prediction techniques from the natal chart, and synthesizes one plain-English
verdict (not guesswork from a single dasha).
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable

from astro_precompute import (
    SIGNS,
    SIGN_LORDS,
    get_dignity,
    house_from_lagna,
    house_sign,
    resolve_precompute,
)

# Reuse horary topic vocabulary (litigation, recovery, disease_cure, etc.)
try:
    from horary_precompute import TOPIC_BHAVAS, TOPIC_KEYWORDS, detect_topic
except ImportError:
    TOPIC_BHAVAS = {}
    TOPIC_KEYWORDS = {}
    detect_topic = lambda q: "general"  # noqa: E731

GOEL_SOURCE = "rules8 (Goel Chara & Yogini)"
KP_SOURCE = "rules21 (Ravichandran KP timing)"
GATE_PCT = 0.75

DOMAIN_TITLE = {
    "career": "Career & Profession",
    "finance": "Finance & Wealth",
    "marriage": "Spouse & Marriage",
    "children": "Children & Family",
    "health": "Health & Recovery",
    "property": "Property & Home",
    "travel": "Travel & Foreign",
    "spiritual": "Spiritual Life",
    "legal": "Legal & Disputes",
    "speech": "Speech & Communication",
    "education": "Education",
    "general": "Your Question",
}

TOPIC_TO_DOMAIN = {
    "disease": "health",
    "disease_cure": "health",
    "recovery": "health",
    "litigation": "legal",
    "job": "career",
    "children": "children",
    "marriage": "marriage",
    "career": "career",
    "health": "health",
    "finance": "finance",
    "travel": "travel",
    "education": "education",
    "property": "property",
    "general": "general",
}

# Natural-language hooks ? primary house (Parashari)
HOUSE_KEYWORDS: dict[int, list[str]] = {
    1: ["body", "vitality", "appearance", "personality", "face", "head", "self", "identity"],
    2: ["speech", "stammer", "stutter", "voice", "teeth", "eyes", "vision", "wealth", "savings", "family money", "food"],
    3: ["sibling", "brother", "sister", "courage", "skill", "writing", "media", "short travel", "communication"],
    4: ["mother", "home", "house", "property", "land", "vehicle", "comfort", "peace of mind"],
    5: ["child", "children", "pregnancy", "creativity", "romance", "education", "intelligence", "speculation"],
    6: ["disease", "illness", "sick", "hospital", "surgery", "enemy", "litigation", "court", "legal", "case", "debt", "service"],
    7: ["spouse", "marriage", "husband", "wife", "partner", "divorce", "business partner", "open enemy"],
    8: ["accident", "surgery", "inheritance", "chronic", "longevity", "hidden", "scandal", "insurance"],
    9: ["father", "guru", "luck", "fortune", "dharma", "religion", "long journey", "higher study", "visa"],
    10: ["career", "job", "promotion", "profession", "boss", "status", "fame", "government",
         "hike", "raise", "increment", "appraisal", "salary"],
    11: ["income", "gains", "wish", "friend", "network", "profit", "bonus"],
    12: ["loss", "expense", "foreign", "abroad", "hospitalization", "sleep", "isolation", "spiritual retreat"],
}

# Natural karakas for house themes (Parashari)
HOUSE_KARAKAS: dict[int, list[str]] = {
    1: ["Sun"],
    2: ["Mercury", "Jupiter"],
    3: ["Mars"],
    4: ["Moon", "Mars"],
    5: ["Jupiter"],
    6: ["Mars", "Saturn"],
    7: ["Venus"],
    8: ["Saturn"],
    9: ["Sun", "Jupiter"],
    10: ["Sun", "Mercury", "Saturn"],
    11: ["Jupiter"],
    12: ["Saturn"],
}



@dataclass
class QuestionContext:
    question: str
    topic: str
    domain: str
    title: str
    intent: str
    primary_house: int
    houses: list[int]
    favorable_houses: list[int]
    denying_houses: list[int]
    event_type: str | None = None
    keywords_matched: list[str] = field(default_factory=list)


@dataclass
class TechniqueVerdict:
    technique_id: str
    label: str
    source: str
    direction: str  # positive | caution | neutral | abstain
    applicable: bool = True
    note: str = ""
    timing: str = ""


def _esc(s: str) -> str:
    return html.escape(str(s))


def _detect_intent(q: str) -> str:
    ql = q.lower()
    if re.search(r"\b(recover|recovery|cure|heal|get well|remission)\b", ql):
        return "recovery"
    if re.search(r"\b(court|litigation|lawsuit|case|win the case|legal battle|bail)\b", ql):
        return "legal_outcome"
    # Amount / magnitude — must NOT collapse to yes/no ("how much hike" ≠ "yes")
    if re.search(
        r"\bhow\s+much\b|\bhow\s+many\b|\bwhat\s+(?:percent|percentage|%)\b|"
        r"\bwhat\s+amount\b|\bby\s+how\s+much\b|\bquantum\b|\bmagnitude\b",
        ql,
    ):
        return "amount"
    # True timing questions — do NOT treat bare "this year" as when (that is a yes/no horizon)
    if re.search(r"\bwhen\b|\bhow long\b|\btiming\b|\bwhat date\b|\bin which (?:month|year)\b", ql):
        return "when"
    if re.search(r"\b(how serious|severity|danger|life threat)\b", ql):
        return "severity"
    if re.search(r"\b(will|can|shall|should|is it possible|going to|is .+ likely)\b", ql):
        return "yes_no"
    return "general"


def _houses_from_question(q: str) -> tuple[list[int], list[str]]:
    ql = q.lower()
    hits: list[tuple[int, str]] = []
    for h, kws in HOUSE_KEYWORDS.items():
        for kw in kws:
            if kw in ql:
                hits.append((h, kw))
    if not hits:
        return [], []
    # Primary = most specific / first strong match
    order = sorted(set(h for h, _ in hits), key=lambda x: (-sum(1 for hh, _ in hits if hh == x), x))
    return order, [kw for _, kw in hits[:6]]


def _refine_topic(q: str, topic: str, intent: str) -> str:
    """Intent + keywords override generic horary topic detection."""
    ql = q.lower()
    if intent == "recovery":
        return "recovery"
    if intent == "legal_outcome" or re.search(r"\b(court|legal|litigation|lawsuit|case)\b", ql):
        return "litigation"
    if re.search(r"\b(married|marriage|marry|wedding|spouse|husband|wife|fianc)\b", ql):
        return "marriage"
    if re.search(r"\b(child|children|pregnant|baby|son|daughter)\b", ql):
        return "children"
    return topic


def _domain_from_topic_and_houses(topic: str, houses: list[int], q: str) -> str:
    if topic in TOPIC_TO_DOMAIN:
        dom = TOPIC_TO_DOMAIN[topic]
        if dom != "general":
            return dom
    if topic == "litigation":
        return "legal"
    if topic == "marriage":
        return "marriage"
    if topic in ("recovery", "disease_cure", "disease"):
        return "health"
    if 2 in houses and re.search(r"\b(speech|stammer|voice|teeth)\b", q.lower()):
        return "speech"
    if topic == "litigation" or 6 in houses[:2]:
        if re.search(r"\b(court|legal|litigation|case)\b", q.lower()):
            return "legal"
    house_domain = {
        2: "finance", 4: "property", 5: "children", 7: "marriage",
        9: "education", 10: "career", 11: "finance",
    }
    for h in houses:
        if h in house_domain:
            return house_domain[h]
    return "general"


def route_client_question(question: str) -> QuestionContext:
    """Semantic map: question -> domain, houses, intent, event hooks.

    Phase 1: MiniLM (paraphrase-multilingual) routes by meaning first; keyword
    tables are assist only. Falls back to keywords if the encoder is absent.
    """
    q = (question or "").strip()
    intent = _detect_intent(q)

    sem = None
    try:
        import semantic_question as SQ
        sem = SQ.route(q) if q else None
    except Exception as exc:  # noqa: BLE001
        print(f"[client_question] semantic route skipped: {exc}", flush=True)

    if sem and not (sem.degraded and sem.method == "keyword" and not sem.houses):
        topic = _refine_topic(q, sem.topic or "general", intent)
        # Prefer MiniLM houses; merge topic-bhavas favourable list
        houses = list(sem.houses or [])
        kw_hits = [f"minilm:h{sem.primary_house}", f"score={sem.house_score:.2f}"]
        if sem.method == "keyword":
            kw_houses, kw_hits = _houses_from_question(q)
            if kw_houses:
                houses = kw_houses
        tb = TOPIC_BHAVAS.get(topic, TOPIC_BHAVAS.get("general", {}))
        topic_primary = int(tb.get("primary", sem.primary_house or 1))
        primary = int(sem.primary_house or topic_primary)
        if primary not in houses:
            houses = [primary] + [h for h in houses if h != primary]
        for h in (tb.get("favorable") or []):
            if h not in houses:
                houses.append(h)
        houses = houses[:5] or [primary]
        domain = sem.domain if sem.domain and sem.domain != "general" else \
            _domain_from_topic_and_houses(topic, houses, q)
        fav = list(tb.get("favorable") or [])
        deny = list(tb.get("denying") or [])
    else:
        topic = _refine_topic(q, detect_topic(q) if q else "general", intent)
        houses, kw_hits = _houses_from_question(q)
        tb = TOPIC_BHAVAS.get(topic, TOPIC_BHAVAS.get("general", {}))
        topic_primary = int(tb.get("primary", 1))
        if houses:
            primary = houses[0] if topic == "general" else topic_primary
            if primary not in houses:
                houses = [primary] + [h for h in houses if h != primary]
        else:
            primary = topic_primary
            houses = [primary]
            sec = [h for h in (tb.get("favorable") or []) if h != primary]
            houses.extend(sec[:2])
        fav = list(tb.get("favorable") or [])
        deny = list(tb.get("denying") or [])
        domain = _domain_from_topic_and_houses(topic, houses, q)

    title = DOMAIN_TITLE.get(domain, domain.replace("_", " ").title())

    event_type = None
    ev_map = {
        "marriage": "marriage", "children": "child_birth", "career": "job_change",
        "property": "house_purchase", "travel": "foreign_relocation",
    }
    # Child speech / development  timing from dasha on H2+H5, not child_birth event gate
    if re.search(r"\b(speech|stammer|stutter|voice|speak)\b", q.lower()) and 2 in houses:
        event_type = None
    elif intent == "when" and domain in ev_map:
        event_type = ev_map[domain]

    return QuestionContext(
        question=q,
        topic=topic,
        domain=domain,
        title=title,
        intent=intent,
        primary_house=primary,
        houses=sorted(set(houses)),
        favorable_houses=fav,
        denying_houses=deny,
        event_type=event_type,
        keywords_matched=kw_hits,
    )


def _lord_in_houses(lord: str, lagna: str, planets: dict, houses: set[int]) -> bool:
    psign = planets.get(lord, {}).get("sign")
    if not psign:
        return False
    return house_from_lagna(psign, lagna) in houses


def _dignity_note(lord: str, planets: dict) -> str:
    psign = planets.get(lord, {}).get("sign", "")
    dig = get_dignity(lord, psign) if psign else "unknown"
    return f"{lord} ({dig})"


def _eval_bhava_lord(pc: dict, ctx: QuestionContext) -> TechniqueVerdict:
    """Primary house lord placement and dignity."""
    lagna = pc.get("lagna", {}).get("sign") or pc.get("meta", {}).get("lagna_sign", "")
    planets = pc.get("planets", {})
    h = ctx.primary_house
    ph_sign = house_sign(h, lagna)
    lord = SIGN_LORDS.get(ph_sign, "")
    if not lord:
        return TechniqueVerdict("bhava_lord", f"H{h} lord strength", "Parashari", "neutral", note="House lord unavailable")
    psign = planets.get(lord, {}).get("sign", "")
    phouse = house_from_lagna(psign, lagna) if psign else 0
    dig = get_dignity(lord, psign) if psign else "unknown"
    direction = "positive" if dig in ("exalted", "own_sign", "moolatrikona") else (
        "caution" if dig in ("debilitated", "enemy_sign") or phouse in (6, 8, 12) else "neutral"
    )
    if phouse in ctx.houses and direction != "caution":
        direction = "positive"
    return TechniqueVerdict(
        "bhava_lord", f"H{h} lord ({lord})", "Parashari",
        direction, note=f"{lord} in H{phouse} ({dig})",
    )


def _eval_natural_karaka(pc: dict, ctx: QuestionContext) -> TechniqueVerdict:
    """Mercury for speech/H2, Venus for spouse/H7, etc."""
    planets = pc.get("planets", {})
    lagna = pc.get("lagna", {}).get("sign") or pc.get("meta", {}).get("lagna_sign", "")
    karakas = HOUSE_KARAKAS.get(ctx.primary_house, [])
    if not karakas:
        return TechniqueVerdict("karaka", "Natural karaka", "Parashari", "abstain", applicable=False)
    best_dir = "neutral"
    notes: list[str] = []
    for k in karakas:
        psign = planets.get(k, {}).get("sign", "")
        if not psign:
            continue
        phouse = house_from_lagna(psign, lagna)
        dig = get_dignity(k, psign)
        notes.append(f"{k} H{phouse} ({dig})")
        if dig in ("exalted", "own_sign", "moolatrikona") and phouse not in (6, 8, 12):
            best_dir = "positive"
        elif dig in ("debilitated", "enemy_sign") or phouse in (6, 8, 12):
            if best_dir != "positive":
                best_dir = "caution"
    return TechniqueVerdict(
        "karaka", f"Natural karaka for H{ctx.primary_house}", "Parashari",
        best_dir, note="; ".join(notes) or "Karaka data unavailable",
    )


# ---------------------------------------------------------------------------
# Live technique evaluators (natal chart  -  no HTML scrape required)
# ---------------------------------------------------------------------------

_DIGNITY_SHORT = {
    "exalted": "exalted",
    "debilitated": "debilitated",
    "own_sign": "in own sign",
    "moolatrikona": "in moolatrikona",
    "friendly": "in friendly sign",
    "enemy_sign": "in enemy sign",
    "neutral_sign": "in neutral sign",
    "neutral": "in neutral sign",
    "great_friend_sign": "in great friend's sign",
}


def pillar_overall_score(pc: dict) -> int:
    """Deterministic lagna-pillar strength (0–95) from natal chart."""
    from vedic_pillar_report import Pillar
    return Pillar(pc).score()["overall"]


def _pillar_direction(overall: int) -> str:
    if overall >= 60:
        return "positive"
    if overall >= 45:
        return "neutral"
    return "caution"


def _pillar_reading(pc: dict, primary_house: int) -> tuple[int, str, str]:
    """Return (overall_pct, direction, factual_note) from chart data."""
    from vedic_pillar_report import NAT_BENEFIC, NAT_MALEFIC, Pillar

    p = Pillar(pc)
    overall = p.score()["overall"]
    direction = _pillar_direction(overall)
    verdict = p.verdict_word(overall).replace("–", "-").lower()

    ll = p.lagna_lord
    ll_h = p.ll["house"]
    ll_sign = p.ll["sign"]
    dig = _DIGNITY_SHORT.get(p.ll["dignity"], p.ll["dignity"].replace("_", " "))
    ruled = p.rules.get(ll, [])

    parts = [
        f"Lagna {p.lagna}; {ll} (lagna lord) {dig} in {ll_sign}, house {ll_h} "
        f"— pillar {verdict} ({overall}%)",
    ]

    if p.nb.get("neecha_bhanga_present"):
        cancel = p.nb.get("cancelling_planet", "")
        nb_ver = p.nb.get("verdict", "neecha bhanga")
        parts.append(f"{cancel + ' cancels debility' if cancel else nb_ver}")

    conj = p.conjunct()
    asp = p.aspecting(ll_h)
    good = sorted({x for x in conj + asp if x in NAT_BENEFIC})
    bad = sorted({x for x in conj + asp if x in NAT_MALEFIC})
    if good:
        parts.append(f"supported by {', '.join(good)}")
    if bad:
        parts.append(f"pressured by {', '.join(bad)}")
    if p.hemming().get("papa"):
        parts.append("Papa-Katari hemming on lagna lord")

    disp = p.dispositor
    disp_pl = p.planets[disp]
    if disp_pl["dignity"] in ("exalted", "own_sign", "moolatrikona", "great_friend_sign") and disp_pl["house"] not in (6, 8, 12):
        parts.append(f"dispositor {disp} well placed (house {disp_pl['house']})")
    elif disp_pl["dignity"] == "debilitated" or disp_pl["house"] in (6, 8, 12):
        parts.append(f"dispositor {disp} weak (house {disp_pl['house']})")

    if primary_house in ruled:
        parts.append(f"lagna lord rules house {primary_house} directly")
    elif ll_h == primary_house:
        parts.append(f"lagna lord occupies house {primary_house}")

    return overall, direction, "; ".join(parts) + "."


def _eval_pillar(pc: dict, ctx: QuestionContext) -> TechniqueVerdict:
    try:
        _, direction, note = _pillar_reading(pc, ctx.primary_house)
    except Exception:
        pillar = pc.get("pillar", {})
        lagna = pc.get("lagna", {}).get("sign") or pc.get("meta", {}).get("lagna_sign", "?")
        ll = pillar.get("lagna_lord", "?")
        ll_h = pillar.get("lagna_lord_house", "?")
        dig = pillar.get("lagna_lord_dignity", "?")
        direction = "neutral"
        note = f"Lagna {lagna}; {ll} (lagna lord) {dig} in house {ll_h} — pillar score unavailable."
    return TechniqueVerdict(
        "pillar", "Pillar of Life (lagna strength)", "Parashari",
        direction, note=note,
    )


def _eval_vimshottari(pc: dict, ctx: QuestionContext) -> TechniqueVerdict:
    vim = pc.get("vimshottari", {})
    md = vim.get("current_md", {}).get("md_lord", "")
    ad = next((a["ad_lord"] for a in vim.get("current_md_antardashas", []) if a.get("status") == "current"), "")
    lagna = pc.get("lagna", {}).get("sign") or pc.get("meta", {}).get("lagna_sign", "")
    planets = pc.get("planets", {})
    targets = set(ctx.houses)
    hits = []
    for lord in (md, ad):
        if lord and _lord_in_houses(lord, lagna, planets, targets):
            hits.append(lord)
    ph_sign = house_sign(ctx.primary_house, lagna)
    ph_lord = SIGN_LORDS.get(ph_sign, "")
    if ph_lord in (md, ad):
        hits.append(f"{ph_lord} rules H{ctx.primary_house}")
    direction = "positive" if hits else "neutral"
    if hits and ctx.intent in ("recovery", "legal_outcome"):
        direction = "positive"
    timing = ""
    for a in vim.get("current_md_antardashas", []):
        if a.get("status") == "current":
            timing = f"{a.get('start', '')[:7]} to {a.get('end', '')[:7]}"
    return TechniqueVerdict(
        "vimshottari", "Vimshottari MD/AD house activation", "rules1-2",
        direction, note="; ".join(hits) or f"Current {md}-{ad} not strongly on H{ctx.primary_house}",
        timing=timing,
    )


def _eval_kp(pc: dict, ctx: QuestionContext) -> TechniqueVerdict:
    if not pc.get("kp", {}).get("cusps"):
        return TechniqueVerdict("kp", "KP cusp sub-lord promise", KP_SOURCE, "abstain", applicable=False)
    try:
        from kp_event_timing import assess_kp_csl_promise, load_kp_chart
        from kp_chart import KPChart

        meta = pc.get("meta", {})
        dob = meta.get("dob", "")
        kp = KPChart.from_block(pc, pc["kp"], date.fromisoformat(dob[:10]), meta.get("client", ""))
        dom = ctx.domain if ctx.domain in ("marriage", "children", "career", "property", "travel", "education", "health") else {
            "legal": "health", "speech": "finance", "finance": "finance",
        }.get(ctx.domain, "career")
        if ctx.domain == "health" or ctx.intent == "recovery":
            dom = "health"
        k = assess_kp_csl_promise(kp, dom if dom != "health" else "marriage")
        # Health: check 6th CSL explicitly
        if ctx.primary_house == 6 or ctx.intent in ("recovery", "legal_outcome"):
            from kp_book_data import links_verdict
            sub6 = kp.csl(6)
            v6, hf, hu = links_verdict(kp.links(sub6), "health_bad" if ctx.intent != "recovery" else "health_good")
            if ctx.intent == "recovery":
                direction = "positive" if v6 in ("promised", "mixed") or 5 in hf or 11 in hf else "caution"
                note = f"H6 CSL {sub6}  -  recovery houses {sorted(hf)} vs blocking {sorted(hu)}"
            else:
                direction = "positive" if v6 == "promised" else ("caution" if v6 == "denied" else "neutral")
                note = f"H6 CSL {sub6}  -  {v6}"
            return TechniqueVerdict("kp", "KP 6th cusp sub-lord (health/legal)", KP_SOURCE, direction, note=note)
        if ctx.domain == "speech" or ctx.primary_house == 2:
            from kp_book_data import links_verdict
            sub2 = kp.csl(2)
            v2, hf, hu = links_verdict(kp.links(sub2), "finance")
            direction = "positive" if v2 in ("promised", "mixed") or 11 in hf else ("caution" if v2 == "denied" else "neutral")
            return TechniqueVerdict(
                "kp", "KP 2nd cusp sub-lord (speech/wealth)", KP_SOURCE, direction,
                note=f"H2 CSL {sub2} - {v2}; supporting houses {sorted(hf)}",
            )
        direction = "positive" if k.get("yes") else ("caution" if k.get("verdict") == "denied" else "neutral")
        return TechniqueVerdict("kp", f"KP H{k.get('primary_house', ctx.primary_house)} CSL promise", KP_SOURCE, direction, note=k.get("note", ""))
    except Exception as exc:
        return TechniqueVerdict("kp", "KP cusp analysis", KP_SOURCE, "abstain", note=str(exc)[:80])


def _eval_jaimini(pc: dict, ctx: QuestionContext) -> TechniqueVerdict:
    karaka_roles = {
        "marriage": "Darakaraka", "children": "Putrakaraka", "career": "Amatyakarak",
        "finance": "Amatyakarak", "property": "Matrukaraka", "legal": "Gnatikaraka",
        "health": "Atmakarak", "speech": "Bhratrukaraka",
    }
    role = karaka_roles.get(ctx.domain, "Atmakarak")
    kk = next((k for k in (pc.get("cara_karakas") or {}).get("karakas", []) if k.get("role") == role), None)
    if not kk:
        return TechniqueVerdict("jaimini", "Jaimini cara karaka", "rules6", "neutral", note=f"No {role} in chart data")
    h = kk.get("house", 0)
    direction = "caution" if h in (6, 8, 12) and kk.get("dignity") in ("debilitated", "enemy_sign") else "positive"
    if h in ctx.houses or ctx.primary_house in (5, 7, 10):
        direction = "positive" if direction != "caution" else "caution"
    return TechniqueVerdict(
        "jaimini", f"Jaimini {role}", "rules6",
        direction, note=f"{kk.get('planet')} in house {h} ({kk.get('dignity', '')})",
    )


def _eval_goel(ctx: QuestionContext, pc: dict, parsed: dict, birth_kw: dict) -> list[TechniqueVerdict]:
    out: list[TechniqueVerdict] = []
    try:
        from chara_yogini_timing import score_chara_goel_window, score_yogini_goel_window

        lagna = parsed.get("lagna", {}).get("sign", "")
        planets = parsed.get("planets", {})
        moon = planets.get("Moon", {})
        dob = date.fromisoformat(birth_kw.get("dob", pc["meta"]["dob"])[:10])
        today = date.today()
        event_houses = set(ctx.houses)

        y = score_yogini_goel_window(
            w_start=today, w_end=today.replace(year=today.year + 2),
            event_kind=ctx.domain if ctx.domain in ("marriage", "child", "career", "property", "travel", "education", "business") else "career",
            event_houses=event_houses, birth_lagna=lagna, planets=planets, pc=pc,
            moon_nak=moon.get("nakshatra", ""), moon_deg_in_nak=float(moon.get("degree_in_nakshatra") or 0),
            dob=dob,
        )
        out.append(TechniqueVerdict(
            "yogini_goel", "Progressive Yogini PL (rules8)", GOEL_SOURCE,
            "positive" if y.get("yes") else "neutral", note=y.get("note", ""),
        ))

        from jaimini_chara_dasha import get_chara_dasha

        chara = get_chara_dasha(pc)
        c = score_chara_goel_window(
            w_start=today, w_end=today.replace(year=today.year + 2),
            event_kind=ctx.domain if ctx.domain in ("marriage", "child", "career", "property", "travel", "education", "business") else "career",
            event_houses=event_houses, birth_lagna=lagna, planets=planets, pc=pc, chara=chara,
        )
        out.append(TechniqueVerdict(
            "chara_goel", "Chara MD-lagna lord link (rules8)", GOEL_SOURCE,
            "positive" if c.get("yes") else "neutral", note=c.get("note", ""),
        ))
    except Exception as exc:
        out.append(TechniqueVerdict("goel", "Goel Chara/Yogini", GOEL_SOURCE, "abstain", note=str(exc)[:60]))
    return out


def _eval_rtvd(pc: dict, ctx: QuestionContext) -> TechniqueVerdict:
    rtvd = pc.get("rtvd", {})
    year_h = rtvd.get("current_year_house")
    if not year_h:
        return TechniqueVerdict("rtvd", "RTVD year-lord house", "rules16", "abstain", applicable=False)
    direction = "positive" if year_h in ctx.houses else "neutral"
    return TechniqueVerdict(
        "rtvd", "RTVD current year theme", "rules16", direction,
        note=f"Age-year activates house {year_h}; question focuses H{ctx.primary_house}",
        timing=str(date.today().year),
    )


def _eval_ashtakavarga(pc: dict, ctx: QuestionContext) -> TechniqueVerdict:
    sav = pc.get("ashtakavarga", {}).get("sav") or []
    if len(sav) < 12:
        return TechniqueVerdict("ashtakavarga", "Ashtakavarga SAV on house", "rules10", "abstain", applicable=False)
    h = ctx.primary_house
    binds = sav[h - 1] if 1 <= h <= 12 else 0
    direction = "positive" if binds >= 28 else ("caution" if binds < 22 else "neutral")
    return TechniqueVerdict(
        "ashtakavarga", f"SAV bindus on H{h}", "rules10", direction, note=f"{binds} bindus (28+ supportive)",
    )


def _eval_longevity(pc: dict, ctx: QuestionContext) -> TechniqueVerdict:
    if ctx.domain not in ("health", "legal") and ctx.intent not in ("recovery", "severity", "legal_outcome"):
        return TechniqueVerdict("longevity", "Maraka / health risk band", "rules25-26", "abstain", applicable=False)
    try:
        from confluence_longevity_lane import classify_ad_risk
        ad = next((a for a in pc.get("vimshottari", {}).get("current_md_antardashas", []) if a.get("status") == "current"), {})
        cls, mb, risk, theme = classify_ad_risk(pc, ad.get("ad_lord", ""))
        direction = "caution" if risk in ("High", "Highest", "Moderate") and ctx.intent == "severity" else (
            "positive" if risk in ("Low", "Minimal") else "neutral"
        )
        if ctx.intent == "recovery" and risk in ("Low", "Minimal"):
            direction = "positive"
        return TechniqueVerdict(
            "longevity", "Longevity / maraka qualification", "rules25-26", direction,
            note=f"Current antar risk {risk}; {theme[:80]}",
        )
    except Exception:
        return TechniqueVerdict("longevity", "Longevity lane", "rules25-26", "abstain", applicable=False)


def _eval_varga(pc: dict, ctx: QuestionContext) -> TechniqueVerdict:
    div = pc.get("divisional", {})
    varga_key = {5: "D7", 7: "D9", 10: "D10", 4: "D4", 9: "D9"}.get(ctx.primary_house, "D9")
    if varga_key not in div and "D9" in div:
        varga_key = "D9"
    if varga_key not in div:
        return TechniqueVerdict("varga", "Event varga", "Goel varga", "neutral", note="Varga map not in precompute")
    lagna = pc.get("lagna", {}).get("sign") or pc.get("meta", {}).get("lagna_sign", "")
    ph_sign = house_sign(ctx.primary_house, lagna)
    lord = SIGN_LORDS.get(ph_sign, "")
    vsign = div.get(varga_key, {}).get(lord, "")
    if not vsign:
        return TechniqueVerdict("varga", f"{varga_key} house lord", "Goel varga", "neutral", note=f"{lord} varga placement unavailable")
    direction = "positive" if get_dignity(lord, vsign) in ("exalted", "own_sign", "moolatrikona", "friend_sign") else "neutral"
    return TechniqueVerdict(
        "varga", f"{varga_key} support for H{ctx.primary_house} lord", "Goel varga",
        direction, note=f"{lord} in {vsign} in {varga_key}",
    )


def _eval_timing_event(ctx: QuestionContext, birth_kw: dict) -> TechniqueVerdict:
    if not ctx.event_type or ctx.intent != "when":
        return TechniqueVerdict("event_timing", "Multi-technique event window", "confluence gate", "abstain", applicable=False)
    try:
        from future_event_timing import predict_next_event
        kw = {k: v for k, v in birth_kw.items() if k != "gender"}
        r = predict_next_event(event_type=ctx.event_type, gender=int(birth_kw.get("gender", 0)), **kw)
        if r.get("timing_available") and r.get("next_window"):
            w = r["next_window"]
            return TechniqueVerdict(
                "event_timing", "Full confluence event window", "future_event_timing",
                "positive", note=f"Confirmed {w.get('range_label')} ({w.get('md_lord')}/{w.get('ad_lord')})",
                timing=w.get("range_label", ""),
            )
        conf = (r.get("best_partial_window") or {}).get("confluence") or {}
        return TechniqueVerdict(
            "event_timing", "Event timing confluence", "future_event_timing",
            "caution", note=r.get("message", "No confirmed window")[:120],
            timing=conf.get("confluence_pct_display", ""),
        )
    except Exception as exc:
        return TechniqueVerdict("event_timing", "Event timing", "future_event_timing", "abstain", note=str(exc)[:60])


# ── extra house-quality votes (nodes, deep divisional, 108 classical rules) ──
_NODES_CQE = {"Rahu", "Ketu"}
_MALEFIC_CQE = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
_BENEFIC_CQE = {"Jupiter", "Venus", "Mercury", "Moon"}
_P9_CQE = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
# primary house -> (varga that examines it, the house number to read within that varga)
_VARGA_FOR_HOUSE = {
    1: ("D1", 1), 2: ("D2", 2), 3: ("D3", 3), 4: ("D4", 4), 5: ("D7", 5),
    6: ("D30", 6), 7: ("D9", 7), 8: ("D30", 8), 9: ("D9", 9), 10: ("D10", 10),
    11: ("D11", 11), 12: ("D20", 12),
}
_DIG_GOOD_CQE = ("exalted", "own_sign", "moolatrikona")
_DIG_BAD_CQE = ("debilitated", "enemy_sign")
_NODE_SIG = {2: "family & savings", 4: "home & peace of mind", 5: "progeny (children)",
             7: "marriage & partner", 9: "fortune & father", 11: "fulfilment of desires"}


def _ord_cqe(n: int) -> str:
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1:'st',2:'nd',3:'rd'}.get(n % 10, 'th')}"


def _all_rule_verdicts(pc: dict):
    c = pc.get("_cqe_eval_all")
    if c is None:
        try:
            from prediction108_rules import evaluate_all
            c = evaluate_all(pc)
        except Exception:
            c = []
        pc["_cqe_eval_all"] = c
    return c


_RULE_NEG_KW = ("debilit", "afflict", "malefic", "weak", " loss", "delay", "obstacl", "difficult",
                "enemy", "combust", "maraka", "dusthana", "dushthana", "sorrow", "disease", "hurdle",
                "suffer", "deny", "denied", "harm", "stress", "problem", "fear", "trik", "separat", "broken")
_RULE_POS_KW = ("exalt", "own sign", "moolatrikona", "moolatrik", "strong", "benefic", "raj yoga",
                "rajayoga", "dignif", "protect", "gain", "support", "prosper", "success", "fortune",
                "blessing", "auspicious", "well placed", "well-placed", "vipreet", "vipareet", "favour")


def _rule_polarity_cqe(low: str) -> int:
    pos = sum(1 for k in _RULE_POS_KW if k in low)
    neg = sum(1 for k in _RULE_NEG_KW if k in low)
    return 1 if pos > neg else (-1 if neg > pos else 0)


def _eval_node_in_house(pc: dict, ctx: QuestionContext) -> TechniqueVerdict:
    """Rahu/Ketu sitting in the primary house disturb that house's signification
    (classic for progeny/marriage/home), except in upachaya houses where they give drive."""
    lagna = pc.get("lagna", {}).get("sign") or pc.get("meta", {}).get("lagna_sign", "")
    planets = pc.get("planets", {})
    h = ctx.primary_house
    nodes = [p for p in ("Rahu", "Ketu")
             if planets.get(p, {}).get("sign") and house_from_lagna(planets[p]["sign"], lagna) == h]
    if not nodes:
        return TechniqueVerdict("node_house", f"Nodes in H{h}", "Parashari", "abstain", applicable=False)
    nd = ", ".join(nodes)
    if h in (3, 6, 11):
        return TechniqueVerdict("node_house", f"{nd} in H{h}", "Parashari", "neutral",
                                note=f"{nd} in growth house H{h} — drive over disturbance")
    sig = _NODE_SIG.get(h)
    note = f"{nd} in H{h} unsettles " + (sig if sig else f"this house's matters")
    return TechniqueVerdict("node_house", f"{nd} in H{h}", "Parashari", "caution", note=note)


def _eval_varga_house(pc: dict, ctx: QuestionContext) -> TechniqueVerdict:
    """Inspect the divisional chart that governs this house (D7 children, D9 marriage,
    D10 career, D30 health…) — its key house occupants, that house-lord, and the karaka."""
    h = ctx.primary_house
    div = pc.get("divisional", {}) or {}
    code, keyh = _VARGA_FOR_HOUSE.get(h, ("D9", h))
    if code not in div:
        code, keyh = ("D9", h) if "D9" in div else (code, keyh)
    vd = div.get(code, {})
    vlagna = vd.get("Lagna")
    if not vlagna or vlagna not in SIGNS:
        return TechniqueVerdict("varga_house", f"{code} depth for H{h}", "Goel varga", "abstain", applicable=False)
    key_sign = SIGNS[(SIGNS.index(vlagna) + keyh - 1) % 12]
    occ = [p for p in _P9_CQE if vd.get(p) == key_sign]
    pos_pts = neg_pts = 0
    notes: list[str] = []
    upa = keyh in (3, 6, 11)
    if not upa:
        bad = [p for p in occ if p in _MALEFIC_CQE and get_dignity(p, key_sign) not in _DIG_GOOD_CQE]
        if bad:
            neg_pts += 1
            notes.append(f"{', '.join(bad)} on {code} {_ord_cqe(keyh)}")
    ben = [p for p in occ if p in _BENEFIC_CQE]
    if ben and not (not upa and any(p in _MALEFIC_CQE for p in occ)):
        pos_pts += 1
        notes.append(f"benefic {', '.join(ben)} on {code} {_ord_cqe(keyh)}")
    for k in HOUSE_KARAKAS.get(h, []):
        ks = vd.get(k)
        if not ks:
            continue
        kd = get_dignity(k, ks)
        if kd in _DIG_GOOD_CQE:
            pos_pts += 1
            notes.append(f"{k} strong in {code}")
        elif kd in _DIG_BAD_CQE:
            neg_pts += 1
            notes.append(f"{k} weak in {code}")
    klord = SIGN_LORDS.get(key_sign, "")
    kls = vd.get(klord)
    if kls:
        kld = get_dignity(klord, kls)
        if kld in _DIG_GOOD_CQE:
            pos_pts += 1
        elif kld in _DIG_BAD_CQE:
            neg_pts += 1
            notes.append(f"{code} {_ord_cqe(keyh)}-lord {klord} weak")
    direction = "positive" if pos_pts > neg_pts else ("caution" if neg_pts > pos_pts else "neutral")
    return TechniqueVerdict("varga_house", f"{code} chart depth for H{h}", "Goel varga",
                            direction, note="; ".join(notes) or f"{code} {_ord_cqe(keyh)} balanced")


def _eval_house_rules108(pc: dict, ctx: QuestionContext) -> TechniqueVerdict:
    """Net of the classical 108 rules (predictivetechnique) that explicitly touch this house."""
    import re
    h = ctx.primary_house
    verds = _all_rule_verdicts(pc)
    if not verds:
        return TechniqueVerdict("rules108_house", f"108 rules on H{h}", "predictivetechnique", "abstain", applicable=False)
    ordh = _ord_cqe(h)
    pos = neg = 0
    for v in verds:
        if getattr(v, "verdict", "") not in ("HIT", "PARTIAL"):
            continue
        low = f"{getattr(v,'title','')} {getattr(v,'finding','')} {getattr(v,'prediction','')}".lower()
        if not (re.search(rf"\b{ordh}\b", low) or f"house {h}" in low):
            continue
        pol = _rule_polarity_cqe(low)
        if pol > 0:
            pos += 1
        elif pol < 0:
            neg += 1
    if pos == 0 and neg == 0:
        return TechniqueVerdict("rules108_house", f"108 rules on H{h}", "predictivetechnique", "abstain", applicable=False)
    direction = "positive" if pos - neg >= 1 else ("caution" if neg - pos >= 1 else "neutral")
    return TechniqueVerdict("rules108_house", f"108 classical rules on H{h}", "predictivetechnique",
                            direction, note=f"{pos} supportive / {neg} cautionary rule(s) on H{h}")


TECHNIQUE_RUNNERS: list[Callable[..., TechniqueVerdict | list[TechniqueVerdict]]] = [
    _eval_pillar,
    _eval_bhava_lord,
    _eval_natural_karaka,
    _eval_vimshottari,
    _eval_kp,
    _eval_jaimini,
    _eval_rtvd,
    _eval_ashtakavarga,
    _eval_longevity,
    _eval_varga,
    _eval_node_in_house,
    _eval_varga_house,
    _eval_house_rules108,
]


def evaluate_question_techniques(
    ctx: QuestionContext,
    pc: dict,
    parsed: dict | None = None,
    *,
    birth_kw: dict | None = None,
) -> list[TechniqueVerdict]:
    """Run every applicable natal technique for this question."""
    parsed = parsed or {"lagna": pc.get("lagna", {}), "planets": pc.get("planets", {})}
    birth_kw = birth_kw or {}
    verdicts: list[TechniqueVerdict] = []

    for fn in TECHNIQUE_RUNNERS:
        verdicts.append(fn(pc, ctx))

    verdicts.extend(_eval_goel(ctx, pc, parsed, birth_kw))
    if birth_kw.get("dob") and birth_kw.get("birth_time"):
        verdicts.append(_eval_timing_event(ctx, birth_kw))

    return [v for v in verdicts if v.applicable]


def synthesize_answer(ctx: QuestionContext, verdicts: list[TechniqueVerdict]) -> dict[str, Any]:
    """Merge technique votes into one client-facing answer."""
    applicable = [v for v in verdicts if v.applicable and v.direction != "abstain"]
    pos = sum(1 for v in applicable if v.direction == "positive")
    cau = sum(1 for v in applicable if v.direction == "caution")
    neu = sum(1 for v in applicable if v.direction == "neutral")
    total = len(applicable) or 1
    pct = round(pos / total, 3)

    # Direction for yes/no, recovery, and amount (never binary "yes" for "how much…")
    if ctx.intent == "recovery":
        answer = "recovery_likely" if pos > cau and pos >= neu else ("recovery_slow" if pos >= cau else "recovery_uncertain")
    elif ctx.intent == "legal_outcome":
        answer = "favorable" if pos > cau else ("challenging" if cau > pos else "mixed")
    elif ctx.intent == "when":
        answer = "window_found" if any(v.technique_id == "event_timing" and v.direction == "positive" for v in applicable) else "timing_partial"
    elif ctx.intent == "amount":
        # Softer gate than yes/no: magnitude lean, not a hard promise
        if pos > cau and pct >= 0.5:
            answer = "increase_favoured"
        elif cau > pos:
            answer = "increase_limited"
        else:
            answer = "amount_unclear"
    else:
        answer = "yes" if pos > cau and pct > GATE_PCT else ("no" if cau > pos and cau / total > GATE_PCT else "uncertain")

    # Mandatory pillars for release
    must_ids = {"vimshottari", "varga", "kp"}
    must_ok = sum(1 for v in applicable if v.technique_id in must_ids and v.direction == "positive")
    goel_ok = any(v.technique_id in ("yogini_goel", "chara_goel") and v.direction == "positive" for v in applicable)
    chara_family = any(v.technique_id in ("chara_goel", "jaimini") and v.direction == "positive" for v in applicable)

    confirmed = (
        pct > GATE_PCT
        and must_ok >= 2
        and (goel_ok or chara_family)
        and pos > cau
    )

    conf_label = (
        "VERY HIGH" if confirmed and pos >= 7 else
        "HIGH" if confirmed else
        "MODERATE" if pct >= 0.6 else
        "LOW"
    )

    timing = next((v.timing for v in applicable if v.timing), "")
    if not timing:
        timing = next((v.timing for v in applicable if v.technique_id == "vimshottari"), "")

    headline = {
        "yes": f"Yes  -  {ctx.title} is supported in your chart",
        "no": f"No  -  strong headwinds for {ctx.title.lower()}",
        "uncertain": f"Mixed signals  -  {ctx.title} needs more alignment",
        "recovery_likely": "Recovery is supported when you follow steady care",
        "recovery_slow": "Recovery is possible but slow  -  patience and discipline required",
        "recovery_uncertain": "Recovery is not clearly promised yet  -  strengthen baseline health",
        "favorable": "Legal outcome can turn in your favour with documentation and timing",
        "challenging": "Legal matter faces real resistance  -  prepare thoroughly",
        "mixed": "Legal result is mixed  -  neither clear win nor clear loss",
        "window_found": "A confirmed timing window exists for this event",
        "timing_partial": "Theme is promised but no fully confirmed date yet",
        "increase_favoured": (
            f"An upward move in {ctx.title.lower()} is favoured — "
            "the chart does not name an exact figure or %"
        ),
        "increase_limited": (
            f"Any rise in {ctx.title.lower()} looks modest or delayed — "
            "not a clear large hike"
        ),
        "amount_unclear": (
            f"The size of any {ctx.title.lower()} change is not clearly fixed — "
            "ask as yes/no or timing for a sharper call"
        ),
    }.get(answer, "Read the technique table below")

    return {
        "answer": answer,
        "headline": headline,
        "confidence": conf_label,
        "confirmed": confirmed,
        "confluence_pct": int(round(pct * 100)),
        "positive_votes": pos,
        "caution_votes": cau,
        "neutral_votes": neu,
        "total_techniques": total,
        "timing": timing,
        "routing": {
            "domain": ctx.domain,
            "title": ctx.title,
            "topic": ctx.topic,
            "intent": ctx.intent,
            "primary_house": ctx.primary_house,
            "houses": ctx.houses,
            "keywords": ctx.keywords_matched,
        },
    }


def answer_client_question(
    question: str,
    *,
    client_name: str,
    dob: str,
    birth_time: str = "",
    latitude: float = 0.0,
    longitude: float = 0.0,
    timezone: float = 5.5,
    place_name: str = "",
    gender: int = 0,
    precomputed_path: str = "",
    extracted_path: str = "",
) -> dict[str, Any]:
    """Full pipeline: route ? evaluate techniques ? synthesize."""
    if not question.strip():
        return {"ok": False, "error": "Question is empty."}

    pc = resolve_precompute(
        client_name, dob,
        extracted_path=extracted_path or None,
        precomputed_path=precomputed_path or None,
        birth_time=birth_time or None,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        place_name=place_name,
    )
    parsed = {
        "lagna": pc.get("lagna", {}),
        "planets": pc.get("planets", {}),
        "divisional": pc.get("divisional", {}),
    }
    ctx = route_client_question(question)
    birth_kw = {
        "client_name": client_name,
        "dob": dob,
        "birth_time": birth_time,
        "rectified_time": birth_time,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "place_name": place_name,
        "gender": gender,
    }
    verdicts = evaluate_question_techniques(ctx, pc, parsed, birth_kw=birth_kw)
    synthesis = synthesize_answer(ctx, verdicts)

    return {
        "ok": True,
        "question": question,
        "synthesis": synthesis,
        "techniques": [
            {
                "id": v.technique_id,
                "label": v.label,
                "source": v.source,
                "direction": v.direction,
                "note": v.note,
                "timing": v.timing,
            }
            for v in verdicts if v.applicable
        ],
    }


def render_question_answer_html(result: dict[str, Any]) -> str:
    """Standalone HTML for Main Question API / focus panel."""
    if not result.get("ok"):
        return f"<p class='warn'>{_esc(result.get('error', 'Failed'))}</p>"

    syn = result["synthesis"]
    route = syn["routing"]
    cls = "ok" if syn["confirmed"] else "info"
    rows = ""
    for t in result.get("techniques", []):
        mark = {"positive": "+", "caution": "-", "neutral": "="}.get(t["direction"], "?")
        rows += f"<tr><td>{mark}</td><td>{_esc(t['label'])}</td><td>{_esc(t['note'][:100])}</td><td>{_esc(t.get('timing',''))}</td></tr>"

    return f"""<div class="btr-result {cls}">
<strong>{_esc(syn['headline'])}</strong>
<p style="font-size:0.8rem;margin-top:6px">Mapped to <strong>{_esc(route['title'])}</strong>
  H{route['primary_house']} focus  intent: {route['intent']}
  {syn['positive_votes']}/{syn['total_techniques']} methods positive ({syn['confluence_pct']}%)
  confidence: {syn['confidence']}{('  timing: ' + _esc(syn['timing'])) if syn.get('timing') else ''}</p>
<table style="width:100%;font-size:0.74rem;margin-top:8px;border-collapse:collapse">
<tr><th></th><th>Technique</th><th>Finding</th><th>When</th></tr>{rows}</table>
<p style="font-size:0.72rem;color:var(--muted);margin-top:8px">Question: &ldquo;{_esc(result['question'])}&rdquo;</p>
</div>"""
