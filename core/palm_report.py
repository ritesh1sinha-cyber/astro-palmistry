"""
palm_report.py — turns the palm engine's raw analysis into the reading a person
reads, split into a free half and a paid half.

Two delivery shapes:
  • build_palm_reading      — legacy JSON for the old in-page card UI
  • build_palm_html_reading — HTML halves from palm_api's report template
                             (same iframe path astrology already uses)
"""

from __future__ import annotations

import copy
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple


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
    if life.get("depth") and heart.get("quality"):
        spec = (f" Your life line runs <b>{prose(life['depth'])}</b> and your heart line reads "
                f"<b>{prose(heart['quality'])}</b>")
        if head.get("start_relation"):
            spec += f", while your head line begins <b>{prose(head['start_relation'])}</b>"
        spec += " — no two people carry that combination the same way."

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

    return [
        {"k": "Vitality",  "v": blend("life",  "health", "venus")},
        {"k": "Intellect", "v": blend("head",  "mind",   "mercury")},
        {"k": "Emotion",   "v": blend("heart", "love",   "moon")},
        {"k": "Fortune",   "v": blend("fate",  "career", "jupiter")},
    ]


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


# ---------------------------------------------------------------------------
# FREE vs PAID policy
# ---------------------------------------------------------------------------
# A purely age-based split breaks down for older users: palm_api's dated
# markings cluster where the detected points fall on the lines, so a 40-year-old
# can have every dated event behind them and nothing left to sell. So the split
# is by VALUE, with the timeline still honouring "read up to today":
#
#   FREE  — proof + identity: scores, both overlays, who you are (character,
#           mind), left-vs-right comparison, and every dated marking up to the
#           user's current age.
#   PAID  — the four decision domains people actually pay for (love, career,
#           wealth, health), special marks + remedies, mount-by-mount analysis,
#           and every dated marking that still lies ahead.
#
# This holds up at any age: a 22-year-old and a 55-year-old both get a
# substantial free reading and a substantial paid report.
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

    # 3. special marks + the remedial guidance attached to them
    marks = [m.get("statement") for m in (conf.get("marks") or []) if m.get("statement")]
    if marks:
        future.append({
            "title": "Remedies for your marks", "kind": "remedy",
            "tags": [f"{len(marks)} detected"], "body": devoice(" ".join(marks)), "source": "",
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

    nxt = future_events[0]["age"] if future_events else None
    domains = [f["title"] for f in future if f.get("kind") == "domain"][:4]
    if nxt:
        teaser = (f"Your palm carries a dated marking at about age {nxt}, plus full readings on "
                  + ", ".join(domains).lower() + ".")
    else:
        teaser = ("Your dated markings on the major lines sit behind you — what the full report opens is "
                  + ", ".join(domains).lower()
                  + ", your special marks with remedies, and a mount-by-mount analysis.")

    quality = (dom.get("features") or {}).get("quality") or {}
    guidance = (dom.get("features") or {}).get("photo_guidance") or {}

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
    """Customer-facing gate: no citations, no machinery talk."""
    out = re.sub(r'<ul class="aspect-cites">.*?</ul>', "", html or "",
                 flags=re.S | re.I)
    try:
        import astro_voice as V
        out = V.strip_citations(V.strip_machinery(out), hide_system_names=True)
    except Exception:                                                 # noqa: BLE001
        pass
    try:
        from report_render import clean as rd_clean
        out = rd_clean(out)
    except Exception:                                                 # noqa: BLE001
        pass
    return out


def _filter_aspects(conf: dict, keys: tuple) -> list:
    return [a for a in (conf.get("life_aspects") or []) if a.get("key") in keys]


def _analysis_for_free(raw: dict, age: int) -> dict:
    """Proof + identity: free aspects, left-vs-right, dated markings up to today."""
    out = copy.deepcopy(raw)
    conf = dict(out.get("confluence") or {})
    conf["life_aspects"] = _filter_aspects(conf, FREE_ASPECTS)
    preds = conf.get("predictions") or []
    conf["predictions"] = [
        p for p in preds
        if isinstance(p.get("age"), int) and p["age"] <= age
    ]
    conf["marks"] = []  # remedies sit behind the paywall
    out["confluence"] = conf
    return out


def _analysis_for_paid(raw: dict, age: int) -> dict:
    """Decision domains, forward markings, marks/remedies, mount readings."""
    out = copy.deepcopy(raw)
    # Per-hand overlays + numbered points already appear on the free half.
    out["left"] = None
    out["right"] = None
    conf = dict(out.get("confluence") or {})
    conf["life_aspects"] = _filter_aspects(conf, PAID_ASPECTS)
    preds = conf.get("predictions") or []
    conf["predictions"] = [
        p for p in preds
        if (isinstance(p.get("age"), int) and p["age"] > age)
        or not isinstance(p.get("age"), int)
    ]
    # Left-vs-right synthesis already sat on the free half.
    conf["lines"] = []
    conf["mounts"] = []
    # Summary belongs with the free orientation block.
    conf["summary"] = ""
    out["confluence"] = conf
    return out


def _paid_section_titles(raw: dict, age: int) -> List[str]:
    conf = raw.get("confluence") or {}
    titles: List[str] = []
    for a in _filter_aspects(conf, PAID_ASPECTS):
        t = (a.get("title") or a.get("key") or "").strip()
        if t:
            titles.append(t)
    for p in conf.get("predictions") or []:
        if isinstance(p.get("age"), int) and p["age"] > age:
            titles.append(f"Age {p['age']} — {p.get('title', 'Your palm')}")
        elif not isinstance(p.get("age"), int):
            titles.append(p.get("title") or "Ahead of you")
    if conf.get("marks"):
        titles.append("Remedies for your marks")
    # de-dupe, keep order
    seen, out = set(), []
    for t in titles:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _inject_before_body_end(html: str, snippet: str) -> str:
    """Place the paywall note inside .report-wrap, just before </body>."""
    if not snippet:
        return html
    m = re.search(r'</div>\s*</body\s*>', html or "", flags=re.I | re.S)
    if m:
        return html[:m.start()] + snippet + html[m.start():]
    m2 = re.search(r"</body\s*>", html or "", flags=re.I)
    if m2:
        return html[:m2.start()] + snippet + html[m2.start():]
    return (html or "") + snippet


def _locked_note_html(paid_sections: List[str], teaser: str) -> str:
    if not paid_sections:
        return ""
    items = "".join(f"<li><b>{re.sub(r'<[^>]+>', '', t)}</b></li>"
                    for t in paid_sections[:8])
    more = (f"<li>+ {len(paid_sections) - 8} more sections</li>"
            if len(paid_sections) > 8 else "")
    safe_teaser = re.sub(r"<[^>]+>", "", teaser or "")
    return f"""
<article class="report-card" style="border:1px dashed #c9a227;
background:rgba(201,162,39,.07)">
  <h2>{len(paid_sections)} more sections in the full report</h2>
  <p>{safe_teaser}</p>
  <ul>{items}{more}</ul>
</article>"""


def build_palm_html_reading(raw: dict, p: dict) -> Tuple[str, str, dict]:
    """
    Build free/paid HTML from the palm_api report template.

    Returns (free_html, paid_html, meta) — same contract as report_render.*.
    Overlays are embedded as data URIs so each half is a standalone document
    inside the site iframe (no extra signed image round-trips).
    """
    from palm_api.pipeline import render_lane_html

    req = _Req(p)
    age = req.age
    name = req.name or "Seeker"

    # Reuse the JSON path's teaser / section list so paywall copy stays consistent.
    sketch = build_reading(raw, req, overlays={})
    paid_sections = list(sketch.get("meta", {}).get("paidSections") or [])
    if not paid_sections:
        paid_sections = _paid_section_titles(raw, age)
    teaser = sketch.get("teaser") or ""

    free_raw = _analysis_for_free(raw, age)
    paid_raw = _analysis_for_paid(raw, age)

    free_html = render_lane_html(
        free_raw, client_name=name, embed_overlays=True)
    paid_html = render_lane_html(
        paid_raw, client_name=name, embed_overlays=True)

    free_html = _inject_before_body_end(
        free_html, _locked_note_html(paid_sections, teaser))

    free_html = _scrub_palm_html(free_html)
    paid_html = _scrub_palm_html(paid_html)

    # Mild title tweak on the paid half so the two iframes don't read identical.
    paid_html = paid_html.replace(
        "Palmistry analysis report", "Full palmistry reading", 1)

    dom_key = (raw.get("confluence") or {}).get("dominant_hand") or req.dominant
    dom = raw.get(dom_key) or raw.get("right") or raw.get("left") or {}
    quality = (dom.get("features") or {}).get("quality") or {}
    guidance = (dom.get("features") or {}).get("photo_guidance") or {}

    meta = {
        "dominantHand": dom_key,
        "handType": ((dom.get("features") or {}).get("morphology") or {}).get("hand_type"),
        "photoQuality": quality.get("grade"),
        "photoScore": quality.get("score"),
        "photoAdvice": guidance.get("suggestions") or [],
        "summary": (raw.get("confluence") or {}).get("summary", ""),
        "teaser": teaser,
        "freeSections": [a.get("title") for a in _filter_aspects(
            raw.get("confluence") or {}, FREE_ASPECTS) if a.get("title")],
        "paidSections": paid_sections,
        "pastCount": sketch.get("meta", {}).get("pastCount"),
        "futureCount": sketch.get("meta", {}).get("futureCount"),
        "datedAhead": sketch.get("meta", {}).get("datedAhead"),
        "scores": sketch.get("scores"),
    }
    return free_html, paid_html, meta
