"""palm_cards.py — the palm reading in the cards-v2 language.

The palm report used to render through `palm_api.pipeline.render_lane_html`,
which carries its own Georgia/blue stylesheet and has no `paid` flag: the two
halves were produced by deep-copying the analysis and deleting fields from each
copy. That approach put the whole numbered-point list — every finding with its
estimated age — on the free side, and took the customer's own annotated
photographs off the paid side.

So this module renders the same analysis twice, branching on `paid`, in the
shared dialect from `report_shell`. Free carries the photographs, the four
scores, the eight life-area verdicts and every dated marking the reader has
already lived through; paid adds the working behind each verdict, the markings
still ahead, the mounts, what the marks mean, hand-specific remedies (do/don't),
and the numbered points.
"""

from __future__ import annotations

import html as _html
import re
from typing import Any, List, Optional


def _palm_quality(hand: dict[str, Any]) -> dict[str, Any]:
    """Return the strongest available photo-quality gate for this hand."""
    q = dict((hand.get("features") or {}).get("quality") or {})
    # Some pipeline versions keep the authoritative measurement gate outside
    # features. Prefer that value when present so a Fair/Poor photo cannot be
    # re-enabled by a stale hand-level quality object.
    for source in (hand.get("measurement_quality"), hand.get("quality")):
        if isinstance(source, dict):
            q.update(source)
    return q


def _palm_special_marks_allowed(hand: dict[str, Any]) -> bool:
    """Single renderer-level source of truth for fine-mark visibility.

    Fair/Poor photos are fail-closed. The numbered-point renderer must obey the
    same gate as the special-mark/remedy cards even if an older detector still
    emitted a mark candidate.
    """
    q = _palm_quality(hand)
    if "special_marks_allowed" in q:
        return bool(q.get("special_marks_allowed"))
    return str(q.get("grade") or q.get("photo_grade") or "").lower() == "good"


def _is_special_mark_item(item: dict[str, Any]) -> bool:
    text = " ".join(str(item.get(k, "")) for k in (
        "kind", "category", "type", "id", "key", "title", "text", "statement", "finding"
    )).lower()
    return any(token in text for token in (
        "trident", "trishul", "star mark", "grille", "fish mark",
        "triangle mark", "special_mark", "special mark"
    ))


def _hand_for_customer_filter(raw: dict[str, Any], hand_key: str) -> dict[str, Any]:
    """Attach the reading-level measurement gate onto a hand before filtering."""
    hd = dict(raw.get(hand_key) or {})
    mq = (raw.get("reading_result") or {}).get("measurement_quality") or {}
    if isinstance(mq, dict) and mq:
        hd["measurement_quality"] = mq
    return hd


def _filter_customer_numbered(hand: dict[str, Any]) -> list[dict[str, Any]]:
    items = list(hand.get("numbered_checklist") or [])
    if _palm_special_marks_allowed(hand):
        return items
    quality = _palm_quality(hand)
    try:
        from palm_api.quality_gate import filter_special_mark_findings
        items = filter_special_mark_findings(items, quality)
    except Exception:
        pass
    # Always apply a local fail-closed filter after the shared gate. This
    # protects against detector versions whose classifier does not recognise a
    # newly named special mark (e.g. a Trishul item labelled only by title).
    return [i for i in items if not _is_special_mark_item(i)]

# Palmistry strength is a confidence level, not a direction, so it maps onto the
# pill colours differently from the chart report's up/down/mixed verdicts.
STRENGTH_PILL = {"strong": "up", "moderate": "mixed", "tentative": "faint"}
STRENGTH_LABEL = {"strong": "Strong signal", "moderate": "Moderate",
                  "tentative": "Tentative"}


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))

def _human_palm_title(title: Any) -> str:
    """Customer-facing palm domain labels; never assume marriage status."""
    raw = str(title or "").strip()
    replacements = {
        "Love, Marriage & Emotions": "Relationships & Emotions",
        "Love & Marriage": "Relationships & Partnership",
        "Career & Destiny": "Career & Direction",
        "Wealth & Fortune": "Money & Resources",
    }
    return replacements.get(raw, raw)


def _first(name: str) -> str:
    n = (name or "").strip().split()
    return n[0] if n else "friend"


