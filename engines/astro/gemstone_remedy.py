#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deterministic gemstone + remedy report (rules40 + rules41).

Chart-based safety gates: debilitated / dusthana lords are not given primary gems.
Timed wear windows follow Vimshottari MD/AD end dates.
"""
from __future__ import annotations

import html
import re
from datetime import date, datetime
from typing import Any, Optional

from astro_precompute import (
    SIGN_LORDS,
    get_dignity,
    house_from_lagna,
    house_sign,
    resolve_precompute,
)

try:
    from client_report_html import client_css, finalize_report_html
except ImportError:
    client_css = lambda: ""  # noqa: E731
    finalize_report_html = lambda h, client_name="": h  # noqa: E731

# rules41 gemstone table (authoritative)
GEM_DATA: dict[str, dict[str, str]] = {
    "Sun": {
        "gem": "Ruby (Manik)", "sub": "Lalri / Garnet", "metal": "Gold or copper",
        "finger": "Ring finger", "day": "Sunday", "mantra": "Aditya Hriday / Surya Gayatri 108x",
        "charity": "Wheat + jaggery on Sunday to the needy",
        "behavior": "Respect father/authority; Surya Namaskar at sunrise",
    },
    "Moon": {
        "gem": "Pearl (Moti)", "sub": "Moonstone / crystal quartz", "metal": "Silver",
        "finger": "Little finger", "day": "Monday", "mantra": "Chandra Gayatri 108x Monday",
        "charity": "Rice, milk, or silver on Monday",
        "behavior": "Respect mother; drink water steadily; wear white on Monday",
    },
    "Mars": {
        "gem": "Red Coral (Moonga)", "sub": "Red Hakik / Kaharwa", "metal": "Copper",
        "finger": "Ring finger", "day": "Tuesday", "mantra": "Hanuman Chalisa daily; Mangal Gayatri 108x",
        "charity": "Red masoor dal on Tuesday; sweets to dogs",
        "behavior": "Avoid anger; wear red on Tuesday",
    },
    "Mercury": {
        "gem": "Emerald (Panna)", "sub": "Green Onyx / Ghritmani", "metal": "Gold or brass",
        "finger": "Little finger", "day": "Wednesday", "mantra": "Vishnu Sahasranama Wednesday; Budh Gayatri 108x",
        "charity": "Green gram or books on Wednesday",
        "behavior": "Green clothes; gardening; clear speech practice",
    },
    "Jupiter": {
        "gem": "Yellow Sapphire (Pukhraj)", "sub": "Sunela / Amber", "metal": "Gold",
        "finger": "Index finger", "day": "Thursday", "mantra": "Brihaspati Gayatri 108x Thursday",
        "charity": "Chana dal + yellow clothes to priest Thursday",
        "behavior": "Respect teachers; yellow on Thursday; water Peepal tree",
    },
    "Venus": {
        "gem": "Diamond (Heera)", "sub": "Fire Opal / White Zircon", "metal": "Silver or platinum",
        "finger": "Middle finger", "day": "Friday", "mantra": "OM SHRIM MAHA LAKSHMIYAI NAMAH 108x Friday",
        "charity": "Ghee or curd to temple on Friday",
        "behavior": "Respect partner; grooming; white clothes Friday",
    },
    "Saturn": {
        "gem": "Blue Sapphire (Neelam)", "sub": "Jamunia / Blue Topaz / Kataila", "metal": "Iron or panchdhatu",
        "finger": "Middle finger", "day": "Saturday", "mantra": "Shani Gayatri 108x; Hanuman Chalisa Tue+Sat",
        "charity": "Urad dal, mustard oil, iron items Saturday",
        "behavior": "Discipline; avoid alcohol; black/blue Saturday",
        "caution": "Test Neelam 3 days before permanent wear (rules41)",
    },
    "Rahu": {
        "gem": "Gomed (Hessonite)", "sub": "Black Onyx / Lapis Lazuli", "metal": "Silver",
        "finger": "Middle finger", "day": "Saturday", "mantra": "Rahu Gayatri 108x",
        "charity": "Coconut or blanket on Saturday",
        "behavior": "Avoid grievances; no blue-black excess",
    },
    "Ketu": {
        "gem": "Cat's Eye (Lehsunia)", "sub": "Turquoise / Agate", "metal": "Gold or silver",
        "finger": "Ring finger", "day": "Tuesday or Thursday", "mantra": "Ketu Gayatri 108x; Ganesha worship",
        "charity": "Blankets to poor; feed dogs",
        "behavior": "Avoid smoking; worship Ganesha",
    },
}

UNIVERSAL_MANTRAS = [
    ("Vishnu Sahasranama", "Wednesday evening  background for all charts (rules40)"),
    ("Gayatri Mantra", "Daily morning  general graha balance"),
    ("Maha-Mrityunjaya", "108x daily when health, child, or recovery themes are active"),
]

DUSTHANA = {6, 8, 12}
DEBIL = {"debilitated", "enemy_sign"}

# Question domain -> extra planets to propitiate (mantra/gem if safe)
DOMAIN_EXTRA: dict[str, list[str]] = {
    "health": ["Sun", "Moon"],
    "recovery": ["Jupiter", "Sun"],
    "speech": ["Mercury", "Venus"],
    "children": ["Jupiter", "Venus"],
    "marriage": ["Venus", "Jupiter"],
    "career": ["Sun", "Mercury"],
    "finance": ["Jupiter", "Venus"],
    "legal": ["Saturn", "Mars"],
    "property": ["Mars", "Venus"],
    "travel": ["Rahu", "Moon"],
    "education": ["Jupiter", "Mercury"],
    "status": ["Sun", "Jupiter"],
    "spiritual": ["Ketu", "Jupiter"],
    "general": [],
}


def _esc(s: Any) -> str:
    return html.escape(str(s))


def _fmt_date(s: str) -> str:
    if not s:
        return ""
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d %b %Y")
    except ValueError:
        return s[:10]


def _house_lord_info(pc: dict, house: int) -> dict[str, Any]:
    lagna = pc.get("lagna", {}).get("sign") or pc.get("meta", {}).get("lagna_sign", "")
    lord = SIGN_LORDS.get(house_sign(house, lagna), "")
    p = pc.get("planets", {}).get(lord, {})
    ph = p.get("house") or house_from_lagna(p.get("sign", ""), lagna)
    dig = p.get("dignity") or get_dignity(lord, p.get("sign", ""))
    return {
        "house": house,
        "lord": lord,
        "sign": p.get("sign", ""),
        "planet_house": ph,
        "dignity": dig,
        "role": f"H{house} lord",
    }


def _planet_snapshot(pc: dict, planet: str) -> dict[str, Any]:
    p = pc.get("planets", {}).get(planet, {})
    lagna = pc.get("lagna", {}).get("sign") or pc.get("meta", {}).get("lagna_sign", "")
    ph = p.get("house") or house_from_lagna(p.get("sign", ""), lagna)
    dig = p.get("dignity") or get_dignity(planet, p.get("sign", ""))
    return {"planet": planet, "house": ph, "sign": p.get("sign", ""), "dignity": dig}


def _gem_safety(
    pc: dict,
    planet: str,
    *,
    role: str = "",
    is_md: bool = False,
    is_ad: bool = False,
) -> dict[str, Any]:
    """Return wear verdict: recommended | mantra_only | avoid | test_required."""
    snap = _planet_snapshot(pc, planet)
    ph = snap["house"]
    dig = snap["dignity"]
    reasons: list[str] = []
    verdict = "recommended"
    use_sub = False

    if ph in DUSTHANA and role not in ("Lagna lord", "H1 lord"):
        verdict = "avoid"
        reasons.append(f"rules41: {planet} rules/occupies dusthana H{ph}")
    if dig in DEBIL:
        if role in ("Lagna lord (H1)", "Lagna lord", "H1 lord") and planet == "Mercury":
            verdict = "mantra_only"
            use_sub = True
            reasons.append("Mercury debilitated as lagna lord  Emerald (Panna) is not advised")
        elif is_md or is_ad:
            verdict = "mantra_only" if verdict != "avoid" else verdict
            use_sub = False
            reasons.append(f"{planet} debilitated during active dasha  mantra and charity only, no gemstone")
        else:
            verdict = "mantra_only" if verdict == "recommended" else verdict
            use_sub = True
            reasons.append(f"{planet} debilitated  primary gem not advised; sub-gem only after 3-day trial if desired")

    if planet == "Saturn" and ph == 12:
        verdict = "avoid"
        reasons.append("Saturn in 12th  Blue Sapphire (Neelam) is not advised")

    if planet in ("Rahu", "Ketu"):
        if is_ad:
            verdict = "mantra_only" if verdict != "avoid" else verdict
            use_sub = False
            gem_name = "Cat's Eye (Lehsunia)" if planet == "Ketu" else "Gomed (Hessonite)"
            reasons.append(
                f"{planet} antardasha active  do not wear {gem_name} or any {planet} gemstone; mantra and charity only"
            )
        elif verdict == "recommended":
            verdict = "mantra_only"
            use_sub = False
            reasons.append(f"{planet} gemstone not advised unless dasha is active and placement is supportive")

    if planet == "Saturn" and verdict == "recommended":
        verdict = "test_required"
        reasons.append("Blue Sapphire must be tested 3 days (rules41)")

    if planet in ("Mars", "Rahu") and ph in (6, 8, 11) and dig in ("moolatrikona", "exalted", "own_sign"):
        if verdict == "recommended":
            verdict = "mantra_only"
            use_sub = False
            reasons.append(f"Strong malefic {planet}  coral/gomed can overheat results; mantra only")

    if dig in ("exalted", "own_sign", "moolatrikona") and ph not in DUSTHANA:
        reasons.append(f"{planet} well placed ({dig}, H{ph})  gem favourable if verdict allows")

    wear_mode = "primary_ok"
    if verdict == "avoid":
        wear_mode = "do_not_wear"
    elif verdict in ("recommended", "test_required"):
        wear_mode = "primary_ok"
    elif planet in ("Ketu", "Rahu") and is_ad:
        wear_mode = "mantra_strict"
    elif role in ("Lagna lord (H1)", "Lagna lord", "H1 lord") and planet == "Mercury" and dig in DEBIL:
        wear_mode = "sub_gem_optional"
    elif is_md or is_ad:
        wear_mode = "mantra_strict"
    elif verdict == "mantra_only":
        wear_mode = "sub_gem_optional"

    return {
        "planet": planet,
        "role": role,
        "verdict": verdict,
        "wear_mode": wear_mode,
        "is_md": is_md,
        "is_ad": is_ad,
        "use_sub_gem": wear_mode == "sub_gem_optional",
        "reasons": reasons,
        "snap": snap,
        "gem": GEM_DATA.get(planet, {}),
    }


def _dasha_windows(pc: dict) -> dict[str, Any]:
    vim = pc.get("vimshottari", {})
    md = vim.get("current_md", {})
    ad = next((a for a in vim.get("current_md_antardashas", []) if a.get("status") == "current"), {})
    return {
        "md_lord": md.get("md_lord", ""),
        "md_end": (md.get("end") or "")[:10],
        "ad_lord": ad.get("ad_lord", ""),
        "ad_start": ad.get("start", "")[:10],
        "ad_end": ad.get("end", "")[:10],
        "antardashas": vim.get("current_md_antardashas", []),
    }


def _timed_recommendations(pc: dict, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach wear-until dates from active/future antardashas."""
    dasha = _dasha_windows(pc)
    md_lord = dasha["md_lord"]
    md_end = dasha["md_end"]
    out: list[dict[str, Any]] = []
    for c in candidates:
        if c["verdict"] in ("avoid",):
            c = {**c, "wear_from": "", "wear_until": "", "timing_note": "Do not wear any gemstone for this planet"}
            out.append(c)
            continue
        pl = c["planet"]
        wear_from = dasha["ad_start"] if pl == dasha["ad_lord"] else ""
        wear_until = dasha["ad_end"] if pl == dasha["ad_lord"] else ""
        if pl == md_lord and not wear_until:
            wear_until = md_end
            wear_from = wear_from or date.today().isoformat()
        if not wear_until:
            for a in dasha["antardashas"]:
                if a.get("ad_lord") == pl:
                    wear_from = a.get("start", "")[:10]
                    wear_until = a.get("end", "")[:10]
                    break
        wm = c.get("wear_mode", "")
        note = ""
        if wm == "mantra_strict":
            if wear_from and wear_until:
                note = f"Until {_fmt_date(wear_until)}: mantra and charity only  no gemstone"
            else:
                note = "Mantra and charity only  no gemstone for this planet"
        elif wm == "sub_gem_optional":
            note = "Mantra is main remedy; sub-gem optional only after 3-day trial"
        elif wear_from and wear_until:
            note = f"Wear from {_fmt_date(wear_from)} until {_fmt_date(wear_until)}"
            if pl == md_lord and wear_until == md_end:
                note += f" (full {pl} mahadasha band)"
        elif c["verdict"] == "mantra_only":
            note = "Mantra and charity only  no primary gemstone"
        else:
            note = "Wear after 3-day trial if comfortable"
        out.append({**c, "wear_from": wear_from, "wear_until": wear_until, "timing_note": note})
    return out


