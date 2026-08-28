"""
palm_report.py — turns the palm engine's raw analysis into the reading a person
reads, split into a free half and a paid half.

Two delivery shapes:
  • build_palm_reading      — legacy JSON for the old in-page card UI
  • build_palm_html_reading — the served path: two HTML halves rendered by
                             `palm_cards` (same iframe path astrology uses)

The halves used to be produced by deep-copying the analysis and deleting fields
from each copy, which put every numbered point and its estimated age on the free
side and took the customer's own annotated photographs off the paid side. They
are now rendered twice from one analysis, branching on `paid`.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

def _customer_numbered(hand: dict[str, Any]) -> list[dict[str, Any]]:
    items = list(hand.get("numbered_checklist") or [])
    q = (hand.get("features") or {}).get("quality") or {}
    try:
        from palm_api.quality_gate import filter_special_mark_findings
        return filter_special_mark_findings(items, q)
    except Exception:
        return items


class _Req:
    """Duck-type of the old pydantic request, so the lifted code is unchanged."""

    def __init__(self, p: dict) -> None:
        self.name = p.get("name", "Seeker")
        self.age = int(p.get("age", 30))
        self.gender = p.get("gender", "other")
        self.dominant = p.get("dominant", "right")


import hashlib as _hl


def _seed(d: dict) -> int:
    key = "|".join(str(d.get(k, "")) for k in ("name", "age", "gender", "dominant"))
    return int(_hl.sha256(key.encode()).hexdigest()[:8], 16)


def _pick(opts: List[str], d: dict, salt: int = 0) -> str:
    return opts[(_seed(d) + salt) % len(opts)]


def _first(name: str) -> str:
    n = (name or "").strip().split()
    return n[0] if n else "friend"


def palm_opening(req: "_Req", dom: Dict[str, Any]) -> str:
    """A paragraph that could only be about this pair of hands."""
    fn = _first(req.name)
    d = {"name": req.name, "age": req.age, "gender": req.gender, "dominant": req.dominant}
    feats = dom.get("features") or {}
    morph = feats.get("morphology") or {}
    hand = morph.get("hand_type")
    lines = feats.get("lines") or {}
    life, heart, head = lines.get("life") or {}, lines.get("heart") or {}, lines.get("head") or {}

    open_ = _pick([
        f"{fn}, I have both of your palms in front of me — the {req.dominant} one for the life "
        f"you have actually built, the other for what you were handed.",
        f"{fn}, your two hands disagree with each other in places, and that is exactly where "
        f"this reading gets interesting.",
        f"{fn}, one of your palms holds the blueprint and the {req.dominant} one holds what you "
        f"did with it. I read them together.",
    ], d)

    detail = ""
    if hand:
        h = prose(hand)
        detail = _pick([
            f" Yours is <b>{h}</b> hand — that single fact changes how every line below "
            f"should be read.",
            f" You have <b>{h}</b> hand, and that sets the temperature for everything "
            f"that follows.",
        ], d, 3)

    spec = ""
    quality_grade = str(((feats.get("quality") or {}).get("grade") or "fair")).lower()
    if quality_grade != "poor" and life.get("depth") and heart.get("quality"):
        spec = (f" Your life line runs <b>{prose(life['depth'])}</b> and your heart line reads "
                f"<b>{prose(heart['quality'])}</b>")
        if head.get("start_relation"):
            spec += f", while your head line begins <b>{prose(head['start_relation'])}</b>"
        spec += " — no two people carry that combination the same way."
    elif quality_grade == "poor":
        spec = " The photograph is not clear enough for me to lean on fine line detail, so I keep the reading to the broader patterns that can still be checked."

    age_bit = (f" At {req.age}, a fair part of your palm is already written; the rest is still "
               f"forming, and that is the half worth talking about." if req.age else "")
    return open_ + detail + spec + age_bit



# Raw feature enums read like database values ("separated_wide"). Say them the
# way a person would.
ENUM_PROSE = {
    "separated_wide": "clearly separate from it",
    "separated": "separate from it",
    "merged": "joined to it for a while",
    "touching": "just touching it",
    "deep": "deep and well cut",
    "faint": "lightly drawn",
    "medium": "evenly drawn",
    "shallow": "lightly drawn",
    "clear": "clean and unbroken",
    "broken": "broken in places",
    "chained": "chained in places",
    "wide": "sweeping wide",
    "narrow": "held close",
    "air": "an Air",
    "earth": "an Earth",
    "fire": "a Fire",
    "water": "a Water",
    "prominent": "full",
    "developed": "well developed",
    "moderate": "moderate",
    "flat": "flat",
}


def prose(value: Any) -> str:
    """Turn a feature enum into something readable."""
    v = str(value or "").strip()
    return ENUM_PROSE.get(v.lower(), v.replace("_", " "))


PALM_STRIP = [
    r"\bno[- ]LLM\b", r"\bNO[- ]LLM\b", r"\bdeterministic\b", r"\bDeterministic\b",
    r"\brule-based\b", r"\bheuristic(ally)?\b", r"\btemplate\b",
]


def devoice(text: str) -> str:
    """Strip machinery talk and third-person distance from generated prose."""
    import re as _re
    out = text or ""
    for pat in PALM_STRIP:
        out = _re.sub(pat, "", out)
    for pat, rep in ((r"\bThe native\b", "You"), (r"\bthe native\b", "you"),
                     (r"\bThe subject\b", "You"), (r"\bthe subject\b", "you"),
                     (r"\bthe wearer\b", "you")):
        out = _re.sub(pat, rep, out)
    return _re.sub(r"\s{2,}", " ", out).strip()


ASPECT_ICON = {
    "character": "i-hand", "mind": "i-star", "love": "i-chat",
    "career": "i-lock", "wealth": "i-star", "health": "i-hand",
    "fortune": "i-moon",
}
STRENGTH_SCORE = {"strong": 86, "moderate": 72, "tentative": 58, "weak": 52}
DEPTH_SCORE = {"deep": 88, "medium": 74, "moderate": 74, "faint": 58, "shallow": 58}
QUALITY_ADJ = {"clear": 6, "broken": -8, "chained": -10, "faint": -6}
MOUNT_SCORE = {"prominent": 88, "developed": 82, "moderate": 72, "flat": 58, "weak": 55}


def _line_score(lines: Dict[str, Any], key: str, fallback: int = 70) -> int:
    p = (lines or {}).get(key) or {}
    if not p.get("detected"):
        return fallback
    try:
        from palm_api.measurements import line_strength_score
        rank = line_strength_score(p)
        return {0: fallback, 1: 58, 2: 74, 3: 88}.get(rank, fallback)
    except Exception:  # noqa: BLE001
        s = DEPTH_SCORE.get(str(p.get("depth")), 72) + QUALITY_ADJ.get(str(p.get("quality")), 0)
        return max(45, min(97, int(s)))


def build_scores(dom: Dict[str, Any], aspects: Dict[str, Any]) -> List[Dict[str, Any]]:
    lines = (dom.get("features") or {}).get("lines") or {}
    mounts = (dom.get("features") or {}).get("mounts") or {}

    def blend(line_key: str, aspect_key: str, mount_key: Optional[str] = None) -> int:
        parts = [_line_score(lines, line_key)]
        a = aspects.get(aspect_key)
        if a:
            parts.append(STRENGTH_SCORE.get(str(a.get("strength")), 70))
        if mount_key and mounts.get(mount_key):
            parts.append(MOUNT_SCORE.get(str(mounts[mount_key]), 70))
        return int(round(sum(parts) / len(parts)))

    rows = [
        {"k": "Vitality",  "v": blend("life",  "health", "venus")},
        {"k": "Intellect", "v": blend("head",  "mind",   "mercury")},
        {"k": "Emotion",   "v": blend("heart", "love",   "moon")},
        {"k": "Fortune",   "v": blend("fate",  "career", "jupiter")},
    ]
    grade = str(((dom.get("features") or {}).get("quality") or {}).get("grade") or "fair").lower()
    if grade == "poor":
        for row in rows:
            row["v"] = min(int(row["v"]), 65)
    elif grade == "fair":
        for row in rows:
            row["v"] = min(int(row["v"]), 78)
    return rows


def _aspect_tags(a: Dict[str, Any]) -> List[str]:
    tags: List[str] = []
    st = str(a.get("strength", "")).strip()
    if st:
        tags.append(st.capitalize() + " signal")
    n = a.get("reinforced_count") or 0
    if n:
        tags.append(f"{n} sign{'s' if n != 1 else ''} agree")
    # deliberately NOT the book labels: a reading should stand on its own
    return tags[:3]


def _cite(a: Dict[str, Any]) -> str:
    """A customer-facing reading carries no citations."""
    return ""


# Aspect partition for the legacy JSON reading only. The HTML halves no longer
# hide whole life areas: every area shows its verdict for free and locks the
# working under it, which is the split `palm_cards` implements.
FREE_ASPECTS = ("character", "mind")
PAID_ASPECTS = ("love", "career", "wealth", "health", "fortune", "travel")


def build_reading(raw: Dict[str, Any], req: "_Req", overlays: Dict[str, str]) -> Dict[str, Any]:
    conf = raw.get("confluence") or {}
    dom_key = conf.get("dominant_hand") or req.dominant
    dom = raw.get(dom_key) or raw.get("right") or raw.get("left") or {}
    aspects_list = conf.get("life_aspects") or []
    aspects = {a["key"]: a for a in aspects_list}
    age = req.age

    # ---- free section: who you are + everything dated up to today -----------
    past: List[Dict[str, Any]] = [{
        "icon": "i-hand",
        "title": f"{_first(req.name)}, this is what your hands say",
        "tags": ["Both palms read", f"{req.dominant.title()}-dominant"],
        "body": palm_opening(req, dom),
        "source": "",
    }]
    for key in FREE_ASPECTS:
        a = aspects.get(key)
        if not a or not (a.get("summary") or "").strip():
            continue
        past.append({
            "icon": ASPECT_ICON.get(key, "i-star"),
            "title": a.get("title") or key.title(),
            "tags": _aspect_tags(a),
            "body": devoice(a["summary"]),
            "source": "",
        })

    # single-hand fallback: palm_api only builds confluence when BOTH hands are
    # present, so fall back to the dominant hand's own numbered findings.
    if not past:
        for item in (dom.get("numbered_checklist") or [])[:8]:
            conc = item.get("conclusive") or {}
            t = item.get("timing") or {}
            if isinstance(t.get("estimated_age"), int) and t["estimated_age"] > age:
                continue
            cit = conc.get("citation") or {}
            past.append({
                "icon": "i-hand" if item.get("kind") == "line" else "i-star",
                "title": item.get("title", "Finding"),
                "tags": [s.strip() for s in str(item.get("finding", "")).split(";") if s.strip()][:3],
                "body": conc.get("conclusion") or conc.get("verdict") or item.get("finding", ""),
                "source": "",
            })

    preds = conf.get("predictions") or []
    dated = [p for p in preds if isinstance(p.get("age"), int)]
    undated = [p for p in preds if not isinstance(p.get("age"), int)]

    past_events = sorted([p for p in dated if p["age"] <= age], key=lambda p: p["age"])
    future_events = sorted([p for p in dated if p["age"] > age], key=lambda p: p["age"])

    if past_events:
        past.append({
            "icon": "i-moon",
            "title": "Your timeline so far",
            "tags": [f"{len(past_events)} dated marking{'s' if len(past_events) != 1 else ''}",
                     f"up to age {age}"],
            "body": "  ".join(f"Age {p['age']} — {p['text']}" for p in past_events),
            "source": "",
        })

    # cross-hand agreement (innate vs developed) — genuinely interesting, keep free
    agree = [x.get("statement") for x in (conf.get("lines") or []) if x.get("statement")]
    agree += [x.get("statement") for x in (conf.get("mounts") or []) if x.get("statement")]
    if agree:
        past.append({
            "icon": "i-hand",
            "title": "Left hand vs right hand",
            "tags": ["Innate vs developed", "Both palms compared"],
            "body": devoice(" ".join(agree[:8])),
            "source": "",
        })

    # ---- paid section ------------------------------------------------------
    future: List[Dict[str, Any]] = []

    # 1. the four decision domains, in full, with citations
    for key in PAID_ASPECTS:
        a = aspects.get(key)
        if not a or not (a.get("summary") or "").strip():
            continue
        future.append({
            "title": a.get("title") or key.title(),
            "kind": "domain",
            "tags": _aspect_tags(a),
            "body": devoice(a["summary"]),
            "source": "",
        })

    # 2. dated markings that still lie ahead
    for p in future_events:
        future.append({
            "title": f"Age {p['age']} — {p.get('title', 'Your palm')}",
            "kind": "timeline", "age": p["age"], "body": devoice(p.get("text", "")),
        })

    seen = {f["title"] for f in future}
    for item in dom.get("numbered_checklist") or []:
        t = item.get("timing") or {}
        rng = t.get("age_range") or []
        est = t.get("estimated_age")
        # only genuinely forward-looking: the estimate itself must be ahead,
        # or (when undated) the whole range must start after today.
        ahead = (isinstance(est, int) and est > age) or (
            est is None and len(rng) == 2 and isinstance(rng[0], int) and rng[0] > age)
        if not ahead:
            continue
        conc = item.get("conclusive") or {}
        title = f"Age {est} — {item.get('title', 'Finding')}" if isinstance(est, int) \
            else item.get("title", "Finding")
        if title in seen:
            continue
        seen.add(title)
        cit = conc.get("citation") or {}
        future.append({
            "title": title, "kind": "timeline",
            "age": est if isinstance(est, int) else None,
            "ageRange": rng if len(rng) == 2 else None,
            "body": conc.get("verdict") or conc.get("conclusion") or item.get("finding", ""),
            "source": "",
        })

    # 3. special marks + remedial guidance. A fair/poor photo may still have
    # detector candidates internally, but they must not become customer claims.
    measurement_quality = (raw.get("reading_result") or {}).get("measurement_quality") or {}
    special_marks_allowed = bool(
        measurement_quality.get("special_marks_allowed",
                               str(measurement_quality.get("photo_grade") or "fair").lower() == "good")
    )
    marks = [m.get("statement") for m in (conf.get("marks") or [])
             if isinstance(m, dict) and m.get("statement")] if special_marks_allowed else []
    if marks:
        future.append({
            "title": "Remedies for your marks", "kind": "remedy",
            "tags": [f"{len(marks)} detected"], "body": devoice(" ".join(marks)), "source": "",
        })
    elif not special_marks_allowed:
        future.append({
            "title": "Fine markings and remedies", "kind": "remedy",
            "tags": ["photo confidence gate"],
            "body": "Fine palm markings are withheld because this photograph does not support reliable interpretation. A clearer image can unlock mark-specific guidance.",
            "source": "",
        })

    # 4. mount-by-mount analysis (palm_api's undated per-mount readings)
    mount_txt = [p.get("text", "") for p in undated if str(p.get("title", "")).startswith("Mount")]
    if mount_txt:
        future.append({
            "title": "Mount-by-mount analysis", "kind": "domain",
            "tags": [f"{len(mount_txt)} mounts"], "body": devoice(" ".join(mount_txt)), "source": "",
        })
    for p in undated:
        if str(p.get("title", "")).startswith("Mount"):
            continue
        future.append({"title": p.get("title", "Ahead of you"), "kind": "domain",
                       "body": p.get("text", "")})

    if not future:
        future = [{"title": "The road ahead",
                   "body": "Your major lines carry no further dated markings. The full report "
                           "covers the minor lines, mount signs and remedial guidance instead."}]

    quality = (dom.get("features") or {}).get("quality") or {}
    guidance = (dom.get("features") or {}).get("photo_guidance") or {}
    special_marks_allowed = bool(
        (raw.get("reading_result") or {}).get("measurement_quality", {}).get(
            "special_marks_allowed",
            str(quality.get("grade") or "fair").lower() == "good"
        )
    )

    nxt = future_events[0]["age"] if future_events else None
    domains = [f["title"] for f in future if f.get("kind") == "domain"][:4]
    if nxt:
        teaser = (f"Your palm carries a dated marking at about age {nxt}, plus full readings on "
                  + ", ".join(domains).lower() + ".")
    else:
        teaser = ("Your dated markings on the major lines sit behind you — what the full report opens is "
                  + ", ".join(domains).lower()
                  + (", your special marks with remedies, and a mount-by-mount analysis."
                     if special_marks_allowed else
                     ", a mount-by-mount analysis, and photo-quality guidance for fine markings."))

    return {
        "readingId": "RD-" + uuid.uuid4().hex[:7].upper(),
        "unlocked": False,
        "summary": conf.get("summary", ""),
        "scores": build_scores(dom, aspects),
        "past": past,
        "teaser": teaser,
        "future": future,
        "overlays": overlays,
        "meta": {
            "dominantHand": dom_key,
            "handType": ((dom.get("features") or {}).get("morphology") or {}).get("hand_type"),
            "photoQuality": quality.get("grade"),
            "photoScore": quality.get("score"),
            "photoAdvice": guidance.get("suggestions") or [],
            "notDetected": dom.get("not_detected") or [],
            "rulesSearched": raw.get("corpus_rules"),
            "pastCount": len(past_events),
            "futureCount": len(future),
            "datedAhead": len(future_events),
            "paidSections": [f["title"] for f in future],
        },
    }




def _blur(text: str, words: int = 18) -> str:
    """Only a teaser of each paid section ever leaves the server."""
    parts = (text or "").split()
    return " ".join(parts[:words]) + ("…" if len(parts) > words else "")


def build_palm_reading(raw: dict, p: dict, overlays: dict) -> dict:
    """
    Returns:
      { "public": free payload for the browser,
        "paid":   full future sections (object storage),
        "_meta":  what to persist on the report row }
    """
    req = _Req(p)
    reading = build_reading(raw, req, overlays)
    full_future = reading["future"]
    locked = []
    for f in full_future:
        item = {k: f.get(k) for k in ("title", "kind", "age", "ageRange", "tags")
                if f.get(k)}
        item["body"] = _blur(f.get("body", ""))
        locked.append(item)

    public = {k: v for k, v in reading.items() if k != "future"}
    public["future"] = locked
    return {
        "public": public,
        "paid": {"future": full_future},
        "_meta": {"scores": reading.get("scores"), "summary": reading.get("summary"),
                  "meta": reading.get("meta"), "past": reading.get("past"),
                  "teaser": reading.get("teaser"),
                  "paidSections": [f["title"] for f in full_future],
                  "futureLocked": locked},
    }


# ---------------------------------------------------------------------------
# HTML halves (pipeline template → iframe delivery, same shape as astrology)
# ---------------------------------------------------------------------------
def _scrub_palm_html(html: str) -> str:
    """Customer-facing gate: no citations, no machinery talk.

    The scrubbers are prose cleaners and will happily rewrite a stylesheet:
    one of them de-stutters repeated words, which quietly turned
    `grid-template-columns:1fr 1fr` into `1fr`. `report_render.clean` already
    stashes style and script blocks for exactly this reason, so do the same
    around the voice pass that runs before it.
    """
    out = re.sub(r'<ul class="aspect-cites">.*?</ul>', "", html or "",
                 flags=re.S | re.I)

    keep: List[str] = []

    def _stash(m: "re.Match[str]") -> str:
        keep.append(m.group(0))
        return f"\x00KEEP{len(keep) - 1}\x00"

    out = re.sub(r"<(style|script)\b.*?</\1>", _stash, out, flags=re.S | re.I)
    try:
        import astro_voice as V
        out = V.strip_citations(V.strip_machinery(out), hide_system_names=True)
        out = V.concise(out)
    except Exception:                                                 # noqa: BLE001
        pass
    for i, block in enumerate(keep):
        out = out.replace(f"\x00KEEP{i}\x00", block)

    try:
        from report_render import clean as rd_clean
        out = rd_clean(out)
    except Exception:                                                 # noqa: BLE001
        pass
    try:
        from palm_api import palm_voice as PV
        out = PV.polish_html(out)
    except Exception:                                                 # noqa: BLE001
        pass
    return out


FREE_SECTIONS = [
    "Both palms, as the engine read them",
    "What your hands say you are",
    "Every life area, and which way it leans",
    "Left hand against right hand",
    "Your hand, read to today",
]

PAID_SECTIONS = [
    "Why each life area reads the way it does",
    "Every dated marking ahead of you",
    "The line-by-line analysis, both hands",
    "Mount by mount",
    "What your special marks mean",
    "Remedies keyed to your hand",
]


def _teaser(n_areas: int, n_ahead: int, n_points: int, *, special_marks_allowed: bool = True) -> str:
    """Shown by palmPayCard on the site, so it has to stand on its own.

    It used to promise only the dated markings still ahead, which read as an
    empty offer for anyone whose markings all sit behind them. The working
    behind the verdicts is the part that is always there to sell.
    """
    parts = [f"the chart working behind all {n_areas} verdicts"] if n_areas else []
    if n_ahead:
        parts.append(f"{n_ahead} dated marking{'s' if n_ahead != 1 else ''} still ahead of you")
    if n_points:
        parts.append(f"the line-by-line reading of all {n_points} numbered points")
    if not parts:
        if special_marks_allowed:
            return ("The full reading opens the working behind every verdict, your "
                    "mounts, your marks and the remedies keyed to them.")
        return ("The full reading opens the working behind every verdict, your "
                "mounts, and the detailed reading supported by your photo quality.")
    return "The full reading opens " + ", ".join(parts) + "."


def build_palm_html_reading(raw: dict, p: dict, *,
                            price: int = 499) -> Tuple[str, str, dict]:
    """
    Build free/paid HTML for one palm reading.

    Returns (free_html, paid_html, meta) — same contract as report_render.*.
    Rendered twice against the same analysis rather than split, because the
    paywall sits inside each life-area card: the verdict is free and the working
    under it is not. Overlays are embedded as data URIs so each half is a
    standalone document inside the site iframe.
    """
    from . import palm_cards as PC

    req = _Req(p)
    age = req.age
    name = req.name or "Seeker"

    conf = raw.get("confluence") or {}
    dom_key = conf.get("dominant_hand") or req.dominant
    dom = raw.get(dom_key) or raw.get("right") or raw.get("left") or {}

    aspects = conf.get("life_aspects") or []
    dom_items = _customer_numbered(dom)
    dated = [(i.get("timing") or {}).get("estimated_age") for i in dom_items
             if i.get("kind") == "line"]
    dated = [a for a in dated if isinstance(a, int)]
    behind = [a for a in dated if a <= age]
    ahead = [a for a in dated if a > age]
    n_points = sum(len(_customer_numbered(raw.get(h) or {}))
                   for h in ("left", "right"))

    # LLM prose layer — facts in, structured prose out (off unless configured).
    prose_overlay: dict = {}
    llm_meta: dict = {"enabled": False}
    facts_payload: dict = {}
    try:
        import sys
        from pathlib import Path
        # engines/astro is on the worker path; llm lives under it.
        eng = Path(__file__).resolve().parents[1] / "engines" / "astro"
        if str(eng) not in sys.path:
            sys.path.insert(0, str(eng))
        from llm.facts import build_palm_facts, project_for_access, public_fact_payload
        from llm.humanize import humanize
        # Ensure reading_result is present for the fact builder.
        if "reading_result" not in raw:
            try:
                from palm_api.reading_result import build_reading_result
                raw = dict(raw)
                raw["reading_result"] = build_reading_result(
                    raw, person={"name": name, "age": age},
                    active_hand=dom_key)
            except Exception:  # noqa: BLE001
                pass
        age_band = "adult"
        if age < 13:
            age_band = "child"
        elif age < 18:
            age_band = "teen"
        elif age < 25:
            age_band = "young_adult"
        pfacts_paid = build_palm_facts(
            raw, name=name, access="paid", age_band=age_band, age_years=age)
        pfacts_free = project_for_access(pfacts_paid, "free")
        facts_payload = public_fact_payload(pfacts_paid)
        free_llm = humanize("palm", pfacts_free, access="free")
        paid_llm = humanize("palm", pfacts_paid, access="paid")
        prose_overlay = {
            "free": free_llm.get("overlay") or {},
            "paid": paid_llm.get("overlay") or {},
        }
        llm_meta = {
            "enabled": bool(paid_llm.get("enabled") or free_llm.get("enabled")),
            "stats": paid_llm.get("stats") or {},
            "free": {"stats": free_llm.get("stats") or {},
                     "fallback_used": bool(free_llm.get("fallback_used"))},
            "paid": {"stats": paid_llm.get("stats") or {},
                     "fallback_used": bool(paid_llm.get("fallback_used"))},
        }
    except Exception as exc:  # noqa: BLE001
        print(f"[palm_report] llm humanize skipped: {exc}", flush=True)

    common = dict(name=name, age=age, gender=req.gender,
                  dominant=req.dominant, price=price)

    def _render_palm(paid: bool) -> str:
        from . import palm_conversational as PConv
        prose = (prose_overlay.get("paid" if paid else "free", {})
                 if isinstance(prose_overlay, dict) else {})
        if not isinstance(prose, dict):
            prose = {}
        return PConv.render(raw, paid=paid, prose=prose, **common)

    free_html = _scrub_palm_html(_render_palm(False))
    paid_html = _scrub_palm_html(_render_palm(True))

    quality = (dom.get("features") or {}).get("quality") or {}
    guidance = (dom.get("features") or {}).get("photo_guidance") or {}
    special_marks_allowed = bool(
        (raw.get("reading_result") or {}).get("measurement_quality", {}).get(
            "special_marks_allowed",
            str(quality.get("grade") or "fair").lower() == "good",
        )
    )

    meta = {
        # The renderer that actually ran. Every palm reading goes through the
        # conversational template — the model only supplies wording inside it,
        # and whether it did is recorded under "llm" below, not here.
        "design": "conversational-v1",
        "dominantHand": dom_key,
        "handType": ((dom.get("features") or {}).get("morphology") or {}).get("hand_type"),
        "photoQuality": quality.get("grade"),
        "photoScore": quality.get("score"),
        "photoAdvice": guidance.get("suggestions") or [],
        "summary": conf.get("summary", ""),
        "teaser": _teaser(len(aspects), len(ahead), n_points, special_marks_allowed=special_marks_allowed),
        "freeSections": list(FREE_SECTIONS),
        "paidSections": list(PAID_SECTIONS),
        "pastCount": len(behind),
        "futureCount": len(ahead),
        "datedAhead": len(ahead),
        "scores": build_scores(dom, {a.get("key"): a for a in aspects}),
        "llm": llm_meta,
        "_facts": facts_payload,
    }
    return free_html, paid_html, meta