def _bar(value: Any) -> str:
    try:
        pct = max(0, min(100, int(value)))
    except (TypeError, ValueError):
        pct = 0
    return f'<div class="bar"><span style="width:{pct}%"></span></div>'


# ---------------------------------------------------------------------------
# blocks
# ---------------------------------------------------------------------------
def _data_uri(overlay_path: Optional[str]) -> str:
    """Overlays are embedded, not linked: each half is served as a standalone
    document through /api/file/{token}, so a storage key would not resolve."""
    if not overlay_path:
        return ""
    from pathlib import Path
    p = Path(overlay_path)
    if not p.is_file():
        return ""
    # A pair of full-resolution overlays can make an iframe document several
    # megabytes long. Some phone browsers then paint the first image and silently
    # abandon the second. Embed a display-sized JPEG instead; the original stays
    # in object storage for the archive.
    data = p.read_bytes()
    try:
        from io import BytesIO
        from PIL import Image

        with Image.open(BytesIO(data)) as image:
            image = image.convert("RGB")
            image.thumbnail((900, 1200))
            out = BytesIO()
            image.save(out, format="JPEG", quality=82, optimize=True)
            data = out.getvalue()
    except Exception:  # Pillow is optional; a valid original still renders.
        pass
    import base64
    return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")


def _photos(raw: dict, dom_key: str) -> str:
    figs = ""
    for hand in ("left", "right"):
        src = _data_uri((raw.get(hand) or {}).get("overlay_path"))
        role = "dominant — what you have made of it" if hand == dom_key \
            else "innate — what you were handed"
        if src:
            visual = (f'<img src="{src}" alt="{hand} palm with the '
                      f'detected lines drawn on"/>')
        else:
            # Do not make a missing overlay look like a missing upload. The
            # reader needs a visible explanation and a retake path, not a
            # mysteriously incomplete two-hand report.
            visual = (f'<div class="palm-img-missing" role="img" aria-label="'
                      f'{hand} palm overlay could not be prepared">Annotated '
                      f'{hand} palm image unavailable. Please retake this hand '
                      f'in bright, even light.</div>')
        figs += (f'<figure>{visual}'
                 f'<figcaption>{hand.title()} hand · {role}</figcaption></figure>')
    return f"""
<div class="palm-shots">
  <div class="ev-label">Your palms, as the engine read them</div>
  <div class="palm-imgs">{figs}</div>
  <p class="fine">These are your own photographs with the lines this reading is
  built from drawn on top. If a hand is unavailable or a line looks wrong,
  retake that photo in bright, even light and run the reading again.</p>
</div>"""


def _quality(dom: dict) -> str:
    feats = dom.get("features") or {}
    q = feats.get("quality") or {}
    grade = str(q.get("grade") or "fair").lower()
    if grade == "good":
        return ""
    if grade == "poor":
        return f"""
<div class="card">
  <div class="ev-label">About your photos</div>
  <p class="claim">Some fine palm details could not be measured reliably.</p>
  <p class="fine">This reading keeps the broad, visible patterns but withholds special marks
  and age-position timing from an unclear photograph. For a deeper reading, retake the
  palm straight-on in bright, even light with the full palm and fingers visible.</p>
</div>"""
    advice = ((feats.get("photo_guidance") or {}).get("suggestions") or [])[:3]
    tips = ("<ul>" + "".join(f"<li>{_e(a)}</li>" for a in advice) + "</ul>") if advice else ""
    return f"""
<div class="card">
  <div class="ev-label">About your photos</div>
  <p class="claim">Photo grade {_e(grade)}.</p>
  <p class="fine">The main patterns can still be read, but fine marks and age positions are less certain.
  We have deliberately widened the timing windows rather than implying false precision.</p>
  {tips}
</div>"""


def _scores(scores: List[dict]) -> str:
    if not scores:
        return ""
    rows = "".join(f"""
    <li><span>{_e(s.get('k'))}</span>{_bar(s.get('v'))}<b>{_e(s.get('v'))}</b></li>"""
                   for s in scores)
    return f"""
<div class="card">
  <div class="ev-label">Measured from your palms</div>
  <ul class="palm-scores">{rows}</ul>
</div>"""


def _opening(text: str) -> str:
    if not text:
        return ""
    # palm_opening() emits its own <b> emphasis, so this one is not escaped.
    return f"""
<div class="card persona">
  <div class="ev-label">What your hands say you are</div>
  <p class="claim">{text}</p>
</div>"""