def build_remedy_report(
    pc: dict,
    *,
    question: str = "",
    domain: str = "",
    intent: str = "",
    client_name: str = "",
) -> dict[str, Any]:
    """Full remedy + gemstone dict for one chart."""
    meta = pc.get("meta", {})
    display_name = (client_name or meta.get("client") or "Client").strip()
    lagna = meta.get("lagna_sign") or pc.get("lagna", {}).get("sign", "")
    ll = meta.get("lagna_lord") or SIGN_LORDS.get(lagna, "Mercury")

    h1 = _house_lord_info(pc, 1)
    h5 = _house_lord_info(pc, 5)
    h9 = _house_lord_info(pc, 9)
    dasha = _dasha_windows(pc)

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(planet: str, role: str, *, is_md=False, is_ad=False, priority: int = 5):
        if not planet or planet in seen:
            return
        seen.add(planet)
        ev = _gem_safety(pc, planet, role=role, is_md=is_md, is_ad=is_ad)
        ev["priority"] = priority
        candidates.append(ev)

    # Priority 1: current AD lord
    if dasha["ad_lord"]:
        add(dasha["ad_lord"], f"Current antardasha lord", is_ad=True, priority=1)
    # Priority 2: MD lord (duration only if safe)
    if dasha["md_lord"]:
        add(dasha["md_lord"], f"Mahadasha lord", is_md=True, priority=2)
    # Yoga lords 1/5/9
    add(h1["lord"], "Lagna lord (H1)", priority=3)
    add(h5["lord"], "5th lord (children/luck)", priority=4)
    add(h9["lord"], "9th lord (fortune/dharma)", priority=5)

    # Atmakarak if present
    ak = next((k.get("planet") for k in (pc.get("cara_karakas") or {}).get("karakas", []) if k.get("role") == "Atmakarak"), None)
    if ak:
        add(ak, "Jaimini Atmakarak", priority=3)

    # Question-specific
    dom = domain or ""
    if question and not dom:
        try:
            from client_question_engine import route_client_question
            ctx = route_client_question(question)
            dom = ctx.domain
            intent = intent or ctx.intent
        except Exception:
            dom = "general"
    for pl in DOMAIN_EXTRA.get(dom, []):
        add(pl, f"Question theme ({dom})", priority=4)

    candidates.sort(key=lambda x: (x["priority"], {"recommended": 0, "test_required": 1, "mantra_only": 2, "avoid": 3}[x["verdict"]]))
    timed = _timed_recommendations(pc, candidates)

    primary_wear = [t for t in timed if t["verdict"] in ("recommended", "test_required")]
    mantra_strict = [t for t in timed if t.get("wear_mode") == "mantra_strict"]
    sub_gem_optional = [t for t in timed if t.get("wear_mode") == "sub_gem_optional"]
    avoid = [t for t in timed if t["verdict"] == "avoid"]
    mantra_only = mantra_strict + sub_gem_optional  # backward compatibility

    question_note = ""
    if dom == "speech":
        question_note = "Speech/child themes: favour Venus (if safe) + Mercury mantra; avoid debilitated Emerald."
    elif dom in ("health", "recovery"):
        question_note = "Recovery: mantra-first during afflicted MD; gem only for supportive 5th/11th lords."
    elif dom == "legal":
        question_note = "Legal: Saturn/Mars mantra + Hanuman Chalisa; gems only if lords not in dusthana."
    elif dom in ("career", "status"):
        question_note = "Status/career: Sun/Jupiter/Venus gems when well placed; time wear to strong antardashas."

    return {
        "ok": True,
        "client": display_name,
        "dob": meta.get("dob", ""),
        "lagna": lagna,
        "lagna_lord": ll,
        "dasha": dasha,
        "domain": dom,
        "intent": intent,
        "question": question,
        "question_note": question_note,
        "yoga_lords": {"h1": h1, "h5": h5, "h9": h9},
        "primary_wear": primary_wear[:4],
        "mantra_strict": mantra_strict[:5],
        "sub_gem_optional": sub_gem_optional[:5],
        "mantra_only": mantra_only[:5],
        "avoid": avoid,
        "universal": UNIVERSAL_MANTRAS,
        "sources": "rules40 (Boney mantra-upaya) + rules41 (Avasthi gemstones)",
    }