def _unique_texts(values: list[str], limit: int = 5) -> list[str]:
    """Stable, lightweight de-duplication for human recognition cues."""
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if not text:
            continue
        key = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def _recognition_block(a: dict) -> str:
    cues = _unique_texts(list(a.get("recognize") or []), limit=4)
    if not cues:
        return ""
    rows = "".join(f"<li>{_e(x)}</li>" for x in cues)
    return f"""
<div class="recognition-box">
  <strong>You may recognize this as</strong>
  <ul>{rows}</ul>
</div>"""


def _technical_evidence(a: dict, *, paid: bool) -> str:
    pts = [p for p in (a.get("points") or []) if (p.get("text") or "").strip()]
    if not pts:
        return ""
    if not paid:
        n = len(pts)
        return f"""
<details class="technical-evidence locked-inline">
  <summary>Why Graharekha says this</summary>
  <p><span class="lockicon">&bull;</span> {n} measured palm finding{"s" if n != 1 else ""} support this interpretation.
  The detailed evidence is in the full reading.</p>
</details>"""

    rows = ""
    for p in pts:
        evidence = str(p.get("text") or "").strip()
        if not evidence:
            continue
        confirmation = (' <b class="both">&#10003; both hands</b>' if p.get("reinforced") else "")
        rows += f"""
<div class="evidence-row">
  <div class="evidence-meaning"><b>{_e(evidence)}</b>{confirmation}</div>
</div>"""
    if not rows:
        return ""
    return f"""
<details class="technical-evidence">
  <summary>Why Graharekha says this</summary>
  <p class="sec-note">The supporting observations are shown in everyday language.
  Traditional source text and internal rule identifiers are kept out of the customer reading.</p>
  <div>{rows}</div>
</details>"""


def _aspect_card(a: dict, *, paid: bool, prose: dict | None = None) -> str:
    pts = [p for p in (a.get("points") or []) if (p.get("text") or "").strip()]
    summary = str(a.get("what_it_means") or a.get("summary") or "").strip()
    llm = prose or {}
    llm_headline = (llm.get("headline") or "").strip()
    llm_why = (llm.get("why") or "").strip()
    if llm_headline:
        summary = llm_headline
    both = sum(1 for p in pts if p.get("reinforced"))
    strength = str(a.get("strength") or "")
    pill_cls = STRENGTH_PILL.get(strength, "faint")
    pill_txt = STRENGTH_LABEL.get(strength, strength.title() or "Read")
    agree = f'<span class="agree">{both} on both hands</span>' if both else ""
    recognition = _recognition_block(a)
    technical = _technical_evidence(a, paid=paid)
    why_html = (
        f'<p class="pred-why"><b>Why:</b> {_e(llm_why)}</p>' if llm_why else ""
    )

    return f"""
<article class="card" data-verdict="{_e(strength)}">
  <div class="card-top"><span class="area">{_e(_human_palm_title(a.get("title")))}</span>
    <span class="pill {pill_cls}">{_e(pill_txt)}</span></div>
  {f'<p class="claim">{_e(summary)}</p>' if summary else ''}
  {why_html}
  {agree}
  {recognition}
  {technical}
</article>"""


def _top_recognition(aspects: list[dict]) -> str:
    """Five high-signal, cross-life-area observations for immediate self-check."""
    candidates: list[tuple[str, str, str]] = []
    for a in aspects:
        title = str(a.get("title") or "").strip()
        family = str(a.get("key") or a.get("title") or "").strip()
        for cue in a.get("recognize") or []:
            text = str(cue or "").strip()
            if text:
                candidates.append((family, title, text))

    selected: list[tuple[str, str, str]] = []
    seen_families: set[str] = set()
    seen_text: set[str] = set()
    # Prefer strong/moderate areas first, while limiting one dominant life area
    # from taking over the opening.
    ranked = sorted(
        candidates,
        key=lambda x: next(
            (0 if str(a.get("key")) == x[0] and a.get("strength") == "strong"
             else 1 if str(a.get("key")) == x[0] and a.get("strength") == "moderate"
             else 2)
            for a in aspects if str(a.get("key")) == x[0]
        ),
    )
    for family, title, text in ranked:
        norm = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
        if norm in seen_text:
            continue
        # First pass: one cue per life area. This makes the opening a broad
        # "does this sound like me?" check rather than five versions of career.
        if family in seen_families:
            continue
        seen_families.add(family)
        seen_text.add(norm)
        selected.append((family, title, text))
        if len(selected) >= 5:
            break

    if len(selected) < 5:
        for family, title, text in ranked:
            norm = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
            if norm in seen_text:
                continue
            seen_text.add(norm)
            selected.append((family, title, text))
            if len(selected) >= 5:
                break

    if not selected:
        return ""

    rows = "".join(
        f'<li><span class="top-recognition-area">{_e(title)}</span> — {_e(text)}</li>'
        for _, title, text in selected
    )
    return f"""
<section class="top-recognition">
  <h3>5 things you may recognize about yourself</h3>
  <p class="sec-note">Use these as a reality check. They are life-pattern
  observations, not guaranteed events.</p>
  <ol>{rows}</ol>
</section>
"""

def _hands_compare(conf: dict) -> str:
    rows = ""
    for li in conf.get("lines") or []:
        # The life-area cards already state the stable traits. This comparison
        # earns its place only where the innate and developed hands differ.
        if not li.get("statement") or li.get("agreement") == "reinforced":
            continue
        rows += (f'<li><b>{_e(li.get("title"))}</b>'
                 f'{_scenario_why_html(li.get("statement") or "")}</li>')
    if not rows:
        return ""
    return f"""
<h3 class="sec">What may have changed with age</h3>
<p class="sec-note">Your non-dominant hand is treated as the underlying tendency, while
your dominant hand reflects how life has shaped or expressed it. Where they differ,
that difference is the most personal part of the reading.</p>
<div class="card"><ul class="palm-list">{rows}</ul></div>"""


def _verdict(item: dict) -> str:
    conc = item.get("conclusive") or {}
    txt = (conc.get("verdict") or conc.get("conclusion")
           or item.get("finding") or "").strip()
    # conclusive.py labels every non-line verdict "Reading for you: ...", which
    # reads as a form field once the sentence sits under its own heading.
    txt = re.sub(r"^Reading for you:\s*", "", txt, flags=re.I)
    return txt[:1].upper() + txt[1:] if txt else ""


def _scenario_why_html(text: str, *, title: str = "") -> str:
    """Turn 'scenario\\nWhy: backing' (or '… Why: …') into styled HTML chips."""
    raw = (text or "").strip()
    if not raw:
        return ""
    # Split on Why even mid-paragraph ("…now. Why: mark on …") — common in
    # palm confluence statements that were never HTML-formatted.
    m = re.split(r"(?i)(?:\r?\n|\s+)Why:\s*", raw, maxsplit=1)
    if len(m) == 2:
        scenario, why = m[0].strip(), m[1].strip()
    elif re.match(r"(?i)^Why:\s*", raw):
        scenario, why = "", re.sub(r"(?i)^Why:\s*", "", raw).strip()
    else:
        scenario, why = raw, ""
    # Drop a trailing period dangling before Why was chopped off.
    scenario = scenario.rstrip()
    head = ""
    if title and scenario:
        head = f'<p class="pred-scenario"><b>{_e(title)}</b> — {_e(scenario)}</p>'
    elif title and not scenario:
        head = f'<p class="pred-scenario"><b>{_e(title)}</b></p>'
    elif scenario:
        head = f'<p class="pred-scenario">{_e(scenario)}</p>'
    why_html = (f'<p class="pred-why"><b>Why:</b> {_e(why)}</p>' if why else "")
    return head + why_html


def _est_age(item: dict) -> Optional[int]:
    age = (item.get("timing") or {}).get("estimated_age")
    return age if isinstance(age, int) else None