def build_remedy_from_birth(
    client_name: str,
    dob: str,
    birth_time: str,
    *,
    latitude: float = 0.0,
    longitude: float = 0.0,
    timezone: float = 5.5,
    place_name: str = "",
    extracted_path: str = "",
    precomputed_path: str = "",
    question: str = "",
    domain: str = "",
) -> dict[str, Any]:
    pc = resolve_precompute(
        client_name, dob,
        birth_time=birth_time or None,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        place_name=place_name,
        extracted_path=extracted_path or None,
        precomputed_path=precomputed_path or None,
    )
    return build_remedy_report(pc, question=question, domain=domain)


def _card_verdict_cls(v: str) -> str:
    return {"recommended": "green", "test_required": "amber", "mantra_only": "blue", "avoid": "red"}.get(v, "amber")


def render_remedy_section_html(report: dict[str, Any], *, compact: bool = False) -> str:
    if not report.get("ok"):
        return ""

    dasha = report["dasha"]
    rows = ""
    for item in report.get("primary_wear", []):
        g = item["gem"]
        primary = g.get("gem", "")
        sub = g.get("sub", "")
        if item["verdict"] == "test_required":
            gem_line = f"YES (test 3 days): {primary} OR budget: {sub}"
        else:
            gem_line = f"YES: {primary} OR budget: {sub}"
        rows += f"""<tr>
          <td><strong>{_esc(item['planet'])}</strong><br><span class="fine">{_esc(item['role'])}</span></td>
          <td>{_esc(gem_line)}<br>{_esc(g.get('metal',''))}  {_esc(g.get('finger',''))}  {_esc(g.get('day',''))}</td>
          <td>{_esc(item.get('timing_note',''))}</td>
          <td class="dot-g">{'Mandatory 3-day trial' if item['verdict']=='test_required' else 'Wear after trial OK'}</td>
        </tr>"""

    strict_rows = ""
    for item in report.get("mantra_strict", []):
        g = item["gem"]
        primary = g.get("gem", "")
        sub = g.get("sub", "")
        strict_rows += f"""<li>
          <strong>{_esc(item['planet'])}</strong> ({_esc(item['role'])})<br>
          <span class="fine"><strong>NO gemstone</strong>  do not wear {_esc(primary)} or {_esc(sub)}.<br>
          <strong>Do instead:</strong> {_esc(g.get('mantra',''))}; charity: {_esc(g.get('charity',''))}.<br>
          {_esc(item.get('timing_note',''))}</span>
        </li>"""

    sub_rows = ""
    for item in report.get("sub_gem_optional", []):
        g = item["gem"]
        primary = g.get("gem", "")
        sub = g.get("sub", "")
        sub_rows += f"""<li>
          <strong>{_esc(item['planet'])}</strong> ({_esc(item['role'])})<br>
          <span class="fine"><strong>NO primary gem</strong>  do not wear {_esc(primary)}.<br>
          <strong>Sub-gem optional:</strong> {_esc(sub)}  only after 3-day trial; remove if uncomfortable.<br>
          <strong>Main remedy:</strong> {_esc(g.get('mantra',''))}; charity: {_esc(g.get('charity',''))}.<br>
          {_esc(item.get('timing_note',''))}</span>
        </li>"""

    avoid_rows = ""
    for item in report.get("avoid", []):
        g = item["gem"]
        primary = g.get("gem", "")
        sub = g.get("sub", "")
        avoid_rows += f"""<li>
          <strong>{_esc(item['planet'])}</strong> ({_esc(item['role'])})<br>
          <span class="fine"><strong>NO  do not wear</strong> {_esc(primary)} or {_esc(sub)}.<br>
          {_esc('; '.join(item.get('reasons',[])[:2]))}<br>
          <strong>Use mantra instead:</strong> {_esc(g.get('mantra',''))}</span>
        </li>"""

    uni = "".join(f"<li><strong>{_esc(n)}</strong>  {_esc(d)}</li>" for n, d in report.get("universal", []))

    qblock = ""
    if report.get("question"):
        qblock = f"""<p class="note">Question-linked remedies ({_esc(report.get('domain','general'))}): {_esc(report.get('question_note',''))}</p>"""

    legend = """<p class="body" style="font-size:.85rem;color:var(--muted);margin-bottom:14px">
      <strong>How to read:</strong>
      <span class="dot-g">Green = YES wear</span> 
      <span class="dot-b">Blue = mantra only, no stone</span> 
      <span style="color:#b8860b">Amber = sub-gem optional</span> 
      <span class="dot-r">Red = NO, do not wear</span>
    </p>"""

    if compact and not rows:
        compact_body = "<ul class='bullets'>" + strict_rows + sub_rows
        if avoid_rows:
            compact_body += f"<li><strong>Do not wear:</strong><ul>{avoid_rows}</ul></li>"
        compact_body += "</ul>"
        return f"""<section class="section"><h2>Remedies &amp; Gemstones</h2>{qblock}{compact_body}</section>"""

    strict_block = ""
    if strict_rows:
        strict_block = f"""
<div class="card blue">
  <h3>Mantra &amp; charity only  NO gemstone</h3>
  <p class="body" style="font-size:.88rem">These planets need mantra and charity. <strong>Do not wear</strong> their primary or sub gemstones now.</p>
  <ul class="bullets">{strict_rows}</ul>
</div>"""

    sub_block = ""
    if sub_rows:
        sub_block = f"""
<div class="card amber">
  <h3>Mantra first  sub-gem optional (not primary)</h3>
  <p class="body" style="font-size:.88rem">Primary gemstone is <strong>not advised</strong>. A cheaper sub-stone may be tried for 3 days only.</p>
  <ul class="bullets">{sub_rows}</ul>
</div>"""

    return f"""
<h2 class="section-h">Remedies &amp; Gemstones</h2>
{qblock}
{legend}
<p class="body" style="font-size:.9rem;color:var(--muted)">Current dasha: <strong>{_esc(dasha.get('md_lord',''))}{_esc(dasha.get('ad_lord',''))}</strong>
 (AD until {_esc(_fmt_date(dasha.get('ad_end','')))}). Source: {_esc(report.get('sources',''))}.</p>

<div class="card green">
  <h3>YES  Gemstones you may wear</h3>
  <p class="body" style="font-size:.88rem">Wear only after a 3-day trial. Energise with the planet mantra before first wear.</p>
  <table class="tl"><thead><tr><th>Planet</th><th>Gem / metal / finger</th><th>Timing</th><th>Note</th></tr></thead>
  <tbody>{rows or '<tr><td colspan=4><strong>None now.</strong> Use mantra sections below until a favourable antardasha opens.</td></tr>'}</tbody></table>
</div>
{strict_block}
{sub_block}

<div class="card red">
  <h3>NO  Do not wear (chart risk)</h3>
  <p class="body" style="font-size:.88rem">These stones are <strong>not advised</strong> for this chart. Use mantra and charity instead.</p>
  <ul class="bullets">{avoid_rows or '<li>No hard avoid flags in this pass  still test every new gem for 3 days.</li>'}</ul>
</div>

<div class="card">
  <h3>Universal background practice</h3>
  <ul class="bullets">{uni}</ul>
</div>"""


def render_remedy_report_html(report: dict[str, Any]) -> str:
    body = render_remedy_section_html(report, compact=False)
    nm = _esc(report.get("client", "Client"))
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Remedies &amp; Gemstones  {nm}</title>
<style>{client_css()}</style></head><body>
<div class="wrap">
<div class="hero">
  <h1>Remedies &amp; Gemstones</h1>
  <div class="tag">{nm}  Lagna {_esc(report.get('lagna',''))}</div>
  <div class="meta"><span>{datetime.now().strftime('%d %B %Y').lstrip('0')}</span></div>
</div>
{body}
<p class="fine" style="margin-top:20px">Educational astrology only. Gemstones do not replace medical or legal advice.</p>
</div></body></html>"""


def save_remedy_report(report: dict[str, Any], out_dir: str, slug: str) -> Optional[str]:
    from pathlib import Path
    if not report.get("ok"):
        return None
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%Y%m%d")
    path = out / f"Remedy_Gemstone_{slug}_{today}.html"
    path.write_text(finalize_report_html(render_remedy_report_html(report)), encoding="utf-8")
    return str(path)