def _read_to_today(items: List[dict], *, first: str, age: int) -> str:
    """The credibility block.

    Two kinds of proof, and it deliberately does not depend on the dated ones.
    The engine only dates points on the four major lines — typically four in a
    whole hand — so a reader younger than their first dated marking would get an
    empty block, losing the one argument that earns the click. Hand shape, thumb
    and fingers are always there and the reader can check every one of them by
    looking down.
    """
    shape = [i for i in items if i.get("kind") in ("morphology", "thumb", "finger")]
    behind = sorted([i for i in items
                     if i.get("kind") == "line" and (_est_age(i) or 10**6) <= age],
                    key=lambda i: _est_age(i) or 0)
    if not shape and not behind:
        return ""

    rows = "".join(
        f'<li><span class="tick">&#10003;</span>'
        f'<div><b>{_e(i.get("title"))}</b>{_scenario_why_html(_verdict(i))}</div></li>'
        for i in shape)
    rows += "".join(
        f'<li><span class="tick">&#10003;</span>'
        f'<div><b>{_e(i.get("title"))}, around age {_e(_est_age(i))}</b>'
        f'{_scenario_why_html(_verdict(i))}</div></li>'
        for i in behind)

    dated_note = (f" The last {len(behind)} sit at points on your lines that map "
                  f"to years you have already lived." if behind else "")
    return f"""
<div class="proof">
  <div class="ev-label">Your hand, read to today</div>
  <h3>{_e(first)}, check these against your own hand</h3>
  <p>You have told us nothing except your age, and shown us two photographs.
  Everything below was measured off them.{dated_note} If most of it does not fit,
  treat that as useful feedback rather than forcing a match. If most of it does fit,
  the same measurements are what the rest of the reading is built on.</p>
  <ul class="hits">{rows}</ul>
</div>"""


def _mark_zone_plain(zone: str) -> str:
    try:
        from palm_api import palm_voice as PV
        return PV._mount_name((zone or "palm").lower())
    except Exception:  # noqa: BLE001
        return "your palm"


def _marks(dom: dict, conf: dict, *, paid: bool) -> str:
    feats = dom.get("features") or {}
    quality = feats.get("quality") or {}
    if not bool(quality.get("special_marks_allowed", str(quality.get("grade") or "").lower() == "good")):
        return ""
    raw_marks = feats.get("special_marks") or []
    if not raw_marks and not (conf.get("marks") or []):
        return ""
    if paid:
        mark_rows = [m for m in (conf.get("marks") or []) if m.get("statement")]
        if mark_rows:
            rows = "".join(
                f'<li>{_scenario_why_html(m.get("statement") or "")}</li>'
                for m in mark_rows)
        else:
            rows = "".join(
                f'<li><p class="pred-scenario"><b>{_e(m.get("title"))}</b> — '
                f'{_e(m.get("meaning"))}</p>'
                f'<p class="pred-why"><b>Why:</b> mark on '
                f'{_e(_mark_zone_plain(str(m.get("zone", "palm"))))}</p></li>'
                for m in raw_marks)
        return f"""
<h3 class="sec">Your special marks, and what they add</h3>
<p class="sec-note">A special mark is treated as a modifier, not a standalone promise.
Its meaning is read together with the surrounding lines, mounts and both-hand comparison.</p>
<div class="card"><ul class="palm-list">{rows}</ul></div>"""

    named = "".join(
        f'<li><b>{_e(m.get("title"))}</b> on '
        f'{_e(_mark_zone_plain(str(m.get("zone", "palm"))))}</li>'
        for m in raw_marks)
    if not named:
        return ""
    n = len(raw_marks)
    return f"""
<h3 class="sec">Your special marks</h3>
<p class="sec-note">These are the marks the image analysis could identify with enough confidence.
Their deeper interpretation is part of the full reading.</p>
<div class="card">
  <ul class="palm-list plain">{named}</ul>
  <div class="when locked-inline"><span class="lockicon">&bull;</span>
  {n} mark{'s' if n != 1 else ''} found. What each one does to the area it sits
  on, and the remedy attached to it, are in the full reading.</div>
</div>"""


def _ahead(items: List[dict], age: int) -> List[dict]:
    return sorted([i for i in items
                   if i.get("kind") == "line" and (_est_age(i) or -1) > age],
                  key=lambda i: _est_age(i) or 0)


def _timeline_ahead(ahead: List[dict]) -> str:
    if not ahead:
        return ""
    rows = "".join(f"""
<li>
  <div class="tl-when">Around age {_e(_est_age(i))}</div>
  <div class="tl-body"><b>{_e(i.get('title'))}</b>
  {_scenario_why_html(_verdict(i))}</div>
</li>""" for i in ahead)
    return f"""
<h3 class="sec">What is still ahead of you</h3>
<p class="sec-note">These ages come from the position of the marking on the line, not a calendar date.
Treat each one as an approximate life-stage window, not a fixed event date.</p>
<ol class="timeline">{rows}</ol>"""


def _mounts(conf: dict, items: List[dict]) -> str:
    rows = ""
    seen: set[str] = set()

    def add(text: str) -> bool:
        key = re.sub(r"\W+", " ", text.lower()).strip()
        if not key or key in seen:
            return False
        seen.add(key)
        return True

    for i in items:
        if i.get("kind") != "mount" or not _verdict(i):
            continue
        verdict = _verdict(i)
        if not add(verdict):
            continue
        rows += f'<li>{_scenario_why_html(verdict)}</li>'
    for mount in conf.get("mounts") or []:
        statement = str(mount.get("statement") or "")
        if add(statement):
            rows += f'<li>{_scenario_why_html(statement)}</li>'
    if not rows:
        return ""
    return f"""
<h3 class="sec">Mount by mount</h3>
<p class="sec-note">The raised and flat parts of the palm say where your energy
actually goes, independently of the lines crossing them.</p>
<div class="card"><ul class="palm-list">{rows}</ul></div>"""


def _remedies(dom: dict, conf: dict, *, paid: bool = False) -> str:
    """Do / don't — only corpus / coded mark rules (see palm_api.palm_remedies)."""
    try:
        from palm_api.palm_remedies import build_palm_remedies, format_remedy_line
    except Exception:  # noqa: BLE001
        return ""

    feats = dom.get("features") or {}
    quality = feats.get("quality") or {}
    grade = str(quality.get("grade") or "fair").lower()
    # Fine hand-specific remedies are paid depth and require a good photo.
    # Fair/poor images may still show the teaser, but must not produce a
    # concrete gemstone/practice recommendation from uncertain measurements.
    if grade != "good":
        if paid:
            return f"""
<h3 class="sec">Remedies for your hand</h3>
<div class="card">
  <p class="fine">Hand-specific remedies are withheld because this photograph
  is not clear enough to support fine-detail recommendations. Retake the palm
  straight-on in bright, even light for a deeper remedy reading.</p>
</div>"""
        return """
<h3 class="sec">Remedies for your hand</h3>
<p class="sec-note">Only when a classical palm rule applies to something we measured.</p>
<div class="card"><div class="when locked-inline"><span class="lockicon">&bull;</span>
Hand-specific remedies are part of the full reading when the photograph supports the underlying measurement.</div></div>"""
    items = build_palm_remedies(feats)
    dos = [format_remedy_line(r) for r in items if r.bucket == "do"][:6]
    donts = [format_remedy_line(r) for r in items if r.bucket == "dont"][:6]
    n = len(dos) + len(donts)
    if n == 0:
        if paid:
            return ""
        return """
<h3 class="sec">Remedies for your hand</h3>
<p class="sec-note">Only when a classical palm rule applies to something we measured.</p>
<div class="card"><div class="when locked-inline"><span class="lockicon">&bull;</span>
Any gem, metal, or practice tied to your mounts and marks is in the full reading.</div></div>"""

    if not paid:
        return f"""
<h3 class="sec">Remedies for your hand</h3>
<p class="sec-note">Only when a classical palm rule applies to something we measured.</p>
<div class="card"><div class="when locked-inline"><span class="lockicon">&bull;</span>
{n} rule-backed step{'s' if n != 1 else ''} sit in the full reading.</div></div>"""

    do_html = "".join(f"<li class=\"stone up\"><div class=\"stone-top\"><b>Do</b>"
                      f"<span class=\"stone-verdict\">What to do</span></div>"
                      f"<div class=\"stone-detail\">{_e(x)}</div></li>" for x in dos)
    dont_html = "".join(f"<li class=\"stone down\"><div class=\"stone-top\"><b>Don't</b>"
                        f"<span class=\"stone-verdict\">What to avoid</span></div>"
                        f"<div class=\"stone-detail\">{_e(x)}</div></li>" for x in donts)
    return f"""
<section class="remedy-card">
  <h3 class="sec">Remedies for your hand</h3>
  <p class="sec-note">These are traditional supportive practices tied to measured
  patterns in your hands. They are optional, not guarantees.</p>
  {f'''<div class="stones-group up">
    <div class="stones-group-label">Do · strengthen</div>
    <ul class="stones">{do_html}</ul>
  </div>''' if do_html else ''}
  {f'''<div class="stones-group down">
    <div class="stones-group-label">Don't · ease off</div>
    <ul class="stones">{dont_html}</ul>
  </div>''' if dont_html else ''}
  <p class="fine">Educational palmistry only. These are optional traditional practices,
  not guarantees or medical advice. Material remedies are shown only when the image
  is clear enough to support the underlying measurement.</p>
</section>"""


def _workings(raw: dict) -> str:
    """Every numbered point on both hands — the working the dots refer to."""
    blocks = ""
    for hand in ("right", "left"):
        hd = _hand_for_customer_filter(raw, hand)
        if not (raw.get(hand)):
            continue
        items = _filter_customer_numbered(hd)
        if not items:
            continue
        rows = ""
        for it in items:
            num = it.get("num", "?")
            conc = it.get("conclusive") or {}
            timing = it.get("timing") or {}
            when = ""
            if timing.get("estimated_age") is not None:
                rng = timing.get("age_range") or []
                age = timing["estimated_age"]
                when = (f'<span class="pt-when">approximately {_e(rng[0])}&ndash;{_e(rng[1])}</span>'
                        if len(rng) == 2 and rng[1] > rng[0] else
                        f'<span class="pt-when">around age {_e(age)}</span>')
            verdict = conc.get("verdict") or conc.get("conclusion") or it.get("finding", "")
            # Never expose raw classical/book wording from a numbered point.
            try:
                from qa_checks.customer_text_sanitizer import sanitize_customer_text
                verdict = sanitize_customer_text(
                    str(verdict), method_label="Palm evidence",
                    direction="neutral", area="inner",
                    seed=str(verdict)[:48])
            except Exception:
                pass
            body = _scenario_why_html(str(verdict))
            if not body:
                body = f'<p>{_e(verdict)}</p>'
            rows += (f'<li><b>Point {_e(num)} — {_e(it.get("title"))}</b>{when}'
                     f'{body}</li>')
        missing = hd.get("not_detected") or []
        note = (f'<p class="fine">Not visible on this photo: {_e(", ".join(missing))}.</p>'
                if missing else "")
        blocks += (f'<h4>{hand.title()} hand</h4>'
                   f'<ul class="palm-points">{rows}</ul>{note}')
    if not blocks:
        return ""
    return f"""
<details class="workings workings-main">
  <summary>Detailed line-by-line reading</summary>
  <div class="workings-body">
    <p>Each numbered point is explained in plain language below.</p>
    {blocks}
  </div>
</details>"""


# ---------------------------------------------------------------------------
# the document
# ---------------------------------------------------------------------------
def render(raw: dict, *, name: str = "Seeker", age: int = 30,
           gender: str = "other", dominant: str = "right",
           paid: bool = False, price: int = 298,
           prose: dict | None = None) -> str:
    """One palm reading, gated. Returns a standalone HTML document.

    ``prose`` is an optional LLM overlay: ``{opening, aspects:{key:{headline,why,points}}}``.
    """
    import report_shell as RS

    from .palm_report import _Req, build_scores, palm_opening

    prose = prose or {}
    prose_aspects = prose.get("aspects") if isinstance(prose, dict) else {}
    if not isinstance(prose_aspects, dict):
        prose_aspects = {}

    req = _Req({"name": name, "age": age, "gender": gender, "dominant": dominant})
    first = _first(name)

    conf = raw.get("confluence") or {}
    dom_key = conf.get("dominant_hand") or dominant
    dom = raw.get(dom_key) or raw.get("right") or raw.get("left") or {}
    # Propagate the authoritative measurement gate into the renderer's hand
    # object. This keeps Fair/Poor special-mark suppression consistent across
    # summary cards, numbered points, workings and remedies.
    dom = dict(dom)
    dom_features = dict(dom.get("features") or {})
    dom_quality = dict(dom_features.get("quality") or {})
    measurement_quality = (raw.get("reading_result") or {}).get("measurement_quality") or {}
    if isinstance(measurement_quality, dict):
        dom_quality.update(measurement_quality)
    dom_features["quality"] = dom_quality
    dom["features"] = dom_features

    aspects = conf.get("life_aspects") or []
    aspects_by_key = {a.get("key"): a for a in aspects}

    # Driven off the dominant hand's checklist rather than confluence
    # `predictions`, which drops the `kind` — without it the mounts, fingers,
    # thumb and hand shape have nowhere to go and fall out of both halves.
    dom_items = dom.get("numbered_checklist") or []
    ahead = _ahead(dom_items, age)
    # Hand dicts must stay dicts — `_filter_customer_numbered` expects a mapping.
    # Always merge the reading-level measurement gate so Fair/Poor photos cannot
    # leak special marks via a stale hand-level quality object.
    n_points = sum(
        len(_filter_customer_numbered(_hand_for_customer_filter(raw, h)))
        for h in ("left", "right")
    )

    cards = "".join(
        _aspect_card(a, paid=paid, prose=prose_aspects.get(a.get("key") or ""))
        for a in aspects
        if (a.get("points") or a.get("summary")))

    scores = build_scores(dom, aspects_by_key)
    llm_opening = (prose.get("opening") or "").strip()
    # Deterministic opening may contain intentional <b>; LLM prose is escaped.
    opening = _e(llm_opening) if llm_opening else palm_opening(req, dom)

    if paid:
        tail = (_timeline_ahead(ahead) + _mounts(conf, dom_items)
                + _marks(dom, conf, paid=True)
                + _remedies(dom, conf, paid=True)
                + _workings(raw))
    else:
        # The rest of the reading is titled and blurred, not bullet-pointed:
        # the free half keeps every paid section's real heading so it reads as
        # a blurred full document, and the bodies are non-personal placeholders
        # (the free path never holds the real paid content). One buy CTA.
        ahead_teaser = (
            f"{len(ahead)} dated marking{'s' if len(ahead) != 1 else ''} on "
            "your major lines."
            if ahead else
            "Where your lines still change, and roughly when.")
        points_teaser = (
            f"{n_points} numbered point{'s' if n_points != 1 else ''} across "
            "both hands, keyed to the dots on your photographs."
            if n_points else
            "Every line, mount, finger and mark, read one at a time.")
        tail = (_marks(dom, conf, paid=False)
                + RS.lock_sections([
                    ("Why each area reads the way it does",
                     f"The working behind all {len(aspects)} verdicts above — "
                     "the lines, mounts and marks that shape them."),
                    ("Every dated marking still ahead of you", ahead_teaser),
                    ("The line-by-line analysis, both hands", points_teaser),
                    ("Mount by mount",
                     "What the raised and flat mounts add, beyond the lines "
                     "crossing them."),
                    ("Your special marks, explained",
                     "Any mark on your palm, and what it does to the mount it "
                     "sits on."),
                    ("Remedies keyed to your own hand",
                     "Traditional supportive practices matched to what your "
                     "palm actually shows, not to your sign."),
                ])
                + RS.buy_block(
                    "See the pattern beneath the first reading",
                    "You have the part you can check against your own hands. "
                    "Unlock the supporting signs, forward age windows, marks "
                    "and hand-specific guidance.",
                    price=price))

    hand_type = ((dom.get("features") or {}).get("morphology") or {}).get("hand_type")
    sub = f"{age} years · {dom_key}-dominant · both palms analysed"
    if hand_type:
        sub += f" · {hand_type} hand"
    q_grade = str(((dom.get("features") or {}).get("quality") or {}).get("grade") or "").lower()
    if q_grade == "poor":
        sub += " · limited visual confidence"
    elif q_grade == "fair":
        sub += " · moderate visual confidence"

    body = (_photos(raw, dom_key)
            + _quality(dom)
            + _scores(scores)
            + _opening(opening)
            + _top_recognition(aspects)
            + '<h3 class="sec">What these signs may look like in your life</h3>'
              '<p class="sec-note">Start with the everyday meaning. Open '
              '<b>Why Graharekha says this</b> when you want the palm evidence '
              'behind it.</p>'
            + cards
            + _hands_compare(conf)
            + _read_to_today(dom_items, first=first, age=age)
            + tail)

    return RS.page(
        f"{first} — your hands", body,
        eyebrow=("Palm reading · unlocked" if paid
                 else "Palm reading · your hands, and what each area says"),
        heading=f"{first}, here is what your hands are carrying.",
        sub=sub)
